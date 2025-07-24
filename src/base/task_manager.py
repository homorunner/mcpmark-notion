import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.logger import get_logger
from src.results_reporter import TaskResult

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
    
    This class implements the Template Method pattern to provide common functionality
    while allowing service-specific customization through abstract methods.
    
    Note: Task managers are no longer responsible for LLM execution or MCP server management.
    Those responsibilities have been moved to independent agent classes.
    """

    def __init__(self, tasks_root: Path = None, service: str = "notion"):
        self.tasks_root = Path(tasks_root) if tasks_root else None
        self.service = service
        self._tasks_cache = None

    # =========================================================================
    # Template Method Implementation - Common task discovery logic
    # =========================================================================
    
    def discover_all_tasks(self) -> List[BaseTask]:
        """Template method for discovering all available tasks.
        
        This method implements the common task discovery pattern and delegates
        service-specific details to abstract methods.
        """
        if self._tasks_cache is not None:
            return self._tasks_cache
        
        tasks = []
        if not self.tasks_root.exists():
            logger.warning("Tasks root directory does not exist: %s", self.tasks_root)
            return tasks
        
        # Get service-specific directory
        service_dir = self.tasks_root / self._get_service_directory_name()
        if not service_dir.exists():
            logger.warning("%s tasks directory does not exist: %s", self.service.title(), service_dir)
            return tasks
        
        # Scan categories using service-specific logic
        for category_dir in service_dir.iterdir():
            if not self._is_valid_category_dir(category_dir):
                continue
                
            category_name = category_dir.name
            logger.info("Discovering tasks in category: %s", category_name)
            
            # Find tasks using service-specific logic
            task_files = self._find_task_files(category_dir)
            for task_files_info in task_files:
                task = self._create_task_from_files(category_name, task_files_info)
                if task:
                    tasks.append(task)
                    logger.debug("Found task: %s", task.name)
        
        # Sort and cache
        self._tasks_cache = sorted(tasks, key=lambda t: (t.category, t.task_id))
        logger.info("Discovered %d %s tasks across all categories", len(self._tasks_cache), self.service.title())
        return self._tasks_cache
    
    def get_categories(self) -> List[str]:
        """Get a list of all task categories (common implementation)."""
        tasks = self.discover_all_tasks()
        return sorted(list(set(task.category for task in tasks)))
    
    def filter_tasks(self, task_filter: str) -> List[BaseTask]:
        """Filter tasks based on category or specific task pattern (common implementation)."""
        all_tasks = self.discover_all_tasks()
        
        if not task_filter or task_filter.lower() == "all":
            return all_tasks
        
        # Check if it's a category filter
        categories = self.get_categories()
        if task_filter in categories:
            return [task for task in all_tasks if task.category == task_filter]
        
        # Check for specific task pattern (category/task_X)
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
        
        # Fallback: check for partial matches in task names or categories
        filtered_tasks = []
        for task in all_tasks:
            if (task_filter in task.category or 
                task_filter in task.name or 
                task_filter == str(task.task_id)):
                filtered_tasks.append(task)
        
        return filtered_tasks
    
    def execute_task(self, task: BaseTask, agent_result: Dict[str, Any]) -> TaskResult:
        """Template method for task execution and verification.
        
        This method implements the common verification pattern and delegates
        service-specific details to abstract methods.
        """
        start_time = time.time()
        logger.info(f"- Verifying {self.service.title()} task: {task.name}")
        
        try:
            # Check for any pre-execution conditions
            pre_check_result = self._pre_execution_check(task)
            if not pre_check_result["success"]:
                execution_time = time.time() - start_time
                return TaskResult(
                    task_name=task.name,
                    success=False,
                    execution_time=execution_time,
                    error_message=pre_check_result["error"],
                    category=task.category,
                    task_id=task.task_id
                )
            
            # If agent execution failed, return the failure
            if not agent_result.get("success", False):
                execution_time = time.time() - start_time
                error_message = agent_result.get("error", "Agent execution failed")
                
                # Standardize MCP network errors
                error_message = self._standardize_error_message(error_message)
                    
                return TaskResult(
                    task_name=task.name,
                    success=False,
                    execution_time=execution_time,
                    error_message=error_message,
                    category=task.category,
                    task_id=task.task_id
                )

            # Run verification using service-specific command
            logger.info(f"- Running verification for task: {task.name}")
            verify_command = self._get_verification_command(task)
            verify_result = subprocess.run(
                verify_command,
                capture_output=True,
                text=True,
                timeout=90
            )
            
            # Process results
            success = verify_result.returncode == 0
            error_message = verify_result.stderr if not success and verify_result.stderr else None
            execution_time = time.time() - start_time
            
            # Post-execution cleanup or tracking
            self._post_execution_hook(task, success)
            
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
    
    def get_task_instruction(self, task: BaseTask) -> str:
        """Template method for getting formatted task instruction.
        
        Combines base instruction with service-specific formatting.
        """
        base_instruction = task.get_task_instruction()
        return self._format_task_instruction(base_instruction)
    
    # =========================================================================
    # Abstract methods for service-specific behavior
    # =========================================================================
    
    @abstractmethod
    def _get_service_directory_name(self) -> str:
        """Return the service directory name (e.g., 'notion', 'github')."""
        pass
    
    @abstractmethod
    def _find_task_files(self, category_dir: Path) -> List[Dict[str, Any]]:
        """Find and return task file information in the category directory.
        
        Returns:
            List of dictionaries containing task file paths and metadata
        """
        pass
    
    @abstractmethod
    def _create_task_from_files(self, category_name: str, task_files_info: Dict[str, Any]) -> Optional[BaseTask]:
        """Create a task object from file information.
        
        Args:
            category_name: Name of the task category
            task_files_info: Dictionary containing task file paths and metadata
            
        Returns:
            Task object or None if creation failed
        """
        pass
    
    @abstractmethod
    def _get_verification_command(self, task: BaseTask) -> List[str]:
        """Get the command to run for task verification.
        
        Args:
            task: The task to verify
            
        Returns:
            Command list suitable for subprocess.run()
        """
        pass
    
    @abstractmethod
    def _format_task_instruction(self, base_instruction: str) -> str:
        """Format the task instruction with service-specific additions.
        
        Args:
            base_instruction: The base task instruction text
            
        Returns:
            Formatted instruction string
        """
        pass
    
    # =========================================================================
    # Hook methods with default implementations (can be overridden)
    # =========================================================================
    
    def _is_valid_category_dir(self, category_dir: Path) -> bool:
        """Check if a directory is a valid category directory.
        
        Default implementation excludes hidden directories and 'utils'.
        Can be overridden by subclasses for service-specific logic.
        """
        return (category_dir.is_dir() and 
                not category_dir.name.startswith(".") and 
                category_dir.name != "utils")
    
    def _pre_execution_check(self, task: BaseTask) -> Dict[str, Any]:
        """Perform any pre-execution checks for the task.
        
        Default implementation returns success. Can be overridden by subclasses.
        
        Returns:
            Dictionary with 'success' boolean and optional 'error' message
        """
        _ = task  # Unused parameter, but part of the interface
        return {"success": True}
    
    def _post_execution_hook(self, task: BaseTask, success: bool) -> None:
        """Perform any post-execution actions.
        
        Default implementation does nothing. Can be overridden by subclasses.
        """
        _ = task, success  # Unused parameters, but part of the interface
        pass
    
    def _standardize_error_message(self, error_message: str) -> str:
        """Standardize error messages for consistent reporting.
        
        Default implementation handles common MCP errors.
        Can be overridden by subclasses for service-specific error handling.
        """
        if "MCP" in error_message or "Error invoking MCP" in error_message:
            return f"{self.service.title()} MCP Network Error"
        return error_message
