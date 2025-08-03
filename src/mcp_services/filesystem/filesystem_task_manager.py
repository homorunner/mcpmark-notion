"""
Simplified Filesystem Task Manager using Enhanced Base Class
============================================================

This module shows how the filesystem task manager can be simplified
using the enhanced base task manager.
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FilesystemTask(BaseTask):
    """Filesystem-specific task with additional fields."""
    test_directory: Optional[str] = None
    expected_files: Optional[List[str]] = None
    expected_directories: Optional[List[str]] = None


class FilesystemTaskManager(BaseTaskManager):
    """Simplified filesystem task manager using enhanced base class."""

    def __init__(self, tasks_root: Path = None):
        """Initialize filesystem task manager."""
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"

        super().__init__(tasks_root, service="filesystem", task_class=FilesystemTask,
                         task_organization="directory")

    # Override only what's needed for filesystem-specific behavior
    def _create_task_from_files(self, category_name: str, task_files_info: Dict[str, Any]) -> BaseTask:
        """Instantiate a `BaseTask` from the dictionary returned by `_find_task_files`."""
        # Extract numeric ID from folder name like "task_1" so that the default
        # `BaseTask.name` ("{category}/task_{task_id}") matches the original path
        # pattern used by the CLI filter, e.g. "form_interaction/task_1".
        try:
            task_id = int(task_files_info["task_name"].split("_")[1])
        except (IndexError, ValueError):
            # Fallback to entire slug when it is not in the expected format
            task_id = task_files_info["task_name"]

        return BaseTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="playwright",
            category=category_name,
            task_id=task_id,
        )
        
    def run_verification(self, task: BaseTask) -> subprocess.CompletedProcess:
        """Run verification with filesystem-specific environment."""
        env = os.environ.copy()

        # Pass test directory to verification script
        # Priority: task.test_directory (set by state manager) > environment variable
        test_dir = None
        if hasattr(task, 'test_directory') and task.test_directory:
            test_dir = task.test_directory
        else:
            test_dir = os.getenv('FILESYSTEM_TEST_DIR')

        if test_dir:
            env['FILESYSTEM_TEST_DIR'] = test_dir
            logger.debug(f"Setting FILESYSTEM_TEST_DIR to: {test_dir}")

        return subprocess.run(
            self._get_verification_command(task),
            capture_output=True,
            text=True,
            timeout=90,
            env=env
        )
