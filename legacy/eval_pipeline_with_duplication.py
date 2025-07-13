#!/usr/bin/env python3
"""
MCPBench Evaluation Pipeline with Page Duplication
=================================================

Automatic evaluation pipeline for testing LLM models on Notion API tasks
with support for page duplication to ensure consistent evaluation.

Usage:
    python eval_pipeline_with_duplication.py --model-name gpt-4 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks all
    python eval_pipeline_with_duplication.py --model-name claude-3 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume
    python eval_pipeline_with_duplication.py --model-name gpt-3.5-turbo --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume/task_1
"""

import argparse
import asyncio
import sys
import time
import tempfile
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# Import our custom modules
from task_manager import TaskManager, Task
from results_reporter import ResultsReporter, EvaluationReport, TaskResult
from mcp_utils import get_notion_key, create_model_provider, create_mcp_server
from notion_task_runner import run_single_task, read_task_file
from agents import Agent, ModelSettings
from page_duplication_manager import PageDuplicationManager
from task_template_manager import TaskTemplateManager


class EvaluationPipeline:
    """Main evaluation pipeline for MCPBench with page duplication support."""
    
    def __init__(self, 
                 model_name: str,
                 api_key: str,
                 base_url: str,
                 notion_key: str,
                 max_workers: int = 3,
                 timeout: int = 300,
                 config_path: Optional[Path] = None):
        """Initialize the evaluation pipeline.
        
        Args:
            model_name: Name of the model to evaluate
            api_key: API key for model provider
            base_url: Base URL for model provider
            notion_key: Notion API key
            max_workers: Maximum number of parallel task executions
            timeout: Timeout for each task execution in seconds
            config_path: Path to configuration file
        """
        self.model_name = model_name
        self.model_config = {
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_name
        }
        self.notion_key = notion_key
        self.max_workers = max_workers
        self.timeout = timeout
        
        self.task_manager = TaskManager()
        self.reporter = ResultsReporter()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize page duplication if enabled
        self.use_page_duplication = self.config.get("evaluation", {}).get("use_duplicated_pages", False)
        if self.use_page_duplication:
            self.page_manager = PageDuplicationManager(
                notion_key=notion_key,
                config=self.config,
                headless=self.config.get("page_duplication", {}).get("headless", True)
            )
            self.template_manager = TaskTemplateManager()
        
        # Validate configuration
        self._validate_config()
    
    def _load_config(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load configuration from file."""
        if config_path is None:
            config_path = Path("config.json")
        
        if not config_path.exists():
            print(f"⚠️  Configuration file not found at {config_path}, using defaults")
            return {
                "evaluation": {"use_duplicated_pages": False},
                "page_duplication": {"headless": True}
            }
        
        try:
            with config_path.open("r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Failed to load config from {config_path}: {e}, using defaults")
            return {
                "evaluation": {"use_duplicated_pages": False},
                "page_duplication": {"headless": True}
            }
    
    def _validate_config(self):
        """Validate the pipeline configuration."""
        try:
            # Validate notion key
            get_notion_key(self.notion_key)
            
            # Validate model provider
            create_model_provider(
                base_url=self.model_config["base_url"],
                api_key=self.model_config["api_key"],
                model_name=self.model_config["model_name"]
            )
            
            # Validate page duplication config if enabled
            if self.use_page_duplication:
                source_pages = self.config.get("source_pages", {})
                if not source_pages:
                    print("⚠️  Page duplication enabled but no source pages configured")
                else:
                    for category, url in source_pages.items():
                        if "REPLACE_WITH_ACTUAL_PAGE_URL" in url:
                            print(f"⚠️  Source page URL for '{category}' not configured")
            
            print("✅ Configuration validated successfully")
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            sys.exit(1)
    
    async def execute_single_task(self, task: Task) -> TaskResult:
        """Execute a single task and return the result."""
        print(f"🔄 Executing {task.name}...")
        start_time = time.time()
        duplicated_page_id = None
        
        try:
            # Get task description
            task_description = task.get_description()
            if not task_description.strip():
                raise ValueError(f"Task description is empty for {task.name}")
            
            # Handle page duplication if enabled
            if self.use_page_duplication:
                try:
                    print(f"📄 Duplicating source page for {task.name}...")
                    duplicated_url, duplicated_page_id = await self.page_manager.duplicate_page_async(
                        task.category, task.name
                    )
                    
                    # Modify task description with the duplicated page ID
                    if self.template_manager.has_page_id_placeholder(task_description):
                        # Use template replacement
                        task_description = self.template_manager.inject_page_id(
                            task_description, duplicated_page_id, duplicated_url
                        )
                    else:
                        # Convert legacy description
                        task_description = self.template_manager.convert_legacy_description(
                            task_description, duplicated_page_id
                        )
                    
                    print(f"✅ Using duplicated page: {duplicated_page_id}")
                    
                except Exception as e:
                    print(f"⚠️  Page duplication failed: {e}, continuing without duplication")
                    duplicated_page_id = None
            
            # Create temporary instruction file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
                temp_file.write(task_description)
                temp_path = Path(temp_file.name)
            
            try:
                # Setup model provider and MCP server
                custom_model_provider = create_model_provider(
                    base_url=self.model_config["base_url"],
                    api_key=self.model_config["api_key"],
                    model_name=self.model_config["model_name"]
                )
                
                async with await create_mcp_server(self.notion_key) as server:
                    # Build the agent
                    agent = Agent(
                        name="Notion Agent",
                        mcp_servers=[server],
                    )
                    ModelSettings.tool_choice = "required"
                    
                    # Execute the task
                    assistant_response = await asyncio.wait_for(
                        run_single_task(agent, task_description, custom_model_provider),
                        timeout=self.timeout
                    )
                    
                    execution_time = time.time() - start_time
                    
                    # Verify the task result
                    verification_success = await self._verify_task(task, duplicated_page_id)
                    
                    return TaskResult(
                        category=task.category,
                        task_id=task.task_id,
                        task_name=task.name,
                        success=verification_success,
                        execution_time=execution_time,
                        error_message=None if verification_success else "Verification failed"
                    )
            
            finally:
                # Clean up temporary file
                temp_path.unlink(missing_ok=True)
        
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            return TaskResult(
                category=task.category,
                task_id=task.task_id,
                task_name=task.name,
                success=False,
                execution_time=execution_time,
                error_message=f"Task timed out after {self.timeout} seconds"
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            return TaskResult(
                category=task.category,
                task_id=task.task_id,
                task_name=task.name,
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
        
        finally:
            # Clean up duplicated page if it was created
            if duplicated_page_id and self.use_page_duplication:
                try:
                    cleanup_enabled = self.config.get("page_duplication", {}).get("cleanup_on_failure", True)
                    if cleanup_enabled:
                        print(f"🗑️  Cleaning up duplicated page: {duplicated_page_id}")
                        await self.page_manager.delete_page_async(duplicated_page_id)
                except Exception as e:
                    print(f"⚠️  Failed to clean up duplicated page: {e}")
    
    async def _verify_task(self, task: Task, page_id: Optional[str] = None) -> bool:
        """Verify a task result using the existing evaluate.py script."""
        try:
            # Build command with optional page_id
            cmd = [
                sys.executable, 
                "evaluate_with_page_id.py", 
                task.category, 
                str(task.task_id)
            ]
            
            # Add page_id if available and page duplication is enabled
            if page_id and self.use_page_duplication:
                cmd.extend(["--page-id", page_id])
            
            # Run the verification script
            result = subprocess.run(
                cmd,
                capture_output=True, 
                text=True, 
                timeout=60,
                cwd=Path(__file__).parent
            )
            
            # Check if verification was successful (returns 1 for success, 0 for failure)
            return result.returncode == 0 and "1" in result.stdout
            
        except Exception as e:
            print(f"⚠️  Verification failed for {task.name}: {e}")
            return False
    
    def execute_task_sync(self, task: Task) -> TaskResult:
        """Synchronous wrapper for executing a single task."""
        return asyncio.run(self.execute_single_task(task))
    
    async def run_evaluation(self, task_filter: str, parallel: bool = True) -> EvaluationReport:
        """Run the complete evaluation pipeline."""
        print("🚀 Starting MCPBench evaluation pipeline...")
        if self.use_page_duplication:
            print("📄 Page duplication is ENABLED")
        else:
            print("📄 Page duplication is DISABLED")
        
        start_time = datetime.now()
        
        # Discover and filter tasks
        tasks = self.task_manager.filter_tasks(task_filter)
        if not tasks:
            print(f"❌ No tasks found for filter: {task_filter}")
            print("Available options:")
            print(f"  Categories: {', '.join(self.task_manager.get_categories())}")
            print(f"  Use 'all' to run all tasks")
            sys.exit(1)
        
        print(f"📋 Found {len(tasks)} tasks to execute")
        
        # Execute tasks
        task_results = []
        
        # For page duplication, we should run sequentially to avoid browser conflicts
        if self.use_page_duplication and parallel:
            print("⚠️  Page duplication requires sequential execution, overriding parallel setting")
            parallel = False
        
        if parallel and len(tasks) > 1:
            print(f"⚡ Running tasks in parallel (max workers: {self.max_workers})")
            
            # Use ThreadPoolExecutor for parallel execution
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task = {
                    executor.submit(self.execute_task_sync, task): task 
                    for task in tasks
                }
                
                for future in concurrent.futures.as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        task_results.append(result)
                        
                        status_icon = "✅" if result.success else "❌"
                        print(f"{status_icon} {result.task_name} - {result.execution_time:.1f}s")
                        
                    except Exception as e:
                        print(f"❌ {task.name} failed with exception: {e}")
                        task_results.append(TaskResult(
                            category=task.category,
                            task_id=task.task_id,
                            task_name=task.name,
                            success=False,
                            execution_time=0,
                            error_message=str(e)
                        ))
        else:
            print("📈 Running tasks sequentially")
            for i, task in enumerate(tasks, 1):
                print(f"[{i}/{len(tasks)}] Executing {task.name}")
                result = await self.execute_single_task(task)
                task_results.append(result)
                
                status_icon = "✅" if result.success else "❌"
                print(f"{status_icon} {result.task_name} - {result.execution_time:.1f}s")
        
        end_time = datetime.now()
        
        # Calculate statistics
        successful_tasks = sum(1 for r in task_results if r.success)
        failed_tasks = len(task_results) - successful_tasks
        
        # Create evaluation report
        report = EvaluationReport(
            model_name=self.model_name,
            model_config=self.model_config,
            start_time=start_time,
            end_time=end_time,
            total_tasks=len(task_results),
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            task_results=task_results
        )
        
        return report


def main():
    """Main entry point for the evaluation pipeline."""
    parser = argparse.ArgumentParser(
        description="MCPBench Evaluation Pipeline with Page Duplication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate all tasks
  python eval_pipeline_with_duplication.py --model-name gpt-4 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks all
  
  # Evaluate specific category
  python eval_pipeline_with_duplication.py --model-name claude-3 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume
  
  # Evaluate specific task
  python eval_pipeline_with_duplication.py --model-name gpt-3.5-turbo --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume/task_1
  
  # Use environment variables (set in .env file)
  python eval_pipeline_with_duplication.py --tasks all
  
  # Disable page duplication
  python eval_pipeline_with_duplication.py --tasks all --no-page-duplication
        """
    )
    
    # Model configuration
    parser.add_argument("--model-name", help="Model name to evaluate")
    parser.add_argument("--api-key", help="API key for model provider")
    parser.add_argument("--base-url", help="Base URL for model provider")
    parser.add_argument("--notion-key", help="Notion API key")
    
    # Task selection
    parser.add_argument("--tasks", required=True,
                       help="Tasks to run: 'all', category name, or specific task (e.g., 'online_resume/task_1')")
    
    # Execution options
    parser.add_argument("--parallel", action="store_true", default=True,
                       help="Run tasks in parallel (default: True)")
    parser.add_argument("--sequential", action="store_true",
                       help="Run tasks sequentially (overrides --parallel)")
    parser.add_argument("--max-workers", type=int, default=3,
                       help="Maximum number of parallel workers (default: 3)")
    parser.add_argument("--timeout", type=int, default=300,
                       help="Timeout for each task in seconds (default: 300)")
    
    # Page duplication options
    parser.add_argument("--config", type=Path,
                       help="Path to configuration file (default: config.json)")
    parser.add_argument("--no-page-duplication", action="store_true",
                       help="Disable page duplication even if configured")
    
    # Output options
    parser.add_argument("--no-console", action="store_true",
                       help="Disable console output")
    parser.add_argument("--no-json", action="store_true",
                       help="Disable JSON report export")
    parser.add_argument("--no-csv", action="store_true",
                       help="Disable CSV report export")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Handle sequential override
    if args.sequential:
        args.parallel = False
    
    try:
        # Load from environment if not provided
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        model_name = args.model_name or os.getenv("MCPBENCH_MODEL_NAME")
        api_key = args.api_key or os.getenv("MCPBENCH_API_KEY")
        base_url = args.base_url or os.getenv("MCPBENCH_BASE_URL")
        notion_key = args.notion_key or os.getenv("NOTION_API_KEY")
        
        # Initialize pipeline
        pipeline = EvaluationPipeline(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            notion_key=notion_key,
            max_workers=args.max_workers,
            timeout=args.timeout,
            config_path=args.config
        )
        
        # Override page duplication if requested
        if args.no_page_duplication:
            pipeline.use_page_duplication = False
        
        # Run evaluation
        report = asyncio.run(pipeline.run_evaluation(args.tasks, args.parallel))
        
        # Generate reports
        pipeline.reporter.generate_full_report(
            report,
            console=not args.no_console,
            json_export=not args.no_json,
            csv_export=not args.no_csv,
            verbose=args.verbose
        )
        
        # Exit with appropriate code
        exit_code = 0 if report.failed_tasks == 0 else 1
        print(f"\n🎯 Evaluation completed with {report.successful_tasks}/{report.total_tasks} successful tasks")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n🛑 Evaluation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"💥 Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()