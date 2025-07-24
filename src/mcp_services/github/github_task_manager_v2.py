#!/usr/bin/env python3
"""
Simplified GitHub Task Manager using Enhanced Base Class
=========================================================
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass 
class GitHubTask(BaseTask):
    """GitHub-specific task with additional fields."""
    repo_name: Optional[str] = None
    pr_title: Optional[str] = None
    expected_changes: Optional[List[str]] = None


class GitHubTaskManager(BaseTaskManager):
    """Simplified GitHub task manager."""
    
    def __init__(self, tasks_root: Path = None):
        """Initialize GitHub task manager."""
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"
        
        super().__init__(tasks_root, service="github")
    
    # Required abstract methods only
    
    def _get_service_directory_name(self) -> str:
        """Return the service directory name."""
        return "github"
    
    def _get_task_organization(self) -> str:
        """GitHub uses file-based organization."""
        return "file"
    
    def _create_task_instance(self, **kwargs) -> GitHubTask:
        """Create a GitHub-specific task instance."""
        return GitHubTask(**kwargs)
    
    # Optional: GitHub-specific overrides
    
    def _pre_execution_check(self, task: BaseTask) -> Dict[str, Any]:
        """Check if GitHub token is available."""
        import os
        if not os.getenv("GITHUB_TOKEN"):
            return {
                "success": False, 
                "error": "GitHub token not found in environment"
            }
        return {"success": True}