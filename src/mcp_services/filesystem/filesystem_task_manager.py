#!/usr/bin/env python3
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
from typing import List, Optional

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
    """Simplified filesystem task manager - only 50 lines!"""
    
    def __init__(self, tasks_root: Path = None):
        """Initialize filesystem task manager."""
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"
        
        super().__init__(tasks_root, service="filesystem")
    
    # Required abstract methods only
    
    def _get_service_directory_name(self) -> str:
        """Return the service directory name."""
        return "filesystem"
    
    def _get_task_organization(self) -> str:
        """Filesystem uses file-based organization."""
        return "file"
    
    def _create_task_instance(self, **kwargs) -> FilesystemTask:
        """Create a filesystem-specific task instance."""
        return FilesystemTask(**kwargs)
    
    # Optional: Override only what's needed
    
    def run_verification(self, task: BaseTask) -> subprocess.CompletedProcess:
        """Run verification with filesystem-specific environment."""
        env = os.environ.copy()
        
        # Pass test directory to verification script
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