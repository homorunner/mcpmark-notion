#!/usr/bin/env python3
"""
Task Manager for MCPBench Evaluation Pipeline
============================================

This module provides utilities for discovering, filtering, and managing
evaluation tasks within the MCPBench project structure.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Task:
    """Represents a single evaluation task."""
    category: str
    task_id: int
    description_path: Path
    verify_path: Path
    original_template_url: Optional[str] = None
    duplicated_template_url: Optional[str] = None
    duplicated_template_id: Optional[str] = None
    
    @property
    def name(self) -> str:
        """Return the full task name."""
        return f"{self.category}/task_{self.task_id}"
    
    def get_description(self) -> str:
        """Read and return the task description."""
        if self.description_path.exists():
            return self.description_path.read_text(encoding="utf-8")
        return ""
    

class TaskManager:
    """Manages task discovery and filtering for MCPBench evaluation."""
    
    def __init__(self, tasks_root: Path = None):
        """Initialize with the tasks directory path."""
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[2] / "tasks"
        self.tasks_root = Path(tasks_root)
        self._tasks_cache = None
    
    def discover_all_tasks(self) -> List[Task]:
        """Discover all available tasks in the tasks directory."""
        if self._tasks_cache is not None:
            return self._tasks_cache
        
        tasks = []
        if not self.tasks_root.exists():
            return tasks
        
        # Iterate through category directories
        for category_dir in self.tasks_root.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith('.') or category_dir.name == 'utils':
                continue
            
            category = category_dir.name
            
            # Find task directories within each category
            for task_dir in category_dir.iterdir():
                if not task_dir.is_dir() or not task_dir.name.startswith('task_'):
                    continue
                
                try:
                    task_id = int(task_dir.name.split('_')[1])
                except (IndexError, ValueError):
                    continue
                
                description_path = task_dir / "description.md"
                verify_path = task_dir / "verify.py"
                
                # Only include tasks that have both description and verify files
                if description_path.exists() and verify_path.exists():
                    tasks.append(Task(
                        category=category,
                        task_id=task_id,
                        description_path=description_path,
                        verify_path=verify_path
                    ))
        
        # Sort tasks by category and task_id for consistent ordering
        tasks.sort(key=lambda t: (t.category, t.task_id))
        self._tasks_cache = tasks
        return tasks
    
    def get_categories(self) -> List[str]:
        """Get all available task categories."""
        tasks = self.discover_all_tasks()
        categories = list(set(task.category for task in tasks))
        return sorted(categories)
    
    def filter_tasks(self, task_filter: str) -> List[Task]:
        """Filter tasks based on the provided filter string.
        
        Args:
            task_filter: Can be:
                - "all": return all tasks
                - category name (e.g., "online_resume"): return all tasks in category
                - specific task (e.g., "online_resume/task_1"): return single task
        
        Returns:
            List of filtered tasks
        """
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