"""
GitHub MCP Service for MCPBench
===============================

This module provides GitHub-specific MCP server integration for MCPBench evaluation.
Uses GitHub's official remote MCP server for streamable HTTP/SSE communication.

Updated to include template-based environment replication mechanism.
"""

from .github_login_helper import GitHubLoginHelper
from .github_task_manager import GitHubTaskManager, GitHubTask
from .github_state_manager import GitHubStateManager
from .github_template_manager import GitHubTemplateManager

__all__ = [
    'GitHubLoginHelper', 
    'GitHubTaskManager', 
    'GitHubTask', 
    'GitHubStateManager',
    'GitHubTemplateManager'
]
