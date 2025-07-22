"""
GitHub MCP Service for MCPBench
===============================

This module provides GitHub-specific MCP server integration for MCPBench evaluation.
Uses GitHub's official remote MCP server for streamable HTTP communication.
"""

from .github_login_helper import GitHubLoginHelper
from .github_task_manager import GitHubTaskManager, GitHubTask
from .github_state_manager import GitHubStateManager

__all__ = ['GitHubLoginHelper', 'GitHubTaskManager', 'GitHubTask', 'GitHubStateManager']
