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
from datetime import datetime
from pathlib import Path

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
        start_time = time.time()

        results = [self._run_single_task(task) for task in tasks]

        end_time = time.time()

        report = EvaluationReport(
            model_name=self.model,
            model_config={
                "service": self.service,
                "base_url": self.base_url,
                "model_name": self.actual_model_name,
                "timeout": self.timeout,
            },
            start_time=datetime.fromtimestamp(start_time),
            end_time=datetime.fromtimestamp(end_time),
            total_tasks=len(tasks),
            successful_tasks=sum(1 for r in results if r.success),
            failed_tasks=sum(1 for r in results if not r.success),
            task_results=results,
        )

        logger.info("\n==================== Evaluation Summary ===========================")
        logger.info(
            f"✓ Tasks: {report.successful_tasks}/{report.total_tasks} passed ({report.success_rate:.1f}%)"
        )
        logger.info(f"✓ Total time: {report.execution_time.total_seconds():.1f}s")

        return report


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

    args = parser.parse_args()

    # Load environment variables from .env file
    load_dotenv(override=True)

    # Initialize and run the evaluation pipeline
    pipeline = EvaluationPipeline(
        service=args.service,
        model=args.model,
        max_workers=args.max_workers,
        timeout=args.timeout,
        browser=args.browser,
    )

    report = pipeline.run_evaluation(args.tasks)

    # Create a unique output directory for the report
    sanitized_model_name = (args.model or "unknown_model").replace(".", "-")
    sanitized_task_filter = args.tasks.replace("/", "_")
    output_dir = (
        args.output_dir / f"{args.service}_{sanitized_model_name}_{sanitized_task_filter}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save the evaluation reports
    if not args.no_json:
        json_path = output_dir / f"evaluation_report_{timestamp}.json"
        json_path = pipeline.results_reporter.save_json_report(report, str(json_path))
        logger.info(f"✓ JSON report saved: {json_path}")

    if not args.no_csv:
        csv_path = output_dir / f"evaluation_results_{timestamp}.csv"
        summary_path = output_dir / f"evaluation_summary_{timestamp}.csv"
        csv_path = pipeline.results_reporter.save_csv_report(report, str(csv_path))
        summary_path = pipeline.results_reporter.save_summary_csv(
            report, str(summary_path)
        )
        logger.info(f"✓ CSV reports saved: {csv_path}, {summary_path}")


if __name__ == "__main__":
    main()
