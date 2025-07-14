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
    
    @property
    def name(self) -> str:
        """Return the full task name."""
        return f"{self.category}/task_{self.task_id}"
    
    def get_description(self) -> str:
        """Read and return the task description."""
        if self.description_path.exists():
            return self.description_path.read_text(encoding="utf-8")
        return ""

    # ------------------------------------------------------------------
    # Backwards-compatibility helpers (legacy pipeline expects these attrs)
    # ------------------------------------------------------------------

    @property
    def description(self) -> str:  # noqa: D401 – kept for compatibility
        """Alias for :py:meth:`get_description` (legacy attribute)."""
        return self.get_description()

    @property
    def verify_script(self) -> Path:  # noqa: D401 – kept for compatibility
        """Alias for :py:attr:`verify_path` (legacy attribute)."""
        return self.verify_path

    @property
    def description_file(self) -> Path:  # noqa: D401 – legacy alias
        """Alias for :py:attr:`description_path` expected by some scripts."""
        return self.description_path


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
    
    def get_task_summary(self) -> Dict[str, int]:
        """Get a summary of tasks by category."""
        tasks = self.discover_all_tasks()
        summary = {}
        
        for task in tasks:
            if task.category not in summary:
                summary[task.category] = 0
            summary[task.category] += 1
        
        return summary
    
    def validate_task_structure(self) -> List[str]:
        """Validate the task directory structure and return any issues."""
        issues = []
        
        if not self.tasks_root.exists():
            issues.append(f"Tasks root directory does not exist: {self.tasks_root}")
            return issues
        
        # Check each category directory
        for category_dir in self.tasks_root.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith('.') or category_dir.name == 'utils':
                continue
            
            category = category_dir.name
            
            # Check for task directories
            task_dirs = [d for d in category_dir.iterdir() if d.is_dir() and d.name.startswith('task_')]
            
            if not task_dirs:
                issues.append(f"No task directories found in category: {category}")
                continue
            
            for task_dir in task_dirs:
                task_name = f"{category}/{task_dir.name}"
                
                # Check for required files
                description_path = task_dir / "description.md"
                verify_path = task_dir / "verify.py"
                
                if not description_path.exists():
                    issues.append(f"Missing description.md in {task_name}")
                
                if not verify_path.exists():
                    issues.append(f"Missing verify.py in {task_name}")
        
        return issues


def main():
    """Example usage of TaskManager."""
    manager = TaskManager()
    
    print("=== MCPBench Task Manager ===\n")
    
    # Validate structure
    issues = manager.validate_task_structure()
    if issues:
        print("Structure Issues:")
        for issue in issues:
            print(f"  - {issue}")
        print()
    
    # Show summary
    summary = manager.get_task_summary()
    print("Task Summary:")
    total_tasks = 0
    for category, count in summary.items():
        print(f"  {category}: {count} tasks")
        total_tasks += count
    print(f"  Total: {total_tasks} tasks\n")
    
    # Show categories
    categories = manager.get_categories()
    print(f"Available Categories: {', '.join(categories)}\n")
    
    # Example filtering
    print("Filter Examples:")
    print(f"  All tasks: {len(manager.filter_tasks('all'))} tasks")
    if categories:
        first_category = categories[0]
        filtered = manager.filter_tasks(first_category)
        print(f"  {first_category}: {len(filtered)} tasks")
        
        if filtered:
            first_task = filtered[0]
            single_task = manager.filter_tasks(first_task.name)
            print(f"  {first_task.name}: {len(single_task)} task")


if __name__ == "__main__":
    main()