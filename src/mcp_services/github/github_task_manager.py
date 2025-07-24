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

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger
from src.results_reporter import TaskResult

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
        
        self._tasks_cache = None
    
    
    # =========================================================================
    # Task Discovery and Management
    # =========================================================================
    
    def discover_all_tasks(self) -> List[GitHubTask]:
        """Discover all available GitHub tasks in the tasks directory."""
        if self._tasks_cache is not None:
            return self._tasks_cache
        
        tasks = []
        if not self.tasks_root.exists():
            logger.warning("Tasks root directory does not exist: %s", self.tasks_root)
            return tasks
        
        # Look for github service directory
        github_tasks_dir = self.tasks_root / "github"
        if not github_tasks_dir.exists():
            logger.warning("GitHub tasks directory does not exist: %s", github_tasks_dir)
            return tasks
        
        # Scan categories
        for category_dir in github_tasks_dir.iterdir():
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
                
                task = GitHubTask(
                    task_instruction_path=task_file,
                    task_verification_path=verify_file,
                    service="github",
                    category=category_name,
                    task_id=task_id
                )
                tasks.append(task)
                logger.debug("Found task: %s", task.name)
        
        self._tasks_cache = sorted(tasks, key=lambda t: (t.category, t.task_id))
        logger.info("Discovered %d GitHub tasks across all categories", len(self._tasks_cache))
        return self._tasks_cache
    
    def _extract_task_id(self, filename: str) -> Optional[int]:
        """Extract task ID from filename like 'task_1.md'."""
        import re
        match = re.match(r'task_(\d+)\.md', filename)
        return int(match.group(1)) if match else None
    
    def get_categories(self) -> List[str]:
        """Get a list of all task categories."""
        tasks = self.discover_all_tasks()
        return sorted(list(set(task.category for task in tasks)))
    
    def filter_tasks(self, task_filter: str) -> List[GitHubTask]:
        """Filter tasks based on category or task name pattern."""
        all_tasks = self.discover_all_tasks()
        
        if not task_filter:
            return all_tasks
        
        filtered_tasks = []
        for task in all_tasks:
            if (task_filter in task.category or 
                task_filter in task.name or 
                task_filter == str(task.task_id)):
                filtered_tasks.append(task)
        
        return filtered_tasks
    
    
    def execute_task(self, task: GitHubTask, agent_result: Dict[str, Any]) -> TaskResult:
        """Execute task verification using the result from agent execution.

        Args:
            task: Task object containing task details
            agent_result: Result from agent execution containing success, output, token_usage, etc.

        Returns:
            TaskResult object with execution results
        """
        start_time = time.time()
        logger.info(f"- Verifying GitHub task: {task.name}")
        
        try:
            # If agent execution failed, return the failure
            if not agent_result.get("success", False):
                execution_time = time.time() - start_time
                error_message = agent_result.get("error", "Agent execution failed")
                
                # Check for MCP network errors
                if "MCP" in error_message or "GitHub MCP" in error_message:
                    error_message = "GitHub MCP Network Error"
                    
                return TaskResult(
                    task_name=task.name,
                    success=False,
                    execution_time=execution_time,
                    error_message=error_message,
                    category=task.category,
                    task_id=task.task_id
                )

            # Run verification
            logger.info(f"- Running verification for task: {task.name}")
            verify_result = subprocess.run(
                [sys.executable, str(task.task_verification_path)],
                capture_output=True,
                text=True,
                timeout=90
            )
            
            # Process results
            success = verify_result.returncode == 0
            error_message = verify_result.stderr if not success and verify_result.stderr else None
            execution_time = time.time() - start_time
            
            # Track created repositories for cleanup if needed
            if task.category == 'basic_repo_operations' and success:
                self._track_created_repositories_from_verification(task)
            
            if success:
                logger.info(f"✓ Verification passed for task: {task.name}")
            else:
                logger.error(f"✗ Verification failed for task: {task.name}")
                logger.error(f"⚠️ Error: {error_message}")
            
            return TaskResult(
                task_name=task.name,
                success=success,
                execution_time=execution_time,
                error_message=error_message,
                model_output=agent_result.get("output", ""),
                category=task.category,
                task_id=task.task_id,
                token_usage=agent_result.get("token_usage", {}),
                turn_count=agent_result.get("turn_count", -1),
            )
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Task verification failed: {e}", exc_info=True)
            return TaskResult(
                task_name=task.name,
                success=False,
                execution_time=execution_time,
                error_message=str(e),
                category=task.category,
                task_id=task.task_id
            )
    
    def get_task_instruction(self, task: GitHubTask) -> str:
        """Get the formatted task instruction for agent execution.
        
        Args:
            task: The task to get instruction for
            
        Returns:
            Formatted task instruction string
        """
        base_instruction = task.get_task_instruction()
        return base_instruction + "\n\nNote: Use GitHub tools to complete this task. Work systematically and verify your actions." 

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