#!/usr/bin/env python3
"""
Service Definitions for MCPBench
================================

Single source of truth for all MCP service configurations.
Adding a new service only requires modifying this file.

Note: Environment variables are already loaded from .mcp_env when the app starts,
so we can reference them directly via the config system.
"""

# Service definitions
SERVICES = {
    "notion": {
        "components": {
            "task_manager": "src.mcp_services.notion.notion_task_manager.NotionTaskManager",
            "state_manager": "src.mcp_services.notion.notion_state_manager.NotionStateManager",
            "login_helper": "src.mcp_services.notion.notion_login_helper.NotionLoginHelper",
        },
        "config_mapping": {
            # Maps config schema keys to class constructor parameters
            "state_manager": {
                "source_notion_key": "source_api_key",
                "eval_notion_key": "eval_api_key",
                "headless": "playwright_headless",
                "browser": "playwright_browser",
                "eval_parent_page_title": "eval_parent_page_title",
            },
            "login_helper": {
                "headless": "playwright_headless",
                "browser": "playwright_browser",
            }
        },
        "mcp_server": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@notionhq/notion-mcp-server"],
            "timeout": 120,
            "cache_tools": True,
            # Special fields that need config values
            "requires_config": {
                "env": {
                    "OPENAPI_MCP_HEADERS": '{"Authorization": "Bearer {notion_key}", "Notion-Version": "2022-06-28"}'
                }
            }
        },
        "eval_config": {
            # For evaluation, use eval_api_key as notion_key
            "notion_key": "eval_api_key"
        }
    },
    
    "github": {
        "components": {
            "task_manager": "src.mcp_services.github.github_task_manager.GitHubTaskManager",
            "state_manager": "src.mcp_services.github.github_state_manager.GitHubStateManager", 
            "login_helper": "src.mcp_services.github.github_login_helper.GitHubLoginHelper",
        },
        "config_mapping": {
            "state_manager": {
                "github_token": "api_key",
                "base_repo_owner": "base_repo_owner",
                "base_repo_name": "base_repo_name",
                "fork_owner": "fork_owner",
            },
            "login_helper": {
                "token": "api_key",
            }
        },
        "mcp_server": {
            "type": "http",
            "url": "https://api.githubcopilot.com/mcp/",
            "timeout": 30,
            "cache_tools": True,
            "requires_config": {
                "headers": {
                    "Authorization": "Bearer {github_token}",
                    "User-Agent": "MCPBench/1.0"
                }
            }
        },
        "eval_config": {
            "github_token": "api_key"
        }
    },
    
    "filesystem": {
        "components": {
            "task_manager": "src.mcp_services.filesystem.filesystem_task_manager.FilesystemTaskManager",
            "state_manager": "src.mcp_services.filesystem.filesystem_state_manager.FilesystemStateManager",
            "login_helper": "src.mcp_services.filesystem.filesystem_login_helper.FilesystemLoginHelper",
        },
        "config_mapping": {
            "state_manager": {
                "test_root": "test_root",
                "cleanup_on_exit": "cleanup_on_exit",
            }
        },
        "mcp_server": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "timeout": 120,
            "cache_tools": True,
            # Filesystem needs test directory appended to args at runtime
            "requires_config": {
                "args_append": ["{test_directory}"]
            }
        },
        "eval_config": {
            # Special handling - get test_directory from state manager
            "test_directory": "__from_state_manager__"
        }
    },
    
    "postgres": {
        "components": {
            # Placeholder - not yet implemented
            "task_manager": None,
            "state_manager": None,
            "login_helper": None,
        },
        "config_mapping": {},
        "mcp_server": None,
        "eval_config": {}
    }
}


def get_service_definition(service_name: str) -> dict:
    """Get service definition by name."""
    if service_name not in SERVICES:
        raise ValueError(f"Unknown service: {service_name}")
    return SERVICES[service_name]


def get_supported_services() -> list:
    """Get list of implemented services."""
    return [name for name, config in SERVICES.items() 
            if config["components"]["task_manager"] is not None]