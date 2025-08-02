"""
Playwright Task Manager for MCPBench
====================================

Simple task manager for Playwright MCP tasks.
Follows anti-over-engineering principles: keep it simple, do what's needed.
"""

import sys
from pathlib import Path
from typing import List

from src.base.task_manager import BaseTask, BaseTaskManager


class PlaywrightTaskManager(BaseTaskManager):
    """Simple task manager for Playwright MCP tasks."""

    def __init__(self, tasks_root: Path = None):
        """Initialize with tasks directory."""
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"
        
        super().__init__(tasks_root, service="playwright", task_class=BaseTask,
                         task_organization="directory")

    def _get_verification_command(self, task: BaseTask) -> List[str]:
        """Get verification command - just run the verify.py script."""
        return [sys.executable, str(task.task_verification_path)]

    def _format_task_instruction(self, base_instruction: str) -> str:
        """Add Playwright-specific note to instructions."""
        return base_instruction + "\n\nUse Playwright MCP tools to complete this web automation task."