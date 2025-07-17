#!/usr/bin/env python3
"""
Results Reporter for MCPBench Evaluation Pipeline
================================================

This module provides utilities for formatting and outputting evaluation results
in various formats, including console, JSON, and CSV.
"""
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


@dataclass
class TaskResult:
    """
    Represents the result of a single task evaluation.
    
    Attributes:
        category: The category of the task.
        task_id: The unique identifier for the task.
        task_name: The name of the task.
        success: A boolean indicating if the task was successful.
        execution_time: The time taken to execute the task in seconds.
        error_message: An optional error message if the task failed.
    """

    task_name: str
    success: bool
    execution_time: float  # in seconds
    category: Optional[str] = None
    task_id: Optional[int] = None
    error_message: Optional[str] = None
    logs_path: Optional[str] = None
    model_output: Optional[str] = None  # Raw assistant output

    @property
    def status(self) -> str:
        """Returns the status of the task as 'PASS' or 'FAIL'."""
        return "PASS" if self.success else "FAIL"


@dataclass
class EvaluationReport:
    """Represents a complete evaluation report for a model."""

    model_name: str
    model_config: Dict[str, Any]
    start_time: datetime
    end_time: datetime
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    task_results: List[TaskResult]
    tasks_filter: Optional[str] = None

    @property
    def success_rate(self) -> float:
        """Calculates the overall success rate as a percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.total_tasks) * 100

    @property
    def execution_time(self) -> timedelta:
        """Calculates the total execution time."""
        return self.end_time - self.start_time

    def get_category_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculates and returns success statistics grouped by task category.
        """
        category_stats = {}

        for result in self.task_results:
            category = result.category or "Uncategorized"
            if category not in category_stats:
                category_stats[category] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "success_rate": 0.0,
                    "avg_execution_time": 0.0,
                }

            category_stats[category]["total"] += 1
            if result.success:
                category_stats[category]["successful"] += 1
            else:
                category_stats[category]["failed"] += 1

        # Calculate derived metrics like success rate and average time
        for category, stats in category_stats.items():
            if stats["total"] > 0:
                stats["success_rate"] = (
                    stats["successful"] / stats["total"]
                ) * 100
                category_results = [
                    r for r in self.task_results if (r.category or "Uncategorized") == category
                ]
                total_time = sum(r.execution_time for r in category_results)
                stats["avg_execution_time"] = total_time / len(category_results)

        return category_stats


class ResultsReporter:
    """Handles the formatting and output of evaluation results."""

    def __init__(self, output_dir: Path = None):
        """
        Initializes the reporter with an optional output directory.
        """
        self.output_dir = Path(output_dir or "./evaluation_results")
        self.output_dir.mkdir(exist_ok=True)

    def print_console_report(self, report: EvaluationReport, verbose: bool = True):
        """Prints a formatted report to the console."""
        print("=" * 80)
        print("MCPBench Evaluation Report")
        print("=" * 80)
        print(f"Model: {report.model_name}")
        print(f"Start Time: {report.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time: {report.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Execution Time: {report.execution_time}")

        # Overall statistics
        print("Overall Results:")
        print(f"  Total Tasks: {report.total_tasks}")
        print(f"  Successful: {report.successful_tasks}")
        print(f"  Failed: {report.failed_tasks}")
        print(f"  Success Rate: {report.success_rate:.1f}%")

        # Category breakdown
        category_stats = report.get_category_stats()
        if category_stats:
            print("Results by Category:")
            print("-" * 60)
            print(f"{'Category':<30} {'Total':<8} {'Pass':<8} {'Fail':<8} {'Rate':<8}")
            print("-" * 60)
            for category, stats in sorted(category_stats.items()):
                print(
                    f"{category:<30} {stats['total']:<8} {stats['successful']:<8} "
                    f"{stats['failed']:<8} {stats['success_rate']:.1f}%"
                )
            print()

        # Failed tasks details
        failed_tasks = [r for r in report.task_results if not r.success]
        if failed_tasks:
            print("Failed Tasks:")
            print("-" * 60)
            for result in failed_tasks:
                print(f"  ❌ {result.task_name}")
                if result.error_message and verbose:
                    print(f"     Error: {result.error_message}")
            print()

        # Successful tasks (if verbose)
        if verbose:
            successful_tasks = [r for r in report.task_results if r.success]
            if successful_tasks:
                print("Successful Tasks:")
                print("-" * 60)
                for result in successful_tasks:
                    print(f"  ✅ {result.task_name} ({result.execution_time:.1f}s)")
                print()

    def _resolve_path(self, filename: Optional[str], default_name: str) -> Path:
        """Resolves the output path for a report file."""
        if filename:
            path = Path(filename)
            return path if path.is_absolute() or path.parent != Path('.') else self.output_dir / path
        return self.output_dir / default_name

    def save_json_report(self, report: EvaluationReport, filename: str = None) -> Path:
        """Saves the full evaluation report as a JSON file."""
        timestamp = report.start_time.strftime("%Y%m%d_%H%M%S")
        output_path = self._resolve_path(filename, f"evaluation_report_{timestamp}.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report_dict = {
            "model_name": report.model_name,
            "model_config": report.model_config,
            "start_time": report.start_time.isoformat(),
            "end_time": report.end_time.isoformat(),
            "execution_time_seconds": report.execution_time.total_seconds(),
            "summary": {
                "total_tasks": report.total_tasks,
                "successful_tasks": report.successful_tasks,
                "failed_tasks": report.failed_tasks,
                "success_rate": report.success_rate,
            },
            "category_stats": report.get_category_stats(),
            "tasks_filter": report.tasks_filter,
            "task_results": [asdict(result) for result in report.task_results],
        }

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        return output_path

    def save_csv_report(self, report: EvaluationReport, filename: str = None) -> Path:
        """Saves the detailed task results as a CSV file."""
        timestamp = report.start_time.strftime("%Y%m%d_%H%M%S")
        output_path = self._resolve_path(filename, f"evaluation_results_{timestamp}.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Category", "Task ID", "Task Name", "Status", "Execution Time (s)", "Error Message"]
            )
            for result in report.task_results:
                writer.writerow(
                    [
                        result.category,
                        result.task_id,
                        result.task_name,
                        result.status,
                        f"{result.execution_time:.2f}",
                        result.error_message or "",
                    ]
                )
        return output_path

    def save_summary_csv(self, report: EvaluationReport, filename: str = None) -> Path:
        """Saves the category summary as a CSV file."""
        timestamp = report.start_time.strftime("%Y%m%d_%H%M%S")
        output_path = self._resolve_path(filename, f"evaluation_summary_{timestamp}.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Write metadata row for task filter
            writer.writerow(["Tasks Filter", report.tasks_filter or ""])
            writer.writerow([])
            # Header
            writer.writerow(
                ["Category", "Total Tasks", "Successful", "Failed", "Success Rate (%)", "Avg Execution Time (s)"]
            )
            category_stats = report.get_category_stats()
            for category, stats in sorted(category_stats.items()):
                writer.writerow(
                    [
                        category,
                        stats["total"],
                        stats["successful"],
                        stats["failed"],
                        f"{stats['success_rate']:.1f}",
                        f"{stats['avg_execution_time']:.2f}",
                    ]
                )
            # Add overall summary at the end
            writer.writerow([])  # Empty row for separation
            writer.writerow(
                [
                    "OVERALL",
                    report.total_tasks,
                    report.successful_tasks,
                    report.failed_tasks,
                    f"{report.success_rate:.1f}",
                    f"{report.execution_time.total_seconds():.2f}",
                ]
            )
        return output_path

    def generate_full_report(
        self,
        report: EvaluationReport,
        console: bool = True,
        json_export: bool = True,
        csv_export: bool = True,
        verbose: bool = True,
    ) -> Dict[str, Path]:
        """
        Generates a complete set of reports in all supported formats.
        """
        output_files = {}
        if console:
            self.print_console_report(report, verbose=verbose)

        if json_export:
            json_path = self.save_json_report(report)
            output_files["json"] = json_path
            logger.info("JSON report saved: %s", json_path)

        if csv_export:
            csv_path = self.save_csv_report(report)
            summary_path = self.save_summary_csv(report)
            output_files["csv"] = csv_path
            output_files["summary_csv"] = summary_path
            logger.info("CSV reports saved: %s, %s", csv_path, summary_path)

        return output_files


def main():
    """Example usage of the ResultsReporter."""
    start_time = datetime.now() - timedelta(minutes=30)
    end_time = datetime.now()

    task_results = [
        TaskResult(
            category="online_resume",
            task_id=1,
            task_name="online_resume/task_1",
            success=True,
            execution_time=45.2,
        ),
        TaskResult(
            category="online_resume",
            task_id=2,
            task_name="online_resume/task_2",
            success=False,
            execution_time=30.1,
            error_message="API timeout",
        ),
        TaskResult(
            category="job_applications",
            task_id=1,
            task_name="job_applications/task_1",
            success=True,
            execution_time=38.7,
        ),
        TaskResult(
            category="job_applications",
            task_id=2,
            task_name="job_applications/task_2",
            success=True,
            execution_time=52.3,
        ),
    ]

    report = EvaluationReport(
        model_name="gpt-4",
        model_config={"base_url": "https://api.openai.com/v1", "temperature": 0.1},
        start_time=start_time,
        end_time=end_time,
        total_tasks=len(task_results),
        successful_tasks=sum(1 for r in task_results if r.success),
        failed_tasks=sum(1 for r in task_results if not r.success),
        task_results=task_results,
    )

    reporter = ResultsReporter()
    reporter.generate_full_report(report)


if __name__ == "__main__":
    main()
