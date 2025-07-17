from abc import ABC, abstractmethod
from .task_manager import BaseTask


class BaseStateManager(ABC):
    """
    Abstract base class for state management in MCP services.

    This class defines the interface for service-specific state managers, which are
    responsible for setting up, duplicating, and cleaning up resources required
    for task execution.
    """

    def __init__(self):
        pass

    @abstractmethod
    def initialize(self, **kwargs):
        """
        Initializes the state manager with service-specific parameters.
        """
        pass

    @abstractmethod
    def clean_up(self, **kwargs):
        """
        Deletes or cleans up a resource after a task is completed.
        """
        pass

    @abstractmethod
    def set_up(self, task: BaseTask) -> bool:
        """
        Prepares the environment or state for a specific task.

        This method handles any necessary setup before a task is executed,
        such as duplicating a template, creating a test database, or forking a repository.

        Args:
            task: The task for which to set up the state.

        Returns:
            True if the setup was successful, False otherwise.
        """
        pass
