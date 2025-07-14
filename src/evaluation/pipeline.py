#!/usr/bin/env python3
"""
MCPBench Unified Evaluation Pipeline
===================================

Automatic evaluation pipeline for testing LLM models on Notion API tasks
with optional page duplication support for consistent evaluation.

Usage:
    python pipeline.py --model-name gpt-4 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks all
    python pipeline.py --model-name claude-3 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume --duplicate-pages
    python pipeline.py --model-name gpt-3.5-turbo --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume/task_1
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
from typing import List, Dict, Any, Optional, Tuple
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Load environment variables from a .env file if present.
# Existing environment variables take precedence over those in the .env file.
load_dotenv(override=False)

# Import our custom modules
sys.path.append(str(Path(__file__).parent.parent))
from core.task_manager import TaskManager, Task
from core.results_reporter import ResultsReporter, EvaluationReport, TaskResult
from utils.mcp_utils import get_notion_key, create_model_provider, create_mcp_server
from core.notion_task_runner import run_single_task_file as run_single_task, read_task_file
from core.page_duplication_manager import PageDuplicationManager
from core.task_template_manager import TaskTemplateManager

try:
    from agents import Agent, ModelSettings
except ImportError:
    print("Warning: agents module not found. Some functionality may be limited.")
    Agent = None
    ModelSettings = None


class EvaluationPipeline:
    """Unified evaluation pipeline for MCPBench with optional page duplication."""
    
    def __init__(self, 
                 model_name: str,
                 api_key: str,
                 base_url: str,
                 notion_key: str,
                 max_workers: int = 3,
                 timeout: int = 300,
                 duplicate_pages: bool = False,
                 config_path: Optional[Path] = None):
        """Initialize the evaluation pipeline.
        
        Args:
            model_name: Name of the model to evaluate
            api_key: API key for the model provider
            base_url: Base URL for the model provider
            notion_key: Notion API key
            max_workers: Maximum number of concurrent workers
            timeout: Timeout in seconds for each task
            duplicate_pages: Whether to duplicate pages for consistent evaluation
            config_path: Optional path to configuration file
        """
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.notion_key = notion_key
        self.max_workers = max_workers
        self.timeout = timeout
        self.duplicate_pages = duplicate_pages
        
        # Initialize managers
        self.task_manager = TaskManager()
        self.results_reporter = ResultsReporter()
        # These managers are only needed when page duplication is enabled. We lazily
        # instantiate the PageDuplicationManager later once we have the *source_pages*
        # information (passed to run_evaluation).
        self.page_duplication_manager = None
        if self.duplicate_pages:
            self.task_template_manager = TaskTemplateManager()
        
        # Load additional config if provided
        if config_path and config_path.exists():
            self._load_config(config_path)
    
    def _load_config(self, config_path: Path):
        """Load configuration from file."""
        try:
            with open(config_path) as f:
                config = json.load(f)
                # Override settings with config values if present
                self.max_workers = config.get('max_workers', self.max_workers)
                self.timeout = config.get('timeout', self.timeout)
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
    
    def _validate_config(self) -> bool:
        """Validate the pipeline configuration."""
        if not self.model_name:
            print("Error: Model name is required")
            return False
        if not self.api_key:
            print("Error: API key is required")
            return False
        if not self.base_url:
            print("Error: Base URL is required")
            return False
        if not self.notion_key:
            print("Error: Notion API key is required")
            return False
        return True
    
    def execute_single_task(self, task: Task, source_pages: Dict[str, str]) -> TaskResult:
        """Execute a single evaluation task.
        
        Args:
            task: Task to execute
            source_pages: Dict mapping task categories to source page URLs
            
        Returns:
            TaskResult with execution details
        """
        print(f"\n🔄 Executing task: {task.name}")
        start_time = time.time()
        
        try:
            # Handle page duplication if enabled
            if self.duplicate_pages:
                category = task.name.split('/')[0]

                # Duplicate the page for this task/category.
                print(f"🔄 Duplicating page for task: {task.name}")
                try:
                    duplicated_url, page_id = self.page_duplication_manager.duplicate_page_for_task(
                        category, task.name
                    )
                except Exception as dup_exc:
                    return TaskResult(
                        task_name=task.name,
                        success=False,
                        execution_time=time.time() - start_time,
                        error_message=f"Failed to duplicate page: {dup_exc}"
                    )
                
                if not page_id:
                    return TaskResult(
                        task_name=task.name,
                        success=False,
                        execution_time=time.time() - start_time,
                        error_message="Failed to duplicate page"
                    )
                
                # Modify task description to use the duplicated page
                task_description = self.task_template_manager.replace_page_search_with_id(
                    task.description, page_id
                )
                
                # Write modified task to a temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                    f.write(task_description)
                    temp_task_path = f.name
                
                try:
                    # Execute the task with the modified description
                    result = run_single_task(
                        temp_task_path,
                        self.model_name,
                        self.api_key,
                        self.base_url,
                        self.notion_key,
                        timeout=self.timeout
                    )
                    
                    # Run verification if available
                    verify_result = None  # Ensure the variable is defined for later error handling
                    if task.verify_script:
                        print(f"🔍 Running verification for task: {task.name}")
                        verify_result = subprocess.run([
                            sys.executable, str(task.verify_script), page_id
                        ], capture_output=True, text=True, timeout=60)

                        success = verify_result.returncode == 0
                        if not success:
                            print(f"❌ Verification failed: {verify_result.stderr}")
                    else:
                        success = result.get('success', False)
                    
                    execution_time = time.time() - start_time
                    
                    # Clean up: delete the duplicated page
                    print(f"🧹 Cleaning up duplicated page for task: {task.name}")
                    self.page_duplication_manager.delete_page(page_id)
                    
                    return TaskResult(
                        task_name=task.name,
                        success=success,
                        execution_time=execution_time,
                        error_message=(verify_result.stderr if verify_result is not None else None) if not success else None,
                        model_output=result.get('output', ''),
                        page_id=page_id
                    )
                    
                finally:
                    # Clean up temp file
                    os.unlink(temp_task_path)
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Task execution failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            return TaskResult(
                task_name=task.name,
                success=False,
                execution_time=execution_time,
                error_message=error_msg
            )
    
    def run_evaluation(self, task_filter: str, source_pages: Dict[str, str] = None) -> EvaluationReport:
        """Run the complete evaluation pipeline.
        
        Args:
            task_filter: Filter for tasks to run ('all', category name, or specific task)
            source_pages: Dict mapping task categories to source page URLs (required if duplicate_pages=True)
            
        Returns:
            EvaluationReport with all results
        """
        if not self._validate_config():
            sys.exit(1)
        
        if self.duplicate_pages and not source_pages:
            print("Error: source_pages must be provided when duplicate_pages=True")
            sys.exit(1)
        
        print(f"🚀 Starting MCPBench evaluation")
        print(f"Model: {self.model_name}")
        print(f"Task filter: {task_filter}")
        print(f"Page duplication: {self.duplicate_pages}")
        print(f"Max workers: {self.max_workers}")
        
        # Discover tasks
        tasks = self.task_manager.filter_tasks(task_filter)
        if not tasks:
            print(f"❌ No tasks found matching filter: {task_filter}")
            sys.exit(1)
        
        print(f"📋 Found {len(tasks)} tasks to evaluate")
        
        # Execute tasks
        start_time = time.time()
        results = []
        
        if self.duplicate_pages:
            # Lazy creation of the duplication manager now that we have *source_pages*.
            if self.page_duplication_manager is None:
                self.page_duplication_manager = PageDuplicationManager(
                    self.notion_key,
                    {"source_pages": source_pages},
                )
            # Run sequentially when page duplication is enabled
            print("🔄 Running tasks sequentially (page duplication enabled)")
            for task in tasks:
                result = self.execute_single_task(task, source_pages)
                results.append(result)
                print(f"✅ Task {task.name}: {'PASSED' if result.success else 'FAILED'}")
        else:
            # Run in parallel when page duplication is disabled
            print(f"🔄 Running tasks in parallel (max {self.max_workers} workers)")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task = {
                    executor.submit(self.execute_single_task, task, source_pages or {}): task
                    for task in tasks
                }
                
                for future in concurrent.futures.as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        results.append(result)
                        print(f"✅ Task {task.name}: {'PASSED' if result.success else 'FAILED'}")
                    except Exception as e:
                        print(f"❌ Task {task.name} failed with exception: {e}")
                        results.append(TaskResult(
                            task_name=task.name,
                            success=False,
                            execution_time=0,
                            error_message=str(e)
                        ))
        
        total_time = time.time() - start_time
        
        # Generate report
        report = EvaluationReport(
            model_name=self.model_name,
            start_time=start_time,
            end_time=datetime.now(),
            total_tasks=len(tasks),
            passed_tasks=sum(1 for r in results if r.success),
            task_results=results,
            duplicate_pages=self.duplicate_pages
        )
        
        # Print summary
        success_rate = (report.passed_tasks / report.total_tasks) * 100
        print(f"\n📊 Evaluation Summary:")
        print(f"Tasks: {report.passed_tasks}/{report.total_tasks} passed ({success_rate:.1f}%)")
        print(f"Total time: {report.total_time:.1f}s")
        
        return report


def main():
    """Main entry point for the evaluation pipeline."""
    parser = argparse.ArgumentParser(
        description="MCPBench Evaluation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate all tasks with basic pipeline
  python pipeline.py --model-name gpt-4 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks all
  
  # Evaluate specific category with page duplication
  python pipeline.py --model-name claude-3 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume --duplicate-pages --source-pages '{"online_resume": "https://notion.so/page-url"}'
  
  # Evaluate single task
  python pipeline.py --model-name gpt-3.5-turbo --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume/task_1
        """
    )
    
    # Model configuration
    parser.add_argument('--model-name', help='Name of the model to evaluate')
    parser.add_argument('--api-key', help='API key for the model provider')
    parser.add_argument('--base-url', help='Base URL for the model provider')
    parser.add_argument('--notion-key', help='Notion API key')
    
    # Task configuration
    parser.add_argument('--tasks', default='all', help='Tasks to run: "all", category name, or "category/task_name"')
    parser.add_argument('--duplicate-pages', action='store_true', help='Enable page duplication for consistent evaluation')
    parser.add_argument('--source-pages', help='JSON string mapping task categories to source page URLs (required if --duplicate-pages)')
    
    # Execution configuration
    parser.add_argument('--max-workers', type=int, default=3, help='Maximum number of concurrent workers (ignored with --duplicate-pages)')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout in seconds for each task')
    parser.add_argument('--config', type=Path, help='Path to configuration file')
    
    # Output configuration
    parser.add_argument('--output-dir', type=Path, default=Path('data/results'), help='Directory to save results')
    parser.add_argument('--no-json', action='store_true', help='Skip JSON report generation')
    parser.add_argument('--no-csv', action='store_true', help='Skip CSV report generation')
    
    args = parser.parse_args()
    
    # Resolve configuration from CLI args or environment variables
    model_name = args.model_name or os.getenv('MCPBENCH_MODEL_NAME')
    api_key = args.api_key or os.getenv('MCPBENCH_API_KEY')
    base_url = args.base_url or os.getenv('MCPBENCH_BASE_URL')
    notion_key = args.notion_key or get_notion_key()

    if not model_name:
        print("Error: Model name not provided. Use --model-name or set MCPBENCH_MODEL_NAME environment variable.")
        sys.exit(1)
    if not api_key:
        print("Error: API key not provided. Use --api-key or set MCPBENCH_API_KEY environment variable.")
        sys.exit(1)
    if not base_url:
        print("Error: Base URL not provided. Use --base-url or set MCPBENCH_BASE_URL environment variable.")
        sys.exit(1)
    if not notion_key:
        print("Error: Notion API key not provided. Use --notion-key or set NOTION_API_KEY environment variable.")
        sys.exit(1)
    
    # Parse source pages if provided via CLI first
    source_pages = {}
    if args.source_pages:
        try:
            source_pages = json.loads(args.source_pages)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --source-pages: {e}")
            sys.exit(1)

    # Fallback: if --source-pages not provided, attempt to load from the config file (if given)
    if not source_pages and args.config and args.config.exists():
        try:
            with open(args.config, 'r') as cfg_file:
                cfg = json.load(cfg_file)
                source_pages = cfg.get('source_pages', {})
        except Exception as e:
            print(f"Warning: Could not load source_pages from config file {args.config}: {e}")

    # Validate page duplication requirements
    if args.duplicate_pages and not source_pages:
        print("Error: --source-pages must be provided when --duplicate-pages is enabled (either via CLI or in the config file)")
        sys.exit(1)
    
    # Initialize and run pipeline
    pipeline = EvaluationPipeline(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        notion_key=notion_key,
        max_workers=args.max_workers,
        timeout=args.timeout,
        duplicate_pages=args.duplicate_pages,
        config_path=args.config
    )
    
    # Run evaluation
    report = pipeline.run_evaluation(args.tasks, source_pages)
    
    # Save results
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not args.no_json:
        json_path = args.output_dir / f"evaluation_report_{timestamp}.json"
        pipeline.results_reporter.save_json_report(report, json_path)
        print(f"📄 JSON report saved: {json_path}")
    
    if not args.no_csv:
        csv_path = args.output_dir / f"evaluation_results_{timestamp}.csv"
        summary_path = args.output_dir / f"evaluation_summary_{timestamp}.csv"
        pipeline.results_reporter.save_csv_reports(report, csv_path, summary_path)
        print(f"📊 CSV reports saved: {csv_path}, {summary_path}")


if __name__ == "__main__":
    main()