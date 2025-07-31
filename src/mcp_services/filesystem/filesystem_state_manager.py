"""
Filesystem State Manager for MCPBench
=====================================

This module handles filesystem state management for consistent task evaluation.
It manages test directories, file creation/cleanup, and environment isolation.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.base.state_manager import BaseStateManager
from src.base.task_manager import BaseTask
from src.logger import get_logger

logger = get_logger(__name__)


class FilesystemStateManager(BaseStateManager):
    """
    Manages filesystem state for task evaluation.

    This includes creating isolated test directories, tracking created resources,
    and cleaning up after task completion.
    """

    def __init__(self, test_root: Optional[Path] = None, cleanup_on_exit: bool = False):
        """
        Initialize filesystem state manager.

        Args:
            test_root: Root directory for test operations (from FILESYSTEM_TEST_ROOT env var)
            cleanup_on_exit: Whether to clean up test directories after tasks (default False for persistent environment)
        """
        super().__init__(service_name="filesystem")

        # Use provided test root or default to persistent test environment
        if test_root:
            self.test_root = Path(test_root)
        else:
            # Default to persistent test environment in repository
            repo_root = Path(__file__).resolve().parents[3]
            self.test_root = repo_root / "test_environments" / "desktop"

        self.cleanup_on_exit = cleanup_on_exit
        self.current_task_dir: Optional[Path] = None
        self.created_resources: List[Path] = []

        logger.info(
            f"Initialized FilesystemStateManager with persistent test environment: {self.test_root}"
        )

    def initialize(self, **kwargs) -> bool:
        """
        Initialize the filesystem environment.

        Ensures the persistent test environment exists and is accessible.

        Returns:
            bool: True if initialization successful
        """
        try:
            # Ensure test environment directory exists
            if not self.test_root.exists():
                logger.error(f"Persistent test environment not found: {self.test_root}")
                logger.error(
                    "Please ensure test_environments/desktop/ exists in the repository"
                )
                return False

            logger.info(f"Using persistent test environment: {self.test_root}")

            # Verify we can write to the directory
            test_file = self.test_root / ".mcpbench_test"
            test_file.write_text("test")
            test_file.unlink()

            return True

        except Exception as e:
            logger.error(f"Failed to initialize filesystem environment: {e}")
            return False

    def set_up(self, task: BaseTask) -> bool:
        """
        Set up filesystem environment for a specific task.

        Uses the persistent test environment as the working directory.

        Args:
            task: The task for which to set up the state

        Returns:
            bool: True if setup successful
        """
        try:
            # Use the persistent test environment directly
            self.current_task_dir = self.test_root

            logger.info(f"Using persistent test environment: {self.current_task_dir}")

            # Store the test directory path in the task object for use by task manager
            if hasattr(task, "__dict__"):
                task.test_directory = str(self.current_task_dir)

            # Set environment variable for verification scripts and MCP server
            os.environ["FILESYSTEM_TEST_DIR"] = str(self.current_task_dir)

            # Reset environment to clean state if needed
            self._reset_environment_if_needed(task.category)

            return True

        except Exception as e:
            logger.error(f"Failed to set up filesystem state for {task.name}: {e}")
            return False

    def clean_up(self, task: Optional[BaseTask] = None, **kwargs) -> bool:
        """
        Clean up filesystem resources created during task execution.

        In persistent mode, minimal cleanup is performed to maintain the environment.

        Args:
            task: The task to clean up after (optional)
            **kwargs: Additional cleanup options

        Returns:
            bool: True if cleanup successful
        """
        if not self.cleanup_on_exit:
            logger.info("Cleanup disabled, maintaining persistent test environment")
            return True

        try:
            cleanup_success = True

            # In persistent mode, only clean up specific temporary files/directories
            # that shouldn't persist between tasks
            temp_files = ["hello_world.txt", "new_file.txt", "temp.txt"]
            for file_name in temp_files:
                file_path = self.test_root / file_name
                if file_path.exists():
                    try:
                        file_path.unlink()
                        logger.info(f"Cleaned up temporary file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to clean up {file_path}: {e}")
                        cleanup_success = False

            # Clear the resources list but keep the current_task_dir reference
            self.created_resources.clear()

            return cleanup_success

        except Exception as e:
            logger.error(f"Filesystem cleanup failed: {e}")
            return False

    def _reset_environment_if_needed(self, category: str) -> None:
        """Reset environment to clean state if needed for specific categories."""
        # For most categories, we use the persistent environment as-is
        # Only reset if specific cleanup is needed
        reset_configs = {
            "file_management": self._reset_file_management,
        }

        reset_func = reset_configs.get(category)
        if reset_func:
            reset_func()
        else:
            logger.debug(f"No specific reset needed for category: {category}")

    def _reset_file_management(self) -> None:
        """Reset file management test environment by removing sorting directories."""
        # Remove sorting directories if they exist from previous runs
        sorting_dirs = ["has_test", "no_test", "organized"]
        for dir_name in sorting_dirs:
            dir_path = self.current_task_dir / dir_name
            if dir_path.exists():
                shutil.rmtree(dir_path)
                logger.info(f"Removed previous sorting directory: {dir_path}")

        # Ensure all test files are back in their original locations
        self._restore_original_file_locations()

    def _restore_original_file_locations(self) -> None:
        """Restore files to their original locations if they were moved."""
        # This is a more complex operation that would need to track file movements
        # For now, we'll rely on the persistent environment being reset manually if needed
        # In a production system, we might maintain a manifest of original file locations
        logger.debug(
            "File restoration not implemented - assuming persistent environment is maintained"
        )

    def get_test_directory(self) -> Optional[Path]:
        """
        Get the current test directory path.

        Returns:
            Path to the current test directory, or None if not set up
        """
        return self.current_task_dir

    def get_service_config_for_agent(self) -> dict:
        """
        Get service-specific configuration for agent execution.

        Returns:
            Dictionary containing configuration needed by the agent/MCP server
        """
        service_config = {}

        # Add test directory if available
        if self.current_task_dir:
            service_config["test_directory"] = str(self.current_task_dir)

        return service_config

    def track_resource(self, resource_path: Path):
        """
        Track a resource for cleanup.

        Args:
            resource_path: Path to the resource to track
        """
        if resource_path not in self.created_resources:
            self.created_resources.append(resource_path)
            logger.debug(f"Tracking resource for cleanup: {resource_path}")

    def reset_test_environment(self) -> bool:
        """
        Reset the test environment to its original state.

        This method can be used for development/debugging purposes.
        In normal operation, the persistent environment is maintained.

        Returns:
            bool: True if reset successful
        """
        try:
            # Remove any sorting directories that might have been created
            sorting_dirs = ["has_test", "no_test", "organized", "backup"]
            for dir_name in sorting_dirs:
                dir_path = self.test_root / dir_name
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    logger.info(f"Removed sorting directory: {dir_path}")

            # Remove any temporary files that might have been created
            temp_files = ["hello_world.txt", "new_file.txt", "temp.txt"]
            for file_name in temp_files:
                file_path = self.test_root / file_name
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Removed temporary file: {file_path}")

            logger.info("Test environment reset completed")
            return True
        except Exception as e:
            logger.error(f"Test environment reset failed: {e}")
            return False

    # =========================================================================
    # Abstract Method Implementations Required by BaseStateManager
    # =========================================================================

    def _create_initial_state(self, task: BaseTask) -> Optional[Dict[str, Any]]:
        """Create initial state for a task.

        For filesystem, this is handled in set_up() method by creating task directories.
        Returns the task directory path as state info.
        """
        if self.current_task_dir and self.current_task_dir.exists():
            return {"task_directory": str(self.current_task_dir)}
        return None

    def _store_initial_state_info(
        self, task: BaseTask, state_info: Dict[str, Any]
    ) -> None:
        """Store initial state information in the task object.

        For filesystem, we store the test directory path.
        """
        if state_info and "task_directory" in state_info:
            if hasattr(task, "__dict__"):
                task.test_directory = state_info["task_directory"]

    def _cleanup_task_initial_state(self, task: BaseTask) -> bool:
        """Clean up initial state for a specific task.

        For filesystem, this means removing the task directory.
        """
        if hasattr(task, "test_directory") and task.test_directory:
            task_dir = Path(task.test_directory)
            if task_dir.exists():
                try:
                    shutil.rmtree(task_dir)
                    logger.info(f"Cleaned up task directory: {task_dir}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to clean up task directory: {e}")
                    return False
        return True

    def _cleanup_single_resource(self, resource: Dict[str, Any]) -> bool:
        """Clean up a single tracked resource.

        For filesystem, resources are paths to files/directories.
        """
        if "path" in resource:
            resource_path = Path(resource["path"])
            if resource_path.exists():
                try:
                    if resource_path.is_dir():
                        shutil.rmtree(resource_path)
                    else:
                        resource_path.unlink()
                    logger.info(f"Cleaned up resource: {resource_path}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to clean up {resource_path}: {e}")
                    return False
        return True
