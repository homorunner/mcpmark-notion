"""
Simplified Task Manager for Demo
================================

This module provides a minimal task manager that allows manual task selection
and verification execution without the complexity of automatic discovery.
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DemoTask:
    """Represents a single evaluation task."""
    
    def __init__(self, category: str, task_name: str, base_path: Path):
        self.category = category
        self.task_name = task_name
        self.name = f"{category}/{task_name}"
        self.base_path = base_path
        
        # Paths to task files
        self.task_dir = base_path / "tasks" / "notion" / category / task_name
        self.description_path = self.task_dir / "description.md"
        self.verify_path = self.task_dir / "verify.py"
        self.meta_path = self.task_dir / "meta.json"
    
    def get_description(self) -> str:
        """Read and return the task description."""
        if self.description_path.exists():
            return self.description_path.read_text(encoding="utf-8")
        return f"Description not found for {self.name}"
    
    def exists(self) -> bool:
        """Check if task files exist."""
        return (self.description_path.exists() and 
                self.verify_path.exists() and 
                self.meta_path.exists())
    
    def get_template_url(self) -> Optional[str]:
        """Read and return the Notion template URL from meta.json."""
        if self.meta_path.exists():
            try:
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)
                return meta_data.get('ori_template_url')
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def get_gt_page_url(self) -> Optional[str]:
        """Read and return the ground truth page URL from meta.json."""
        if self.meta_path.exists():
            try:
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)
                return meta_data.get('gt_page_url')
            except (json.JSONDecodeError, IOError):
                return None
        return None


class DemoTaskManager:
    """Simplified task manager for demonstration."""
    
    def __init__(self, base_path: Path = None):
        """Initialize with the project root path."""
        if base_path is None:
            # Assume we're in presentation/, go up one level
            base_path = Path(__file__).resolve().parent.parent
        self.base_path = base_path
    
    def get_available_tasks(self) -> List[Dict[str, str]]:
        """Get a list of available tasks for the UI by parsing tasks/notion directory."""
        tasks = []
        notion_tasks_dir = self.base_path / "tasks" / "notion"
        
        if not notion_tasks_dir.exists():
            return tasks
            
        # Iterate through each category directory
        for category_dir in notion_tasks_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            category_name = category_dir.name
            
            # Iterate through each task directory in the category
            for task_dir in category_dir.iterdir():
                if not task_dir.is_dir():
                    continue
                    
                task_name = task_dir.name
                meta_file = task_dir / "meta.json"
                description_file = task_dir / "description.md"
                verify_file = task_dir / "verify.py"
                
                # Only include tasks that have all required files
                if meta_file.exists() and description_file.exists() and verify_file.exists():
                    try:
                        # Read meta.json to get task information
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            meta_data = json.load(f)
                        
                        # Create a readable label from category and task name
                        category_label = category_name.replace('_', ' ').title()
                        task_label = task_name.replace('_', ' ').title()
                        
                        # Check if meta has tags for better description
                        if 'tags' in meta_data and meta_data['tags']:
                            tag_desc = ', '.join(meta_data['tags'][:2])  # Use first 2 tags
                            label = f"{category_label} - {task_label} ({tag_desc})"
                        else:
                            label = f"{category_label} - {task_label}"
                        
                        tasks.append({
                            "value": f"{category_name}/{task_name}",
                            "label": label
                        })
                        
                    except (json.JSONDecodeError, KeyError, IOError):
                        # Skip tasks with invalid meta.json
                        continue
        
        # Sort tasks by category and then by task name for consistent ordering
        tasks.sort(key=lambda x: x["value"])
        return tasks
    
    def get_task(self, category: str, task_name: str) -> Optional[DemoTask]:
        """Get a specific task."""
        task = DemoTask(category, task_name, self.base_path)
        if task.exists():
            return task
        return None
    
    def get_task_by_name(self, full_task_name: str) -> Optional[DemoTask]:
        """Get a task by its full name (e.g., 'online_resume/work_history_addition')."""
        try:
            category, task_name = full_task_name.split("/", 1)
            return self.get_task(category, task_name)
        except ValueError:
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