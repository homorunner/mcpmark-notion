"""
Playwright Task Manager for MCPBench Evaluation Pipeline
========================================================

This module provides utilities for discovering, filtering, and managing
Playwright-based web automation evaluation tasks.

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
class PlaywrightTask(BaseTask):
    """Represents a single evaluation task for Playwright service."""
    # Playwright-specific fields
    target_url: Optional[str] = None
    expected_elements: Optional[List[str]] = None
    expected_interactions: Optional[List[str]] = None
    screenshot_path: Optional[str] = None
    expected_page_title: Optional[str] = None
    browser_context: Optional[Dict[str, Any]] = None


class PlaywrightTaskManager(BaseTaskManager):
    """Manages task discovery, filtering, and verification for Playwright-based MCPBench evaluation."""

    def __init__(self, tasks_root: Path = None):
        """Initialize Playwright task manager.

        Args:
            tasks_root: Path to the tasks directory
        """
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"

        # Call parent constructor
        super().__init__(tasks_root, service="playwright", task_class=PlaywrightTask,
                         task_organization="directory")  # Playwright uses directory-based tasks


    # =========================================================================
    # Service-specific implementations
    # =========================================================================

    def _get_verification_command(self, task: PlaywrightTask) -> List[str]:
        """Get the verification command for Playwright tasks."""
        return [sys.executable, str(task.task_verification_path)]

    def _format_task_instruction(self, base_instruction: str) -> str:
        """Format task instruction with Playwright-specific additions."""
        return base_instruction + "\n\nNote: Use Playwright tools to complete this task. You can navigate to web pages, interact with elements, take screenshots, and perform web automation tasks."

    def _post_execution_hook(self, task: PlaywrightTask, success: bool) -> None:
        """Handle any cleanup or logging after task execution."""
        if task.category == 'web_navigation' and success:
            logger.info(f"Successfully completed web navigation task: {task.task_id}")
        elif task.category == 'form_interaction' and success:
            logger.info(f"Successfully completed form interaction task: {task.task_id}")
        elif task.category == 'element_extraction' and success:
            logger.info(f"Successfully completed element extraction task: {task.task_id}")
