#!/usr/bin/env python3
"""
Playwright State Manager for MCPBench Evaluation Pipeline
=========================================================

This module manages initial state setup and cleanup for Playwright tasks.
Handles browser session management and test isolation.
"""

from typing import Optional, Dict, Any
from src.base.state_manager import BaseStateManager, InitialStateInfo
from src.base.task_manager import BaseTask
from src.logger import get_logger

logger = get_logger(__name__)

class PlaywrightStateManager(BaseStateManager):
    """Manages initial state setup and cleanup for Playwright tasks."""
    
    def __init__(self, browser: str = "chrome", headless: bool = True, 
                 network_origins: str = "*", user_profile: str = "isolated",
                 viewport_width: int = 1280, viewport_height: int = 720):
        """Initialize Playwright state manager.
        
        Args:
            browser: Browser to use (chrome, firefox, webkit)
            headless: Run browser in headless mode
            network_origins: Allowed network origins
            user_profile: User profile type (isolated or persistent)
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
        """
        super().__init__("playwright")
        self.browser = browser
        self.headless = headless
        self.network_origins = network_origins
        self.user_profile = user_profile
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        
        # Track browser sessions and contexts
        self.active_sessions = {}
    
    def _create_initial_state(self, task: BaseTask) -> Optional[InitialStateInfo]:
        """Create initial state for a Playwright task.
        
        For Playwright tasks, this typically means setting up browser context
        and preparing any required initial state.
        """
        try:
            # Generate unique session ID for this task
            session_id = f"playwright_session_{task.category}_{task.task_id}"
            
            # Create browser context configuration
            context_config = {
                "browser": self.browser,
                "headless": self.headless,
                "viewport": {
                    "width": self.viewport_width,
                    "height": self.viewport_height
                },
                "user_profile": self.user_profile,
                "network_origins": self.network_origins
            }
            
            # Track the session
            self.active_sessions[session_id] = context_config
            self.track_resource("browser_session", session_id)
            
            # Create state info
            state_info = InitialStateInfo(
                state_id=session_id,
                state_url=f"browser://{self.browser}/{session_id}",
                metadata={
                    "browser": self.browser,
                    "headless": self.headless,
                    "viewport_width": self.viewport_width,
                    "viewport_height": self.viewport_height,
                    "user_profile": self.user_profile,
                    "network_origins": self.network_origins
                }
            )
            
            logger.info(f"Created Playwright session: {session_id}")
            return state_info
            
        except Exception as e:
            logger.error(f"Failed to create initial state for Playwright task: {e}")
            return None
    
    def _store_initial_state_info(self, task: BaseTask, state_info: InitialStateInfo) -> None:
        """Store initial state information in the task object."""
        if hasattr(task, 'browser_context'):
            task.browser_context = state_info.metadata
        
        # Store session ID for cleanup
        if hasattr(task, 'session_id'):
            task.session_id = state_info.state_id
    
    def _cleanup_task_initial_state(self, task: BaseTask) -> bool:
        """Clean up initial state for a specific task."""
        try:
            session_id = getattr(task, 'session_id', None)
            if session_id and session_id in self.active_sessions:
                # Clean up browser session
                del self.active_sessions[session_id]
                logger.info(f"Cleaned up Playwright session: {session_id}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup task state: {e}")
            return False
    
    def _cleanup_single_resource(self, resource: Dict[str, Any]) -> bool:
        """Clean up a single tracked resource."""
        try:
            resource_type = resource['type']
            resource_id = resource['id']
            
            if resource_type == "browser_session":
                if resource_id in self.active_sessions:
                    del self.active_sessions[resource_id]
                    logger.info(f"Cleaned up browser session: {resource_id}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup resource {resource}: {e}")
            return False
    
    def get_browser_config(self) -> Dict[str, Any]:
        """Get current browser configuration."""
        return {
            "browser": self.browser,
            "headless": self.headless,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "user_profile": self.user_profile,
            "network_origins": self.network_origins
        }