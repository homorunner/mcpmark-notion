#!/usr/bin/env python3
"""
Notion Task Manager for MCPBench Evaluation Pipeline
====================================================

This module provides utilities for discovering, filtering, and managing
evaluation tasks within the MCPBench project structure, as well as executing
Notion API tasks using an MCP-enabled agent with configurable models and environments.
"""

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents import (
    Agent,
    Model,
    ModelProvider,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
    ItemHelpers,
    set_tracing_export_api_key,
)
from agents.mcp.server import MCPServerStdio
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger
from src.results_reporter import TaskResult


logger = get_logger(__name__)

set_tracing_export_api_key(os.getenv("OPENAI_TRACE_API_KEY"))

@dataclass
class NotionTask(BaseTask):
    """Represents a single evaluation task for Notion service."""
    # Additional Notion-specific fields
    original_template_url: Optional[str] = None
    duplicated_template_url: Optional[str] = None
    duplicated_template_id: Optional[str] = None
    
    def __post_init__(self):
        # Ensure base class fields are set if not provided
        if not hasattr(self, 'task_instruction_path') or self.task_instruction_path is None:
            self.task_instruction_path = self.description_path
        if not hasattr(self, 'task_verification_path') or self.task_verification_path is None:
            self.task_verification_path = self.verify_path
    
    @property
    def description_path(self) -> Path:
        """Alias for task_instruction_path."""
        return self.task_instruction_path
    
    @property
    def verify_path(self) -> Path:
        """Alias for task_verification_path."""
        return self.task_verification_path
    
    @property
    def name(self) -> str:
        """Return the full task name."""
        return f"{self.category}/task_{self.task_id}"
    
    def get_description(self) -> str:
        """Read and return the task description."""
        if self.description_path.exists():
            return self.description_path.read_text(encoding="utf-8")
        return ""


class NotionTaskManager(BaseTaskManager):
    """Manages task discovery, filtering, and execution for Notion-based MCPBench evaluation."""
    
    def __init__(self, tasks_root: Path = None, model_name: str = None, api_key: str = None, 
                 base_url: str = None, notion_key: str = None, timeout: int = 600):
        """Initialize with the tasks directory path and execution configuration.
        
        Args:
            tasks_root: Path to the tasks directory
            model_name: Name of the model to use for task execution
            api_key: API key for the model provider
            base_url: Base URL for the model provider
            notion_key: Notion API key
            timeout: Task execution timeout in seconds
        """
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"
        
        # Call parent constructor
        super().__init__(tasks_root, service="notion")
        
        self._tasks_cache = None
        
        # Execution configuration
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.notion_key = notion_key
        self.timeout = timeout
        
        # Initialize model provider if configuration is provided
        self.model_provider = None
        if all([model_name, api_key, base_url]):
            self.model_provider = self._create_model_provider()
        
        # Ensure logs directory exists
        self.logs_dir = Path("./logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Retry configuration for transient network errors (e.g. ETIMEDOUT)
        self.max_retries: int = 3  # total attempts = 1 + (max_retries-1) retries
        self.retry_backoff: float = 5.0  # seconds, will multiply by attempt index for simple back-off
    
    def _create_model_provider(self) -> ModelProvider:
        base_url = self.base_url
        api_key = self.api_key
        model_name = self.model_name
        client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        
        class CustomModelProvider(ModelProvider):
            def get_model(self, model_name_override: str | None) -> Model:
                final_model_name = model_name_override or model_name
                return OpenAIChatCompletionsModel(
                    model=final_model_name, openai_client=client
                )
        
        return CustomModelProvider()
    
    # =========================================================================
    # Task Discovery and Management
    # =========================================================================
    
    def discover_all_tasks(self) -> List[NotionTask]:
        """Discover all available tasks in the tasks directory."""
        if self._tasks_cache is not None:
            return self._tasks_cache
        
        tasks = []
        if not self.tasks_root.exists():
            return tasks
        
        # Navigate to the notion subdirectory
        notion_tasks_root = self.tasks_root / "notion"
        if not notion_tasks_root.exists():
            return tasks
        
        # Iterate through category directories
        for category_dir in notion_tasks_root.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith('.') or category_dir.name == 'utils':
                continue
            
            category = category_dir.name
            
            # Find task directories within each category
            for task_dir in category_dir.iterdir():
                if not task_dir.is_dir() or not task_dir.name.startswith('task_'):
                    continue
                
                try:
                    task_id = int(task_dir.name.split('_')[1])
                except (IndexError, ValueError):
                    continue
                
                description_path = task_dir / "description.md"
                verify_path = task_dir / "verify.py"
                
                # Only include tasks that have both description and verify files
                if description_path.exists() and verify_path.exists():
                    tasks.append(NotionTask(
                        task_instruction_path=description_path,
                        task_verification_path=verify_path,
                        service="notion",
                        category=category,
                        task_id=task_id
                    ))
        
        # Sort tasks by category and task_id for consistent ordering
        tasks.sort(key=lambda t: (t.category, t.task_id))
        self._tasks_cache = tasks
        return tasks
    
    def get_categories(self) -> List[str]:
        """Get all available task categories."""
        tasks = self.discover_all_tasks()
        categories = list(set(task.category for task in tasks))
        return sorted(categories)
    
    def filter_tasks(self, task_filter: str) -> List[NotionTask]:
        """Filter tasks based on the provided filter string."""
        all_tasks = self.discover_all_tasks()
        
        if task_filter.lower() == "all":
            return all_tasks
        
        # Check if it's a category filter
        categories = self.get_categories()
        if task_filter in categories:
            return [task for task in all_tasks if task.category == task_filter]
        
        # Check if it's a specific task filter
        if "/" in task_filter:
            try:
                category, task_part = task_filter.split("/", 1)
                if task_part.startswith("task_"):
                    task_id = int(task_part.split("_")[1])
                    for task in all_tasks:
                        if task.category == category and task.task_id == task_id:
                            return [task]
            except (ValueError, IndexError):
                pass
        
        # If no matches found, return empty list
        return []


    def execute_task(self, task: NotionTask) -> TaskResult:
        """Execute a complete task including verification and cleanup.
        
        Args:
            task: Task object containing task details
            
        Returns:
            TaskResult object with execution results
        """
        logger.info(f"- Executing task: {task.name}")
        start_time = time.time()
        
        # Check if duplication succeeded
        if task.duplicated_template_id is None:
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
            # Prepare task description with template ID
            template_id = str(task.duplicated_template_id)
            task_description = task.get_description() + f"\n\nNote: The ID of the working page/database is `{template_id}`. Check the title and properties of this block; this should be the first step."
            
            # Create temporary task file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(task_description)
                temp_task_path = f.name
            
            try:
                # Run the task
                result = self.run_single_task_file(temp_task_path, timeout=self.timeout)

                # If MCP network error after all retries, bubble up immediately
                if not result["success"] and result.get("error") == "MCP Network Error":
                    execution_time = time.time() - start_time
                    # Clean up duplicated template if needed
                    return TaskResult(
                        task_name=task.name,
                        success=False,
                        execution_time=execution_time,
                        error_message="MCP Network Error",
                        category=task.category,
                        task_id=task.task_id
                    )

                # Run verification
                logger.info(f"- Running verification for task: {task.name}")
                verify_result = subprocess.run(
                    [sys.executable, str(task.verify_path), task.duplicated_template_id],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                # Process results
                success = verify_result.returncode == 0
                error_message = verify_result.stderr if not success and verify_result.stderr else None
                execution_time = time.time() - start_time

                if success:
                    logger.info(f"✓ Verification passed for task: {task.name}")
                else:
                    logger.error(f"✗ Verification failed for task: {task.name}")
                    logger.error(f"⚠️ Error: {error_message}")
                
                
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

    # =========================================================================
    # Task Execution
    # =========================================================================
    
    async def _create_mcp_server(self) -> MCPServerStdio:
        """Create and return an MCP server connection for Notion."""
        return MCPServerStdio(
            params={
                "command": "npx",
                "args": ["-y", "@notionhq/notion-mcp-server"],
                "env": {
                    "OPENAPI_MCP_HEADERS": (
                        '{"Authorization": "Bearer ' + self.notion_key + '", '
                        '"Notion-Version": "2022-06-28"}'
                    )
                },
            },
            client_session_timeout_seconds=120,
            cache_tools_list=True,
        )
    
    def _read_task_file(self, path: Path) -> str:
        """Return the full text content of a file."""
        if not path.exists():
            raise FileNotFoundError(f"Task file '{path}' does not exist")
        
        return path.read_text(encoding="utf-8")
    
    async def _run_single_task_async(self, agent: Agent, task_content: str) -> str:
        """Send task content to agent and stream the response."""
        # Prepare the conversation with a single user message
        conversation = [{"content": task_content, "role": "user"}]
        
        # Run the agent and stream events
        result = Runner.run_streamed(
            agent, 
            max_turns=20, 
            input=conversation, 
            run_config=RunConfig(model_provider=self.model_provider)
        )
        
        # Add a small delay to ensure the background task has started
        await asyncio.sleep(0.1)

        try:
            event_count = 0
            async for event in result.stream_events():
                event_count += 1
                logger.debug(f"Event {event_count}: {event}")
                
                # Check if event has type attribute
                if hasattr(event, 'type'):
                    logger.debug(f"Event type: {event.type}")
                    
                    if event.type == "raw_response_event":
                        if hasattr(event, 'data') and isinstance(event.data, ResponseTextDeltaEvent):
                            # Print token deltas as we receive them
                            delta_text = event.data.delta
                            print(delta_text, end="", flush=True)
                    elif event.type == "run_item_stream_event":
                        if hasattr(event, 'item'):
                            if hasattr(event.item, 'type'):
                                if event.item.type == "tool_call_item":
                                    logger.info(
                                        f"\n-- Calling Tool: {event.item.raw_item.name if hasattr(event.item, 'raw_item') else 'Unknown'}..."
                                    )
                                # elif event.item.type == "tool_call_output_item":
                                #     logger.info(f"-- Tool output: {event.item.output}")
                                # elif event.item.type == "message_output_item":
                                #     logger.info(f"-- Message output:\n {ItemHelpers.text_message_output(event.item)}")
                                else:
                                    pass
            
            logger.info(f"Total events received: {event_count}")
        except Exception as e:
            logger.error(f"Error during streaming: {e}", exc_info=True)
            if result._run_impl_task:
                logger.error(f"Background task exception: {result._run_impl_task.exception()}")
            raise
        
        print()  # Final newline after the assistant's completion
        
        return result.to_input_list()
    
    def _run_single_task_file_once(self, task_file_path: str, timeout: int) -> Dict[str, Any]:
        """Run the task exactly once (helper for retry wrapper)."""
        task_path = Path(task_file_path)

        try:
            async def _run() -> str:
                """Internal coroutine that performs the actual evaluation."""
                async with await self._create_mcp_server() as server:
                    agent = Agent(name="Notion Agent", mcp_servers=[server])
                    ModelSettings.tool_choice = "required"

                    task_content = self._read_task_file(task_path)

                    # Set the Notion API key in environment for the MCP server
                    if self.notion_key:
                        os.environ["NOTION_API_KEY"] = self.notion_key

                    # Delegate to the async implementation to stream the response
                    return await self._run_single_task_async(agent, task_content)

            # Execute with timeout handling
            assistant_response: str = asyncio.run(asyncio.wait_for(_run(), timeout=timeout))

            return {
                "success": True,
                "output": assistant_response,
                "error": None,
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": "",
                "error": f"Task timed out after {timeout} seconds",
            }
        except Exception as exc:
            return {
                "success": False,
                "output": "",
                "error": str(exc),
            }

    def run_single_task_file(self, task_file_path: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute a single task from a file, with automatic retries on transient
        network errors such as ETIMEDOUT or ECONNREFUSED."""

        for attempt in range(1, self.max_retries + 1):
            result = self._run_single_task_file_once(task_file_path, timeout)

            # Success – return immediately
            if result["success"]:
                return result

            # Check for transient network error keywords
            error_msg = result["error"] or ""
            transient = any(code in error_msg for code in ("ETIMEDOUT", "ECONNREFUSED"))

            if transient and attempt < self.max_retries:
                wait_seconds = self.retry_backoff * attempt
                logger.warning(
                    f"[Retry] Attempt {attempt}/{self.max_retries} failed with transient network error. "
                    f"Waiting {wait_seconds}s before retrying…"
                )
                time.sleep(wait_seconds)
                continue  # Retry

            # Out of retries on transient error → normalize error message for callers
            if transient:
                result["error"] = "MCP Network Error"
            # Non-transient error or out of retry attempts – return last result
            return result