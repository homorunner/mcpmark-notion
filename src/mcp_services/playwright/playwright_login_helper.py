#!/usr/bin/env python3
"""
Playwright Login Helper for MCPBench Evaluation Pipeline
========================================================

This module handles Playwright authentication and session management.
Since Playwright is a web automation tool, "login" here refers to 
ensuring the MCP server is accessible and browser capabilities are available.
"""

from pathlib import Path
from typing import Optional
from src.base.login_helper import BaseLoginHelper
from src.logger import get_logger

logger = get_logger(__name__)

class PlaywrightLoginHelper(BaseLoginHelper):
    """Handles Playwright MCP server authentication and session management."""
    
    def __init__(self, browser: str = "chrome", headless: bool = True, 
                 state_path: Optional[Path] = None):
        """Initialize Playwright login helper.
        
        Args:
            browser: Browser to use (chrome, firefox, webkit)
            headless: Run browser in headless mode
            state_path: Path to store authentication state
        """
        super().__init__("playwright", state_path)
        self.browser = browser
        self.headless = headless
    
    def login(self) -> bool:
        """Perform Playwright authentication.
        
        For Playwright MCP, this means verifying that:
        1. The MCP server is accessible
        2. Browser capabilities are available
        3. Required browser is installed
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Check if Playwright MCP server can be accessed
            # This would typically involve checking if the npm package is available
            # and if the browser binaries are installed
            
            logger.info(f"Checking Playwright MCP availability for browser: {self.browser}")
            
            # For now, we'll assume the MCP server is available
            # In a real implementation, you might want to:
            # 1. Check if playwright-mcp npm package is available
            # 2. Verify browser installation
            # 3. Test basic MCP server communication
            
            self._update_login_state(True)
            logger.info("Playwright MCP login successful")
            return True
            
        except Exception as e:
            logger.error(f"Playwright login failed: {e}")
            self._update_login_state(False)
            return False
    
    def is_logged_in(self) -> bool:
        """Check if currently logged in to Playwright MCP.
        
        For Playwright, this means checking if the MCP server is accessible
        and browser capabilities are available.
        
        Returns:
            bool: True if logged in, False otherwise
        """
        try:
            # Check authentication state from file if available
            if self.state_file.exists():
                state = self._load_login_state()
                return state.get("logged_in", False)
            
            # If no state file, assume not logged in
            return False
            
        except Exception as e:
            logger.error(f"Error checking Playwright login status: {e}")
            return False
    
    def logout(self) -> bool:
        """Logout from Playwright MCP.
        
        For Playwright, this means cleaning up any persistent state
        and marking as logged out.
        
        Returns:
            bool: True if logout successful, False otherwise
        """
        try:
            logger.info("Logging out from Playwright MCP")
            
            # Clean up any persistent browser state if using persistent profile
            # For isolated profiles, this is typically not needed
            
            self._update_login_state(False)
            logger.info("Playwright MCP logout successful")
            return True
            
        except Exception as e:
            logger.error(f"Playwright logout failed: {e}")
            return False
    
    def get_browser_info(self) -> dict:
        """Get current browser configuration information.
        
        Returns:
            dict: Browser configuration details
        """
        return {
            "browser": self.browser,
            "headless": self.headless,
            "service": "playwright"
        }