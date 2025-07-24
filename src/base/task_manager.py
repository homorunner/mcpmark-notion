from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


@dataclass
class BaseTask:
    """
    Base class for representing a task in the evaluation pipeline.
    All service-specific task classes should inherit from this.
    """

    task_instruction_path: Path
    task_verification_path: Path
    service: str
    category: str
    task_id: int

    @property
    def name(self) -> str:
        """Returns the full name of the task (e.g., 'category/task_1')."""
        return f"{self.category}/task_{self.task_id}"

    def get_task_instruction(self) -> str:
        """Reads and returns the task instruction from its file."""
        if self.task_instruction_path.exists():
            return self.task_instruction_path.read_text(encoding="utf-8")
        return ""


@dataclass
class BaseTaskResult:
    """Base class for representing the result of a task."""

    success: bool = False
    execution_time: float = 0.0
    service: str = "notion"
    category: str = "online_resume"
    task_id: int = 1
    error_message: Optional[str] = None
    conversation: Optional[dict] = None

    @property
    def status(self) -> str:
        """Returns the status of the task as 'PASS' or 'FAIL'."""
        return "PASS" if self.success else "FAIL"


class BaseTaskManager(ABC):
    """
    Abstract base class for task management in MCP services.
    Defines the interface for discovering, filtering, and verifying tasks.
    
    Note: Task managers are no longer responsible for LLM execution or MCP server management.
    Those responsibilities have been moved to independent agent classes.
    """

    def __init__(self, tasks_root: Path = None, service: str = "notion"):
        self.tasks_root = Path(tasks_root) if tasks_root else None
        self.service = service

    @abstractmethod
    def discover_all_tasks(self) -> List[BaseTask]:
        """Discovers all available tasks for the service."""
        pass

    @abstractmethod
    def get_categories(self) -> List[str]:
        """Gets a list of all task categories."""
        pass

    @abstractmethod
    def filter_tasks(self, task_filter: str) -> List[BaseTask]:
        """Filters tasks based on a given criteria."""
        pass

    @abstractmethod
    def get_task_instruction(self, task: BaseTask) -> str:
        """Gets the formatted task instruction for agent execution."""
        pass

    @abstractmethod
    def execute_task(self, task: BaseTask, agent_result: dict) -> BaseTaskResult:
        """Verifies a task using the result from agent execution and returns the final result."""
        pass
