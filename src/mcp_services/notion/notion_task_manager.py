#!/usr/bin/env python3
"""
Notion Task Manager for MCPBench Evaluation Pipeline
====================================================

This module provides utilities for discovering, filtering, and managing
evaluation tasks within the MCPBench project structure for Notion service.

The task manager is responsible for:
- Task discovery and filtering
- Task verification and result processing
- Task-specific logic (NOT LLM execution)
"""

import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger
from src.results_reporter import TaskResult

logger = get_logger(__name__)


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
    """Manages task discovery, filtering, and verification for Notion-based MCPBench evaluation."""

    def __init__(self, tasks_root: Path = None):
        """Initialize with the tasks directory path.

        Args:
            tasks_root: Path to the tasks directory
        """
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"

        # Call parent constructor
        super().__init__(tasks_root, service="notion")

        self._tasks_cache = None


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
            if (
                not category_dir.is_dir()
                or category_dir.name.startswith(".")
                or category_dir.name == "utils"
            ):
                continue

            category = category_dir.name

            # Find task directories within each category
            for task_dir in category_dir.iterdir():
                if not task_dir.is_dir() or not task_dir.name.startswith("task_"):
                    continue

                try:
                    task_id = int(task_dir.name.split("_")[1])
                except (IndexError, ValueError):
                    continue

                description_path = task_dir / "description.md"
                verify_path = task_dir / "verify.py"

                # Only include tasks that have both description and verify files
                if description_path.exists() and verify_path.exists():
                    tasks.append(
                        NotionTask(
                            task_instruction_path=description_path,
                            task_verification_path=verify_path,
                            service="notion",
                            category=category,
                            task_id=task_id,
                        )
                    )

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

    def execute_task(self, task: NotionTask, agent_result: Dict[str, Any]) -> TaskResult:
        """Execute task verification using the result from agent execution.

        Args:
            task: Task object containing task details
            agent_result: Result from agent execution containing success, output, token_usage, etc.

        Returns:
            TaskResult object with execution results
        """
        logger.info(f"- Verifying task: {task.name}")
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
                task_id=task.task_id,
            )

        try:
            # If agent execution failed, return the failure
            if not agent_result.get("success", False):
                execution_time = time.time() - start_time
                error_message = agent_result.get("error", "Agent execution failed")
                
                # Check for MCP network errors
                if "MCP" in error_message or "Error invoking MCP" in error_message:
                    error_message = "MCP Network Error"
                    
                return TaskResult(
                    task_name=task.name,
                    success=False,
                    execution_time=execution_time,
                    error_message=error_message,
                    category=task.category,
                    task_id=task.task_id,
                )

            # Run verification
            logger.info(f"- Running verification for task: {task.name}")
            verify_result = subprocess.run(
                [
                    sys.executable,
                    str(task.verify_path),
                    task.duplicated_template_id,
                ],
                capture_output=True,
                text=True,
                timeout=90,
            )

            # Process results
            success = verify_result.returncode == 0
            error_message = (
                verify_result.stderr
                if not success and verify_result.stderr
                else None
            )
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
                model_output=agent_result.get("output", ""),
                category=task.category,
                task_id=task.task_id,
                token_usage=agent_result.get("token_usage", {}),
                turn_count=agent_result.get("turn_count", -1),
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Task verification failed: {str(e)}"

            return TaskResult(
                task_name=task.name,
                success=False,
                execution_time=execution_time,
                error_message=error_msg,
                category=task.category,
                task_id=task.task_id,
            )

    def get_task_instruction(self, task: NotionTask) -> str:
        """Get the formatted task instruction for agent execution.
        
        Args:
            task: The task to get instruction for
            
        Returns:
            Formatted task instruction string
        """
        base_instruction = task.get_description()
        return base_instruction + "\n\nNote: Based on your understanding, solve the task all at once by yourself, don't ask for my opinions on anything."
