#!/usr/bin/env python3
"""
Filesystem Task Manager for MCPBench Evaluation Pipeline
========================================================

This module provides utilities for discovering, filtering, and managing
filesystem-based evaluation tasks using the filesystem MCP server.
"""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FilesystemTask(BaseTask):
    """Represents a single evaluation task for filesystem service."""
    # Filesystem-specific fields
    test_directory: Optional[str] = None
    expected_files: Optional[List[str]] = None
    expected_directories: Optional[List[str]] = None


class FilesystemTaskManager(BaseTaskManager):
    """Manages task discovery and verification for filesystem-based MCPBench evaluation."""
    
    def __init__(self, tasks_root: Path = None):
        """Initialize filesystem task manager.
        
        Args:
            tasks_root: Path to the tasks directory
        """
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"
        
        # Call parent constructor
        super().__init__(tasks_root, service="filesystem")
        
        self._tasks_cache = None
    
    # =========================================================================
    # Abstract Method Implementations
    # =========================================================================
    
    def _get_service_directory_name(self) -> str:
        """Get the service directory name."""
        return "filesystem"
    
    def _is_valid_category_dir(self, category_dir: Path) -> bool:
        """Check if a directory is a valid category directory."""
        return category_dir.is_dir() and not category_dir.name.startswith('.')
    
    def _find_task_files(self, category_dir: Path) -> List[Dict[str, Any]]:
        """Find task files in a category directory.
        
        Returns list of dicts with 'description' and 'verification' paths.
        """
        task_files = []
        
        # Look for task_*.md files
        for task_file in sorted(category_dir.glob("task_*.md")):
            task_id = self._extract_task_id(task_file.name)
            if task_id is None:
                continue
            
            # Look for corresponding verification script
            verify_file = task_file.parent / f"task_{task_id}_verify.py"
            if not verify_file.exists():
                logger.warning("No verification script found for task: %s", task_file)
                continue
            
            task_files.append({
                'description': task_file,
                'verification': verify_file,
                'task_id': task_id
            })
        
        return task_files
    
    def _create_task_from_files(self, category_name: str, task_files_info: Dict[str, Any]) -> Optional[FilesystemTask]:
        """Create a FilesystemTask from file information."""
        return FilesystemTask(
            task_instruction_path=task_files_info['description'],
            task_verification_path=task_files_info['verification'],
            service="filesystem",
            category=category_name,
            task_id=task_files_info['task_id']
        )
    
    def _extract_task_id(self, filename: str) -> Optional[int]:
        """Extract task ID from filename like 'task_1.md'."""
        import re
        match = re.match(r'task_(\d+)\.md', filename)
        return int(match.group(1)) if match else None
    
    def _read_task_instruction(self, task: BaseTask) -> str:
        """Read and return the task instruction content."""
        if not task.task_instruction_path.exists():
            raise FileNotFoundError(f"Task file '{task.task_instruction_path}' does not exist")
        return task.task_instruction_path.read_text(encoding="utf-8")
    
    def _format_task_instruction(self, instruction_content: str) -> str:
        """Format the task instruction with any service-specific additions."""
        # For filesystem tasks, we don't need to add anything special
        # The state manager will handle setting up the test directory
        return instruction_content
    
    def _get_verification_command(self, task: BaseTask) -> List[str]:
        """Get the command to run task verification."""
        return [sys.executable, str(task.task_verification_path)]
    
    def _pre_execution_check(self, task: BaseTask) -> Dict[str, Any]:
        """Perform any pre-execution checks."""
        # No special pre-execution checks needed for filesystem
        return {"success": True}
    
    def _post_execution_hook(self, task: BaseTask, success: bool) -> None:
        """Perform any post-execution actions."""
        # No special post-execution actions needed for filesystem
        pass
    
    # =========================================================================
    # Legacy compatibility methods (will be removed in future)
    # =========================================================================
    
    def discover_all_tasks(self) -> List[FilesystemTask]:
        """Discover all available filesystem tasks in the tasks directory."""
        if self._tasks_cache is not None:
            return self._tasks_cache
        
        tasks = []
        if not self.tasks_root.exists():
            logger.warning("Tasks root directory does not exist: %s", self.tasks_root)
            return tasks
        
        # Look for filesystem service directory
        filesystem_tasks_dir = self.tasks_root / "filesystem"
        if not filesystem_tasks_dir.exists():
            logger.warning("Filesystem tasks directory does not exist: %s", filesystem_tasks_dir)
            return tasks
        
        # Scan categories
        for category_dir in filesystem_tasks_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            category_name = category_dir.name
            logger.info("Discovering tasks in category: %s", category_name)
            
            # Find all task files in this category
            for task_file in category_dir.glob("task_*.md"):
                task_id = self._extract_task_id(task_file.name)
                if task_id is None:
                    continue
                
                # Look for corresponding verification script
                verify_file = task_file.parent / f"task_{task_id}_verify.py"
                if not verify_file.exists():
                    logger.warning("No verification script found for task: %s", task_file)
                    continue
                
                task = FilesystemTask(
                    task_instruction_path=task_file,
                    task_verification_path=verify_file,
                    service="filesystem",
                    category=category_name,
                    task_id=task_id
                )
                tasks.append(task)
                logger.debug("Found task: %s", task.name)
        
        self._tasks_cache = sorted(tasks, key=lambda t: (t.category, t.task_id))
        logger.info("Discovered %d filesystem tasks across all categories", len(self._tasks_cache))
        return self._tasks_cache
    
    def run_verification(self, task: BaseTask) -> subprocess.CompletedProcess:
        """Run the verification script for a task.
        
        This method provides filesystem-specific environment variables to the verification script.
        """
        # Set environment variable for test directory if available
        env = os.environ.copy()
        
        # Get the test directory from state manager or environment
        test_dir = os.getenv('FILESYSTEM_TEST_DIR')
        if test_dir:
            env['FILESYSTEM_TEST_DIR'] = test_dir
            logger.debug(f"Setting FILESYSTEM_TEST_DIR to: {test_dir}")
        
        # Run verification with filesystem-specific environment
        return subprocess.run(
            self._get_verification_command(task),
            capture_output=True,
            text=True,
            timeout=90,
            env=env
        )