"""
GitHub Task Manager for MCPBench Evaluation Pipeline
====================================================

This module provides utilities for discovering, filtering, and managing
GitHub-based evaluation tasks.

The task manager is responsible for:
- Task discovery and filtering
- Task verification and result processing
- Task-specific logic (NOT LLM execution)
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger

logger = get_logger(__name__)

@dataclass
class GitHubTask(BaseTask):
    """Represents a single evaluation task for GitHub service."""
    # GitHub-specific fields
    repository_url: Optional[str] = None
    branch_name: Optional[str] = None
    pr_number: Optional[int] = None
    issue_number: Optional[int] = None
    expected_actions: Optional[List[str]] = None  # Expected GitHub actions to verify

    # Directory-based task slug (e.g., "update_readme")
    task_name: str = ""

    @property
    def name(self) -> str:
        """Return the full task name.

        When a human–readable slug (task_name) is available we prefer it, otherwise we
        fall back to the legacy numeric style kept in `task_id`.
        """
        if self.task_name:
            return f"{self.category}/{self.task_name}"
        return f"{self.category}/task_{self.task_id}"


class GitHubTaskManager(BaseTaskManager):
    """Manages task discovery, filtering, and verification for GitHub-based MCPBench evaluation."""

    def __init__(self, tasks_root: Path = None):
        """Initialize GitHub task manager.

        Args:
            tasks_root: Path to the tasks directory
        """
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"

        # Call parent constructor
        super().__init__(tasks_root, service="github", task_class=GitHubTask,
                         task_organization="file")  # GitHub uses file-based tasks


    # =========================================================================
    # Service-specific implementations
    # =========================================================================
    # No custom task discovery methods needed; relying entirely on BaseTaskManager defaults.

    def _create_task_from_files(self, category_name: str, task_files_info: Dict[str, Any]) -> Optional[GitHubTask]:
        """Instantiate a GitHubTask from the dictionary yielded by _find_task_files."""

        return GitHubTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="github",
            category=category_name,
            task_id=task_files_info["task_name"],  # keep compatibility with BaseTask
            task_name=task_files_info["task_name"],
        )

    def _get_verification_command(self, task: GitHubTask) -> List[str]:
        """Get the verification command for GitHub tasks."""
        return [sys.executable, str(task.task_verification_path)]

    def _format_task_instruction(self, base_instruction: str) -> str:
        """Format task instruction with GitHub-specific additions."""
        return base_instruction + "\n\nNote: Use GitHub tools to complete this task. Work systematically and verify your actions."

    def _post_execution_hook(self, task: GitHubTask, success: bool) -> None:
        """Track created repositories for cleanup if needed."""
        if task.category == 'basic_repo_operations' and success:
            self._track_created_repositories_from_verification(task)

    def _track_created_repositories_from_verification(self, task: GitHubTask):
        """Track created repositories from verification for cleanup."""
        try:
            # For basic repository operations, track default repository names
            if 'task_1' in str(task.task_id):  # Task 1 creates mcpbench-test-repo
                from src.factory import MCPServiceFactory
                state_manager = MCPServiceFactory.create_state_manager('github')
                state_manager.track_created_repository('mcpbench-test-repo')
                logger.info("Tracked repository 'mcpbench-test-repo' for cleanup")
        except Exception as e:
            logger.warning(f"Failed to track created repositories: {e}")


    # Note: execute_task and get_task_instruction are now implemented in the base class
    # Service-specific behavior is handled through the template methods above
