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

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NotionTask(BaseTask):
    """Represents a single evaluation task for Notion service."""

    # Additional Notion-specific fields
    original_initial_state_url: Optional[str] = None
    duplicated_initial_state_url: Optional[str] = None
    duplicated_initial_state_id: Optional[str] = None

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


    # =========================================================================
    # Service-specific implementations for template methods
    # =========================================================================

    def _get_service_directory_name(self) -> str:
        """Return the service directory name for Notion."""
        return "notion"

    def _find_task_files(self, category_dir: Path) -> List[Dict[str, Any]]:
        """Find task files in Notion category directory.

        Notion tasks are organized as task_X directories with description.md and verify.py.
        """
        task_files = []

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
                task_files.append({
                    "task_id": task_id,
                    "instruction_path": description_path,
                    "verification_path": verify_path
                })

        return task_files

    def _create_task_from_files(self, category_name: str, task_files_info: Dict[str, Any]) -> Optional[NotionTask]:
        """Create a NotionTask from file information."""
        return NotionTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="notion",
            category=category_name,
            task_id=task_files_info["task_id"],
        )

    def _get_verification_command(self, task: NotionTask) -> List[str]:
        """Get the verification command for Notion tasks.

        Notion verification requires the duplicated template ID.
        """
        return [
            sys.executable,
            str(task.task_verification_path),
            task.duplicated_initial_state_id or "",
        ]

    def _format_task_instruction(self, base_instruction: str) -> str:
        """Format task instruction with Notion-specific additions."""
        return base_instruction + "\n\nNote: Based on your understanding, solve the task all at once by yourself, don't ask for my opinions on anything."

    def _pre_execution_check(self, task: NotionTask) -> Dict[str, Any]:
        """Check if duplication succeeded before execution."""
        if task.duplicated_initial_state_id is None:
            return {
                "success": False,
                "error": "Duplication failed"
            }
        return {"success": True}

    # Note: execute_task and get_task_instruction are now implemented in the base class
    # Service-specific behavior is handled through the template methods above
