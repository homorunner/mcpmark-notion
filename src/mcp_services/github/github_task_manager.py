#!/usr/bin/env python3
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
        super().__init__(tasks_root, service="github")
    
    
    # =========================================================================
    # Service-specific implementations for template methods
    # =========================================================================
    
    def _get_service_directory_name(self) -> str:
        """Return the service directory name for GitHub."""
        return "github"
    
    def _get_task_organization(self) -> str:
        """GitHub uses directory-based task organization."""
        return "directory"
    
    def _create_task_instance(self, **kwargs) -> GitHubTask:
        """Create a GitHub task instance."""
        return GitHubTask(**kwargs)
    
    def _find_task_files(self, category_dir: Path) -> List[Dict[str, Any]]:
        """Find task files in GitHub category directory.
        
        GitHub tasks are organized as task_X.md files with task_X_verify.py scripts.
        """
        task_files = []
        
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
            
            task_files.append({
                "task_id": task_id,
                "instruction_path": task_file,
                "verification_path": verify_file
            })
        
        return task_files
    
    def _extract_task_id(self, filename: str) -> Optional[int]:
        """Extract task ID from filename like 'task_1.md'."""
        import re
        match = re.match(r'task_(\d+)\.md', filename)
        return int(match.group(1)) if match else None
    
    def _create_task_from_files(self, category_name: str, task_files_info: Dict[str, Any]) -> Optional[GitHubTask]:
        """Create a GitHubTask from file information."""
        return GitHubTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="github",
            category=category_name,
            task_id=task_files_info["task_id"]
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