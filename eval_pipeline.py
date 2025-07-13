#!/usr/bin/env python3
"""
MCPBench Evaluation Pipeline
===========================

Automatic evaluation pipeline for testing LLM models on Notion API tasks.

Usage:
    python eval_pipeline.py --model-name gpt-4 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks all
    python eval_pipeline.py --model-name claude-3 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume
    python eval_pipeline.py --model-name gpt-3.5-turbo --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume/task_1
"""

import argparse
import asyncio
import sys
import time
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# Import our custom modules
from task_manager import TaskManager, Task
from results_reporter import ResultsReporter, EvaluationReport, TaskResult
from mcp_utils import get_notion_key, create_model_provider, create_mcp_server
from notion_task_runner import run_single_task, read_task_file
from agents import Agent, ModelSettings


class EvaluationPipeline:
    """Main evaluation pipeline for MCPBench."""
    
    def __init__(self, 
                 model_name: str,
                 api_key: str,
                 base_url: str,
                 notion_key: str,
                 max_workers: int = 3,
                 timeout: int = 300):
        """Initialize the evaluation pipeline.
        
        Args:
            model_name: Name of the model to evaluate
            api_key: API key for model provider
            base_url: Base URL for model provider
            notion_key: Notion API key
            max_workers: Maximum number of parallel task executions
            timeout: Timeout for each task execution in seconds
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
        
        # Validate configuration
        self._validate_config()
    
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
            
            print("✅ Configuration validated successfully")
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            sys.exit(1)
    
    async def execute_single_task(self, task: Task) -> TaskResult:
        """Execute a single task and return the result."""
        print(f"🔄 Executing {task.name}...")
        start_time = time.time()
        
        try:
            # Create a temporary instruction file for this task
            task_description = task.get_description()
            if not task_description.strip():
                raise ValueError(f"Task description is empty for {task.name}")
            
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
                    verification_success = await self._verify_task(task)
                    
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
    
    async def _verify_task(self, task: Task) -> bool:
        """Verify a task result using the existing evaluate.py script."""
        try:
            # Run the verification script
            result = subprocess.run([
                sys.executable, 
                "evaluate.py", 
                task.category, 
                str(task.task_id)
            ], 
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
        description="MCPBench Evaluation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate all tasks
  python eval_pipeline.py --model-name gpt-4 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks all
  
  # Evaluate specific category
  python eval_pipeline.py --model-name claude-3 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume
  
  # Evaluate specific task
  python eval_pipeline.py --model-name gpt-3.5-turbo --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume/task_1
  
  # Use environment variables (set in .env file)
  python eval_pipeline.py --tasks all
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
            timeout=args.timeout
        )
        
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