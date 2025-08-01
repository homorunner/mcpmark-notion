"""
Simplified Task Manager for Demo
================================

This module provides a minimal task manager that allows manual task selection
and verification execution without the complexity of automatic discovery.
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DemoTask:
    """Represents a single evaluation task."""
    
    def __init__(self, category: str, task_id: int, base_path: Path):
        self.category = category
        self.task_id = task_id
        self.name = f"{category}/task_{task_id}"
        self.base_path = base_path
        
        # Paths to task files
        self.task_dir = base_path / "tasks" / "notion" / category / f"task_{task_id}"
        self.description_path = self.task_dir / "description.md"
        self.verify_path = self.task_dir / "verify.py"
    
    def get_description(self) -> str:
        """Read and return the task description."""
        if self.description_path.exists():
            return self.description_path.read_text(encoding="utf-8")
        return f"Description not found for {self.name}"
    
    def exists(self) -> bool:
        """Check if task files exist."""
        return self.description_path.exists() and self.verify_path.exists()


class DemoTaskManager:
    """Simplified task manager for demonstration."""
    
    def __init__(self, base_path: Path = None):
        """Initialize with the project root path."""
        if base_path is None:
            # Assume we're in presentation/, go up one level
            base_path = Path(__file__).resolve().parent.parent
        self.base_path = base_path
    
    def get_available_tasks(self) -> List[Dict[str, str]]:
        """Get a list of available tasks for the UI."""
        # Hardcode some common tasks for demo
        tasks = [
            {"value": "habit_tracker/task_1", "label": "Habit Tracker - Add habit and mark days"},
            {"value": "habit_tracker/task_2", "label": "Habit Tracker - Mark specific days"},
            {"value": "job_applications/task_1", "label": "Job Applications - Add Google application"},
            {"value": "team_projects/task_1", "label": "Team Projects - Update project status"},
            {"value": "online_resume/task_1", "label": "Online Resume - Add work experience"},
        ]
        
        # Filter to only include tasks that actually exist
        existing_tasks = []
        for task_info in tasks:
            category, task_part = task_info["value"].split("/")
            task_id = int(task_part.split("_")[1])
            task = self.get_task(category, task_id)
            if task and task.exists():
                existing_tasks.append(task_info)
        
        return existing_tasks
    
    def get_task(self, category: str, task_id: int) -> Optional[DemoTask]:
        """Get a specific task."""
        task = DemoTask(category, task_id, self.base_path)
        if task.exists():
            return task
        return None
    
    def get_task_by_name(self, task_name: str) -> Optional[DemoTask]:
        """Get a task by its full name (e.g., 'habit_tracker/task_1')."""
        try:
            category, task_part = task_name.split("/")
            task_id = int(task_part.split("_")[1])
            return self.get_task(category, task_id)
        except (ValueError, IndexError):
            return None
    
    def run_verification(self, task: DemoTask, page_id: str, notion_api_key: str = None) -> Tuple[bool, str]:
        """Run the verification script for a task.
        
        Args:
            task: The task to verify
            page_id: The Notion page ID to verify against
            notion_api_key: Optional Notion API key to pass to verification script
            
        Returns:
            Tuple of (success: bool, output: str)
        """
        try:
            # Set up environment with Notion API key if provided
            env = os.environ.copy()
            if notion_api_key:
                env["EVAL_NOTION_API_KEY"] = notion_api_key
            
            # Run verification script with page_id as argument
            result = subprocess.run(
                [sys.executable, str(task.verify_path), page_id],
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )
            
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, "Verification script timed out after 30 seconds"
        except Exception as e:
            return False, f"Error running verification: {str(e)}"