#!/usr/bin/env python3
"""
MCPBench Unified Evaluation Pipeline
===================================

This script provides an automated evaluation pipeline for testing Large Language Models (LLMs)
on various Multi-Step Cognitive Processes (MCP) services like Notion, GitHub, and PostgreSQL.
It supports optional state management for consistent and reliable evaluations.
"""
import argparse
import time
# Built-ins
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from src.factory import MCPServiceFactory
from src.logger import get_logger
from src.model_config import ModelConfig
from src.results_reporter import EvaluationReport, ResultsReporter, TaskResult

# Initialize logger
logger = get_logger(__name__)


class EvaluationPipeline:
    """
    Orchestrates the evaluation of a model on a given MCP service.
    """

    def __init__(
        self,
        service: str,
        model: str,
        max_workers: int = 3,
        timeout: int = 300,
        browser: str = "firefox",
        exp_name: str = "",
        output_dir: Path = None,
    ):
        # Main configuration
        self.service = service
        self.model = model
        self.max_workers = max_workers
        self.timeout = timeout
        self.browser = browser

        # Initialize model configuration
        model_config = ModelConfig(model)
        self.actual_model_name = model_config.actual_model_name
        self.base_url = model_config.base_url
        self.api_key = model_config.api_key

        # Initialize managers using the factory pattern
        self.task_manager = MCPServiceFactory.create_task_manager(
            service,
            model_name=self.actual_model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout,
        )
        self.state_manager = MCPServiceFactory.create_state_manager(
            service, model_name=self.actual_model_name, browser=browser
        )

        # Initialize results reporter
        self.results_reporter = ResultsReporter()

        # ------------------------------------------------------------------
        # Output directory handling
        # ------------------------------------------------------------------
        self.exp_name = exp_name  # Optional experiment folder name
        # Base directory for all outputs (default: ./results)
        self.output_dir = Path(output_dir or "./results")

        # Directory that groups all tasks for this run
        model_slug = self.actual_model_name.replace(".", "-")
        self.base_experiment_dir = self.output_dir / self.exp_name / f"{service}_{model_slug}"
        self.base_experiment_dir.mkdir(parents=True, exist_ok=True)

    def _get_task_output_dir(self, task) -> Path:
        """Return the directory path for storing this task's reports."""
        # Replace underscores with hyphens inside the category name
        category_slug = task.category.replace("_", "-") if task.category else "uncategorized"
        task_slug = f"task-{task.task_id}"

        return self.base_experiment_dir / f"{category_slug}_{task_slug}"

    # ------------------------------------------------------------------
    # Resuming helpers
    # ------------------------------------------------------------------

    def _convert_dict_to_task_result(self, data: dict) -> TaskResult:
        """Helper to convert a JSON-serialisable dict back to TaskResult."""
        return TaskResult(**data)

    def _load_latest_task_result(self, task) -> Optional[TaskResult]:
        """Return the most recent TaskResult for *task* if it has been run before."""
        task_dir = self._get_task_output_dir(task)
        if not task_dir.exists():
            return None

        json_files = sorted(task_dir.glob("evaluation_report_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not json_files:
            return None

        try:
            with json_files[0].open("r", encoding="utf-8") as f:
                data = json.load(f)
            # Expect single-task report – first element in task_results
            if data.get("task_results"):
                return self._convert_dict_to_task_result(data["task_results"][0])
        except Exception as exc:
            logger.warning("Failed to load existing result for %s: %s", task.name, exc)
        return None

    def _gather_all_task_results(self) -> List[TaskResult]:
        """Scan *all* task sub-directories and collect the latest TaskResult from each."""
        results: list[TaskResult] = []
        if not self.base_experiment_dir.exists():
            return results

        for task_dir in self.base_experiment_dir.iterdir():
            if not task_dir.is_dir():
                continue
            json_files = sorted(task_dir.glob("evaluation_report_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not json_files:
                continue
            try:
                with json_files[0].open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("task_results"):
                    results.append(self._convert_dict_to_task_result(data["task_results"][0]))
            except Exception as exc:
                logger.warning("Failed to parse existing report in %s: %s", task_dir, exc)
        return results

    def _run_single_task(self, task) -> TaskResult:
        """
        Runs a single task, including setup, execution, and cleanup.
        """
        # Set up the initial state for the task
        setup_start_time = time.time()
        logger.info("==================== Stage 1: Setting Up Task ====================")
        setup_success = self.state_manager.set_up(task)
        setup_time = time.time() - setup_start_time

        if not setup_success:
            logger.error(f"State setup failed for task: {task.name}")
            return TaskResult(
                task_name=task.name,
                success=False,
                execution_time=setup_time,
                error_message="State Duplication Error",
                category=task.category,
                task_id=task.task_id,
            )

        # Execute the task and record the result
        logger.info("\n==================== Stage 2: Executing Task ======================")
        result = self.task_manager.execute_task(task)

        # Clean up the temporary task state
        logger.info("\n==================== Stage 3: Cleaning Up =========================")
        self.state_manager.clean_up(task)

        return result

    def run_evaluation(self, task_filter: str) -> EvaluationReport:
        """
        Runs the full evaluation for the specified tasks.
        """
        tasks = self.task_manager.filter_tasks(task_filter)
        pipeline_start_time = time.time()

        results = []

        for task in tasks:
            # ------------------------ Resume check ------------------------
            existing_result = self._load_latest_task_result(task)
            if existing_result:
                logger.info("↩️  Skipping already-completed task (resume): %s", task.name)
                results.append(existing_result)
                continue

            # -------------------- Execute new task -----------------------
            task_start = time.time()
            task_result = self._run_single_task(task)
            task_end = time.time()

            results.append(task_result)

            # ----------------------------------------------------------
            # Save results for this single task immediately for resume
            # ----------------------------------------------------------
            single_report = EvaluationReport(
                model_name=self.model,
                model_config={
                    "service": self.service,
                    "base_url": self.base_url,
                    "model_name": self.actual_model_name,
                    "timeout": self.timeout,
                },
                start_time=datetime.fromtimestamp(task_start),
                end_time=datetime.fromtimestamp(task_end),
                total_tasks=1,
                successful_tasks=1 if task_result.success else 0,
                failed_tasks=0 if task_result.success else 1,
                task_results=[task_result],
                tasks_filter=task.name,
            )

            # Prepare directory & save
            task_output_dir = self._get_task_output_dir(task)
            task_output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            json_path = task_output_dir / f"evaluation_report_{timestamp}.json"
            csv_path = task_output_dir / f"evaluation_results_{timestamp}.csv"

            self.results_reporter.save_json_report(single_report, str(json_path))
            self.results_reporter.save_csv_report(single_report, str(csv_path))

        pipeline_end_time = time.time()

        # --------------------------------------------------------------
        # Aggregate results – combine current `results` with any previously
        # saved TaskResults that ALSO match the current task_filter.
        # --------------------------------------------------------------

        # Helper: determine if a TaskResult matches the filter string
        def _matches_filter(tr: TaskResult, flt: str) -> bool:
            if flt.lower() == "all":
                return True
            if "/" in flt:
                # specific task (category/task_N)
                return tr.task_name == flt
            # category level
            return tr.category == flt

        # Pull existing reports from disk and merge
        existing_results = [r for r in self._gather_all_task_results() if _matches_filter(r, task_filter)]

        # Merge, giving preference to fresh `results` (avoids duplicates)
        merged: dict[str, TaskResult] = {r.task_name: r for r in existing_results}
        merged.update({r.task_name: r for r in results})  # overwrite with latest run

        final_results = list(merged.values())

        aggregated_report = EvaluationReport(
            model_name=self.model,
            model_config={
                "service": self.service,
                "base_url": self.base_url,
                "model_name": self.actual_model_name,
                "timeout": self.timeout,
            },
            start_time=datetime.fromtimestamp(pipeline_start_time),
            end_time=datetime.fromtimestamp(pipeline_end_time),
            total_tasks=len(final_results),
            successful_tasks=sum(1 for r in final_results if r.success),
            failed_tasks=sum(1 for r in final_results if not r.success),
            task_results=final_results,
            tasks_filter=task_filter,
        )

        logger.info("\n==================== Evaluation Summary ===========================")
        logger.info(
            f"✓ Tasks: {aggregated_report.successful_tasks}/{aggregated_report.total_tasks} passed ({aggregated_report.success_rate:.1f}%)"
        )
        logger.info(f"✓ Total time: {aggregated_report.execution_time.total_seconds():.1f}s")

        return aggregated_report


def main():
    """Main entry point for the evaluation pipeline."""
    parser = argparse.ArgumentParser(
        description="MCPBench Unified Evaluation Pipeline."
    )

    supported_services = MCPServiceFactory.get_supported_services()
    supported_models = ModelConfig.get_supported_models()

    # Main configuration
    parser.add_argument(
        "--service",
        default="notion",
        choices=supported_services,
        help="MCP service to use (default: notion)",
    )
    parser.add_argument(
        "--model",
        required=True,
        choices=supported_models,
        help="Name of the model to evaluate",
    )
    parser.add_argument(
        "--tasks",
        default="all",
        help='Tasks to run: "all", a category name, or "category/task_name"',
    )

    # Execution configuration
    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Maximum number of concurrent workers",
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Timeout in seconds for each task"
    )

    # Playwright configuration
    parser.add_argument(
        "--browser",
        default="firefox",
        choices=["chromium", "firefox"],
        help="Playwright browser engine to use (default: firefox)",
    )

    # Output configuration
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./results"),
        help="Directory to save results",
    )
    parser.add_argument(
        "--no-json", action="store_true", help="Skip JSON report generation"
    )
    parser.add_argument(
        "--no-csv", action="store_true", help="Skip CSV report generation"
    )

    # Experiment name (required) – results are stored under results/<exp-name>/
    parser.add_argument(
        "--exp-name",
        required=True,
        help="Experiment name; results are saved under results/<exp-name>/",
    )

    args = parser.parse_args()

    # Load environment variables from .env file
    load_dotenv(dotenv_path=".mcp_env", override=True)

    # Initialize and run the evaluation pipeline
    pipeline = EvaluationPipeline(
        service=args.service,
        model=args.model,
        max_workers=args.max_workers,
        timeout=args.timeout,
        browser=args.browser,
        exp_name=args.exp_name,
        output_dir=args.output_dir,
    )

    report = pipeline.run_evaluation(args.tasks)

    # Create a unique output directory for the report
    sanitized_model_name = (args.model or "unknown_model").replace(".", "-")
    output_dir = args.output_dir / args.exp_name / f"{args.service}_{sanitized_model_name}"
    output_dir.mkdir(parents=True, exist_ok=True)
    sanitized_task_filter = args.tasks.replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = output_dir / f"evaluation_report_{sanitized_task_filter}_{timestamp}.json"
    csv_path = output_dir / f"evaluation_results_{sanitized_task_filter}_{timestamp}.csv"
    summary_path = output_dir / f"evaluation_summary_{sanitized_task_filter}_{timestamp}.csv"

    # Save the evaluation reports
    if not args.no_json:
        json_path = pipeline.results_reporter.save_json_report(report, str(json_path))
        logger.info(f"✓ JSON report saved: {json_path}")

    if not args.no_csv:
        csv_path = pipeline.results_reporter.save_csv_report(report, str(csv_path))
        summary_path = pipeline.results_reporter.save_summary_csv(report, str(summary_path))
        logger.info(f"✓ CSV reports saved: {csv_path}, {summary_path}")


if __name__ == "__main__":
    main()
