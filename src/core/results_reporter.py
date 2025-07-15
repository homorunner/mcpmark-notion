#!/usr/bin/env python3
"""
Results Reporter for MCPBench Evaluation Pipeline
================================================

This module provides utilities for formatting and outputting evaluation results
in various formats (console, JSON, CSV).
"""

import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class TaskResult:
    """Represents the result of a single task evaluation.

    The fields *category* and *task_id* are optional to allow older call sites
    (e.g. legacy or in-progress refactors) that may not yet supply them. When
    omitted, they will default to ``None`` which is handled gracefully by the
    reporting utilities.
    """

    task_name: str
    success: bool
    execution_time: float  # in seconds

    # Optional/extended metadata ------------------------------------------------
    category: Optional[str] = None
    task_id: Optional[int] = None
    error_message: Optional[str] = None
    logs_path: Optional[str] = None
    model_output: Optional[str] = None  # Raw assistant output (if captured) 
    
    @property
    def status(self) -> str:
        return "PASS" if self.success else "FAIL"


@dataclass
class EvaluationReport:
    """Represents a complete evaluation report."""
    model_name: str
    model_config: Dict[str, Any]
    start_time: datetime
    end_time: datetime
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    task_results: List[TaskResult]
    
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate as percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.total_tasks) * 100
    
    @property
    def execution_time(self) -> timedelta:
        """Total execution time."""
        return self.end_time - self.start_time
    
    def get_category_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get success statistics by category."""
        category_stats = {}
        
        for result in self.task_results:
            category = result.category
            if category not in category_stats:
                category_stats[category] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "success_rate": 0.0,
                    "avg_execution_time": 0.0
                }
            
            category_stats[category]["total"] += 1
            if result.success:
                category_stats[category]["successful"] += 1
            else:
                category_stats[category]["failed"] += 1
        
        # Calculate derived metrics
        for category, stats in category_stats.items():
            if stats["total"] > 0:
                stats["success_rate"] = (stats["successful"] / stats["total"]) * 100
                
                # Calculate average execution time for this category
                category_results = [r for r in self.task_results if r.category == category]
                total_time = sum(r.execution_time for r in category_results)
                stats["avg_execution_time"] = total_time / len(category_results)
        
        return category_stats


class ResultsReporter:
    """Handles formatting and output of evaluation results."""
    
    def __init__(self, output_dir: Path = None):
        """Initialize with optional output directory for file exports."""
        if output_dir is None:
            output_dir = Path("./evaluation_results")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def print_console_report(self, report: EvaluationReport, verbose: bool = True):
        """Print a formatted console report."""
        print("=" * 80)
        print("MCPBench Evaluation Report")
        print("=" * 80)
        print()
        
        # Model information
        print(f"Model: {report.model_name}")
        print(f"Start Time: {report.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time: {report.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Execution Time: {report.execution_time}")
        print()
        
        # Overall statistics
        print("Overall Results:")
        print(f"  Total Tasks: {report.total_tasks}")
        print(f"  Successful: {report.successful_tasks}")
        print(f"  Failed: {report.failed_tasks}")
        print(f"  Success Rate: {report.success_rate:.1f}%")
        print()
        
        # Category breakdown
        category_stats = report.get_category_stats()
        if category_stats:
            print("Results by Category:")
            print("-" * 60)
            print(f"{'Category':<30} {'Total':<8} {'Pass':<8} {'Fail':<8} {'Rate':<8}")
            print("-" * 60)
            
            for category, stats in sorted(category_stats.items()):
                print(f"{category:<30} {stats['total']:<8} {stats['successful']:<8} "
                      f"{stats['failed']:<8} {stats['success_rate']:.1f}%")
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
    
    def save_json_report(self, report: EvaluationReport, filename: str = None) -> Path:
        """Save report as JSON file."""
        # -----------------------------------------------------------------
        # Resolve output path
        # -----------------------------------------------------------------
        if filename is None:
            timestamp = report.start_time.strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"evaluation_report_{timestamp}.json"
        else:
            candidate = Path(filename)
            # If the provided filename is absolute or already contains parent
            # directories, respect it as-is; otherwise, place it inside the
            # default output directory.
            if candidate.is_absolute() or candidate.parent != Path('.'):
                output_path = candidate
            else:
                output_path = self.output_dir / candidate

        # Ensure destination directory exists (including nested folders)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert report to JSON-serializable format
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
                "success_rate": report.success_rate
            },
            "category_stats": report.get_category_stats(),
            "task_results": [asdict(result) for result in report.task_results]
        }
        
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def save_csv_report(self, report: EvaluationReport, filename: str = None) -> Path:
        """Save detailed task results as CSV file."""
        # -----------------------------------------------------------------
        # Resolve output path
        # -----------------------------------------------------------------
        if filename is None:
            timestamp = report.start_time.strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"evaluation_results_{timestamp}.csv"
        else:
            candidate = Path(filename)
            if candidate.is_absolute() or candidate.parent != Path('.'):
                output_path = candidate
            else:
                output_path = self.output_dir / candidate

        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "Category", "Task ID", "Task Name", "Status", 
                "Execution Time (s)", "Error Message"
            ])
            
            # Write task results
            for result in report.task_results:
                writer.writerow([
                    result.category,
                    result.task_id,
                    result.task_name,
                    result.status,
                    f"{result.execution_time:.2f}",
                    result.error_message or ""
                ])
        
        return output_path
    
    def save_summary_csv(self, report: EvaluationReport, filename: str = None) -> Path:
        """Save category summary as CSV file."""
        # -----------------------------------------------------------------
        # Resolve output path
        # -----------------------------------------------------------------
        if filename is None:
            timestamp = report.start_time.strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"evaluation_summary_{timestamp}.csv"
        else:
            candidate = Path(filename)
            if candidate.is_absolute() or candidate.parent != Path('.'):
                output_path = candidate
            else:
                output_path = self.output_dir / candidate

        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        category_stats = report.get_category_stats()
        
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "Category", "Total Tasks", "Successful", "Failed", 
                "Success Rate (%)", "Avg Execution Time (s)"
            ])
            
            # Write category stats
            for category, stats in sorted(category_stats.items()):
                writer.writerow([
                    category,
                    stats["total"],
                    stats["successful"],
                    stats["failed"],
                    f"{stats['success_rate']:.1f}",
                    f"{stats['avg_execution_time']:.2f}"
                ])
            
            # Write overall summary
            writer.writerow([])  # Empty row
            writer.writerow([
                "OVERALL",
                report.total_tasks,
                report.successful_tasks,
                report.failed_tasks,
                f"{report.success_rate:.1f}",
                f"{report.execution_time.total_seconds():.2f}"
            ])
        
        return output_path
    
    def generate_full_report(self, report: EvaluationReport, 
                           console: bool = True, 
                           json_export: bool = True,
                           csv_export: bool = True,
                           verbose: bool = True) -> Dict[str, Path]:
        """Generate a complete report with all formats."""
        output_files = {}
        
        # Console output
        if console:
            self.print_console_report(report, verbose=verbose)
        
        # JSON export
        if json_export:
            json_path = self.save_json_report(report)
            output_files["json"] = json_path
            print(f"JSON report saved: {json_path}")
        
        # CSV exports
        if csv_export:
            csv_path = self.save_csv_report(report)
            summary_path = self.save_summary_csv(report)
            output_files["csv"] = csv_path
            output_files["summary_csv"] = summary_path
            print(f"CSV reports saved: {csv_path}, {summary_path}")
        
        return output_files


def main():
    """Example usage of ResultsReporter."""
    # Create sample data
    start_time = datetime.now() - timedelta(minutes=30)
    end_time = datetime.now()
    
    task_results = [
        TaskResult("online_resume", 1, "online_resume/task_1", True, 45.2),
        TaskResult("online_resume", 2, "online_resume/task_2", False, 30.1, "API timeout"),
        TaskResult("job_applications", 1, "job_applications/task_1", True, 38.7),
        TaskResult("job_applications", 2, "job_applications/task_2", True, 52.3),
    ]
    
    report = EvaluationReport(
        model_name="gpt-4",
        model_config={"base_url": "https://api.openai.com/v1", "temperature": 0.1},
        start_time=start_time,
        end_time=end_time,
        total_tasks=4,
        successful_tasks=3,
        failed_tasks=1,
        task_results=task_results
    )
    
    # Generate report
    reporter = ResultsReporter()
    reporter.generate_full_report(report)


if __name__ == "__main__":
    main()