#!/usr/bin/env python3
"""
MCPBench Unified Evaluation Pipeline
===================================

Automatic evaluation pipeline for testing LLM models on Notion API tasks
with optional page duplication support for consistent evaluation.
"""

import argparse
import asyncio
import sys
import time
import tempfile
import subprocess
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))
from core.task_manager import TaskManager, Task
from core.results_reporter import ResultsReporter, EvaluationReport, TaskResult
from core.notion_runner import NotionRunner
from core.template_manager import TemplateManager


class EvaluationPipeline:
    def __init__(self, 
                 model_name: str,
                 api_key: str,
                 base_url: str,
                 notion_key: str,
                 max_workers: int = 3,
                 timeout: int = 300
                 ):
        # Main config
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.notion_key = notion_key
        self.max_workers = max_workers
        self.timeout = timeout
        
        # Initialize managers
        self.task_manager = TaskManager()
        self.results_reporter = ResultsReporter()
        self.template_manager = TemplateManager(notion_key)
        self.notion_runner = NotionRunner(model_name, api_key, base_url, notion_key)
        
    
    def execute_single_task(self, task: Task) -> TaskResult:
        print(f"\n🔄 Executing task: {task.name}")
        start_time = time.time()
        if task.duplicated_template_id == None:
            execution_time = time.time() - start_time
            
            return TaskResult(
                task_name=task.name,
                success=False,
                execution_time=execution_time,
                error_message="Duplication failed",
                category=task.category,
                task_id=task.task_id
            )
        
        try:
            template_id = str(task.duplicated_template_id)
            task_description = task.get_description() + f"\n\nNote: The ID of the working page/database is `{template_id}`. Check the title and properties of this block; this should be the first step."
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(task_description)
                temp_task_path = f.name
            
            try:
                result = self.notion_runner.run_single_task_file(
                    temp_task_path,
                    timeout=self.timeout
                )
                
                verify_result = subprocess.run([
                    sys.executable, str(task.verify_path), task.duplicated_template_id
                ], capture_output=True, text=True, timeout=60)

                # Logs
                success = verify_result.returncode == 0
                error_message = (verify_result.stderr if verify_result is not None else None) if not success else None
                execution_time = time.time() - start_time
            
                # Clean up the duplicated template
                self.template_manager.delete_template(task.duplicated_template_id)
                
                return TaskResult(
                    task_name=task.name,
                    success=success,
                    execution_time=execution_time,
                    error_message=error_message,
                    model_output=result.get('output', ''),
                    category=task.category,
                    task_id=task.task_id
                )
                
            finally:
                # Clean up temp file
                os.unlink(temp_task_path)
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Task execution failed: {str(e)}"
            
            return TaskResult(
                task_name=task.name,
                success=False,
                execution_time=execution_time,
                error_message=error_msg,
                category=task.category,
                task_id=task.task_id
            )
    
    def run_evaluation(self, task_filter: str) -> EvaluationReport:
        tasks = self.task_manager.filter_tasks(task_filter)
        
        # Process templates and update task objects with template info
        template_results = self.template_manager.process_task_templates(tasks)
        for task in tasks:
            if task.name in template_results:
                task_template_info = template_results[task.name]
                task.original_template_url = task_template_info["original_template_url"]
                task.duplicated_template_url = task_template_info["duplicated_template_url"]
                task.duplicated_template_id = task_template_info["duplicated_template_id"]
    
        start_time = time.time()
        results = []
        for task in tasks:
            result = self.execute_single_task(task)
            results.append(result)

        end_time = time.time()
        
        report = EvaluationReport(
            model_name=self.model_name,
            model_config={"base_url": self.base_url, "timeout": self.timeout},
            start_time=datetime.fromtimestamp(start_time),
            end_time=datetime.fromtimestamp(end_time),
            total_tasks=len(tasks),
            successful_tasks=sum(1 for r in results if r.success),
            failed_tasks=sum(1 for r in results if not r.success),
            task_results=results
        )
        
        success_rate = report.success_rate
        print(f"\n📊 Evaluation Summary:")
        print(f"Tasks: {report.successful_tasks}/{report.total_tasks} passed ({success_rate:.1f}%)")
        print(f"Total time: {report.execution_time.total_seconds():.1f}s")
        
        return report


def main():
    """Main entry point for the evaluation pipeline."""
    parser = argparse.ArgumentParser()
    
    # Model configuration
    parser.add_argument('--model-name', help='Name of the model to evaluate')
    parser.add_argument('--api-key', help='API key for the model provider')
    parser.add_argument('--base-url', help='Base URL for the model provider')
    
    # Task configuration
    parser.add_argument('--notion-key', help='Notion API key')
    parser.add_argument('--tasks', default='all', help='Tasks to run: "all", category name, or "category/task_name"')

    # Execution configuration
    parser.add_argument('--max-workers', type=int, default=3, help='Maximum number of concurrent workers')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout in seconds for each task')
    
    # Output configuration
    parser.add_argument('--output-dir', type=Path, default=Path('data/results'), help='Directory to save results')
    parser.add_argument('--no-json', action='store_true', help='Skip JSON report generation')
    parser.add_argument('--no-csv', action='store_true', help='Skip CSV report generation')
    
    args = parser.parse_args()
    
    # Resolve configuration from CLI args or environment variables
    load_dotenv(override=False)
    model_name = args.model_name or os.getenv('MCPBENCH_MODEL_NAME')
    api_key = args.api_key or os.getenv('MCPBENCH_API_KEY')
    base_url = args.base_url or os.getenv('MCPBENCH_BASE_URL')
    notion_key = args.notion_key or os.getenv('NOTION_API_KEY')
    
    # Initialize and run pipeline
    pipeline = EvaluationPipeline(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        notion_key=notion_key,
        max_workers=args.max_workers,
        timeout=args.timeout,
    )
    
    # Run evaluation
    report = pipeline.run_evaluation(args.tasks)
    
    # Save results
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not args.no_json:
        json_path = args.output_dir / f"evaluation_report_{timestamp}.json"
        json_path = pipeline.results_reporter.save_json_report(report, str(json_path))
        print(f"📄 JSON report saved: {json_path}")
    
    if not args.no_csv:
        csv_path = args.output_dir / f"evaluation_results_{timestamp}.csv"
        summary_path = args.output_dir / f"evaluation_summary_{timestamp}.csv"
        csv_path = pipeline.results_reporter.save_csv_report(report, str(csv_path))
        summary_path = pipeline.results_reporter.save_summary_csv(report, str(summary_path))
        print(f"📊 CSV reports saved: {csv_path}, {summary_path}")


if __name__ == "__main__":
    main()