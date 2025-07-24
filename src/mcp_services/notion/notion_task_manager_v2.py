#!/usr/bin/env python3
"""
Simplified Notion Task Manager using Enhanced Base Class
========================================================
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NotionTask(BaseTask):
    """Notion-specific task with additional fields."""
    page_id: Optional[str] = None
    workspace_id: Optional[str] = None
    database_id: Optional[str] = None
    expected_properties: Optional[Dict[str, Any]] = None


class NotionTaskManager(BaseTaskManager):
    """Simplified Notion task manager."""
    
    def __init__(self, tasks_root: Path = None):
        """Initialize Notion task manager."""
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"
        
        super().__init__(tasks_root, service="notion")
    
    # Required abstract methods only
    
    def _get_service_directory_name(self) -> str:
        """Return the service directory name."""
        return "notion"
    
    def _get_task_organization(self) -> str:
        """Notion uses directory-based organization."""
        return "directory"
    
    def _create_task_instance(self, **kwargs) -> NotionTask:
        """Create a Notion-specific task instance."""
        return NotionTask(**kwargs)
    
    # Optional: Notion-specific formatting
    
    def _format_task_instruction(self, instruction_content: str) -> str:
        """Add Notion-specific instructions."""
        return instruction_content + "\n\nIMPORTANT: use Notion MCP Tools for this task."