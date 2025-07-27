"""
Filesystem State Manager for MCPBench
=====================================

This module handles filesystem state management for consistent task evaluation.
It manages test directories, file creation/cleanup, and environment isolation.
"""

import os
import shutil
import tempfile
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

    def __init__(
        self,
        test_root: Optional[Path] = None,
        cleanup_on_exit: bool = True
    ):
        """
        Initialize filesystem state manager.

        Args:
            test_root: Root directory for test operations (from FILESYSTEM_TEST_ROOT env var)
            cleanup_on_exit: Whether to clean up test directories after tasks
        """
        super().__init__(service_name="filesystem")

        # Use provided test root or create in temp directory
        if test_root:
            self.test_root = Path(test_root)
        else:
            # Default to a subdirectory in the system temp directory
            self.test_root = Path(tempfile.gettempdir()) / "mcpbench_filesystem_tests"

        self.cleanup_on_exit = cleanup_on_exit
        self.current_task_dir: Optional[Path] = None
        self.created_resources: List[Path] = []

        logger.info(f"Initialized FilesystemStateManager with test root: {self.test_root}")

    def initialize(self, **kwargs) -> bool:
        """
        Initialize the filesystem environment.

        Creates the test root directory if it doesn't exist.

        Returns:
            bool: True if initialization successful
        """
        try:
            # Create test root directory if it doesn't exist
            self.test_root.mkdir(parents=True, exist_ok=True)
            logger.info(f"Test root directory ready: {self.test_root}")

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

        Creates an isolated directory for the task to operate in.

        Args:
            task: The task for which to set up the state

        Returns:
            bool: True if setup successful
        """
        try:
            # Create a unique directory for this task
            task_dir_name = f"{task.service}_{task.category}_{task.task_id}_{os.getpid()}"
            self.current_task_dir = self.test_root / task_dir_name

            # Clean up if directory already exists (from previous run)
            if self.current_task_dir.exists():
                shutil.rmtree(self.current_task_dir)

            # Create fresh task directory
            self.current_task_dir.mkdir(parents=True)
            self.created_resources.append(self.current_task_dir)

            logger.info(f"Created task directory: {self.current_task_dir}")

            # Store the test directory path in the task object for use by task manager
            if hasattr(task, '__dict__'):
                task.test_directory = str(self.current_task_dir)

            # Set environment variable for verification scripts and MCP server
            os.environ["FILESYSTEM_TEST_DIR"] = str(self.current_task_dir)

            # Create category-specific initial state
            self._setup_category_files(task.category)

            return True

        except Exception as e:
            logger.error(f"Failed to set up filesystem state for {task.name}: {e}")
            return False

    def clean_up(self, task: Optional[BaseTask] = None, **kwargs) -> bool:
        """
        Clean up filesystem resources created during task execution.

        Args:
            task: The task to clean up after (optional)
            **kwargs: Additional cleanup options

        Returns:
            bool: True if cleanup successful
        """
        if not self.cleanup_on_exit:
            logger.info("Cleanup disabled, keeping test directories")
            return True

        try:
            cleanup_success = True

            # Clean up current task directory if it exists
            if self.current_task_dir and self.current_task_dir.exists():
                try:
                    shutil.rmtree(self.current_task_dir)
                    logger.info(f"Cleaned up task directory: {self.current_task_dir}")
                except Exception as e:
                    logger.error(f"Failed to clean up task directory: {e}")
                    cleanup_success = False

            # Clean up any other tracked resources
            for resource in self.created_resources:
                if resource.exists():
                    try:
                        if resource.is_dir():
                            shutil.rmtree(resource)
                        else:
                            resource.unlink()
                        logger.info(f"Cleaned up resource: {resource}")
                    except Exception as e:
                        logger.error(f"Failed to clean up {resource}: {e}")
                        cleanup_success = False

            # Clear the resources list
            self.created_resources.clear()
            self.current_task_dir = None

            return cleanup_success

        except Exception as e:
            logger.error(f"Filesystem cleanup failed: {e}")
            return False

    def _setup_category_files(self, category: str) -> None:
        """Setup category-specific files and directories."""
        setup_configs = {
            "basic_operations": self._setup_basic_operations,
            "directory_operations": self._setup_directory_operations,
            "file_management": self._setup_file_management,
        }

        setup_func = setup_configs.get(category)
        if setup_func:
            setup_func()
        else:
            logger.debug(f"No specific setup for category: {category}")

    def _setup_basic_operations(self) -> None:
        """Setup files for basic operations category."""
        sample_file = self.current_task_dir / "sample.txt"
        sample_file.write_text("This is a sample file for testing.")
        logger.info(f"Created sample file: {sample_file}")

    def _setup_directory_operations(self) -> None:
        """Setup directories for directory operations category."""
        nested_dir = self.current_task_dir / "level1" / "level2"
        nested_dir.mkdir(parents=True)
        (nested_dir / "nested_file.txt").write_text("Nested content")
        logger.info("Created nested directory structure")

    def _setup_file_management(self) -> None:
        """Setup various files for file management category."""
        files_to_create = [
            # Files with "test" in content
            ("experiment.txt", "This is a test experiment file."),
            ("data/test_results.txt", "Test results from the latest run."),

            # Files with "sample" in content
            ("example.txt", "This is a sample document."),
            ("docs/sample_data.txt", "Sample data for analysis."),

            # Files with neither test nor sample
            ("readme.txt", "Project documentation goes here."),
            ("notes.txt", "Important notes about the project."),
        ]

        for file_path, content in files_to_create:
            full_path = self.current_task_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        logger.info("Created various txt files for organization task")

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

    def force_cleanup_all(self) -> bool:
        """
        Force cleanup of all test directories in the test root.

        Returns:
            bool: True if cleanup successful
        """
        if not self.test_root.exists():
            return True

        try:
            for item in self.test_root.iterdir():
                if item.is_dir() and item.name.startswith("filesystem_"):
                    shutil.rmtree(item)
                    logger.info(f"Force cleaned up: {item}")
            return True
        except Exception as e:
            logger.error(f"Force cleanup failed: {e}")
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

    def _store_initial_state_info(self, task: BaseTask, state_info: Dict[str, Any]) -> None:
        """Store initial state information in the task object.

        For filesystem, we store the test directory path.
        """
        if state_info and "task_directory" in state_info:
            if hasattr(task, '__dict__'):
                task.test_directory = state_info["task_directory"]

    def _cleanup_task_initial_state(self, task: BaseTask) -> bool:
        """Clean up initial state for a specific task.

        For filesystem, this means removing the task directory.
        """
        if hasattr(task, 'test_directory') and task.test_directory:
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
