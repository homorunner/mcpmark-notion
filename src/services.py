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
        "config_schema": {
            "source_api_key": {
                "env_var": "SOURCE_NOTION_API_KEY",
                "required": True,
                "description": "Notion API key for source hub with templates"
            },
            "eval_api_key": {
                "env_var": "EVAL_NOTION_API_KEY",
                "required": True,
                "description": "Notion API key for evaluation hub"
            },
            "eval_parent_page_title": {
                "env_var": "EVAL_PARENT_PAGE_TITLE",
                "required": True,
                "description": "Title of the parent page in evaluation workspace"
            },
            "playwright_headless": {
                "env_var": "PLAYWRIGHT_HEADLESS",
                "default": True,
                "required": False,
                "description": "Run browser in headless mode",
                "transform": "bool"  # Will be handled by GenericConfigSchema
            },
            "playwright_browser": {
                "env_var": "PLAYWRIGHT_BROWSER",
                "default": "firefox",
                "required": False,
                "description": "Browser to use for Playwright",
                "validator": "in:chromium,firefox,webkit"  # Simple validator syntax
            }
        },
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
        "config_schema": {
            "api_key": {
                "env_var": "GITHUB_TOKEN",
                "required": True,
                "description": "GitHub personal access token"
            },
            "base_repo_owner": {
                "env_var": "GITHUB_BASE_REPO_OWNER",
                "default": "mcpbench",
                "required": False,
                "description": "Owner of the base repository"
            },
            "base_repo_name": {
                "env_var": "GITHUB_BASE_REPO_NAME",
                "default": "eval-dev-quality",
                "required": False,
                "description": "Name of the base repository"
            },
            "fork_owner": {
                "env_var": "GITHUB_FORK_OWNER",
                "default": "mcpbench-eval",
                "required": False,
                "description": "Owner for forked repositories"
            }
        },
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
        "config_schema": {
            "test_root": {
                "env_var": "FILESYSTEM_TEST_ROOT",
                "default": None,
                "required": False,
                "description": "Root directory for filesystem tests",
                "transform": "path"  # Convert to Path object
            },
            "cleanup_on_exit": {
                "env_var": "FILESYSTEM_CLEANUP",
                "default": True,
                "required": False,
                "description": "Clean up test directories after tasks",
                "transform": "bool"
            }
        },
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
    
    "playwright": {
        "config_schema": {
            "browser": {
                "env_var": "PLAYWRIGHT_BROWSER",
                "default": "chromium",
                "required": False,
                "description": "Browser to use (chromium, firefox, webkit)",
                "validator": "in:chromium,firefox,webkit"
            },
            "headless": {
                "env_var": "PLAYWRIGHT_HEADLESS",
                "default": True,
                "required": False,
                "description": "Run browser in headless mode",
                "transform": "bool"
            },
            "network_origins": {
                "env_var": "PLAYWRIGHT_NETWORK_ORIGINS",
                "default": "*",
                "required": False,
                "description": "Allowed network origins (comma-separated or *)"
            },
            "user_profile": {
                "env_var": "PLAYWRIGHT_USER_PROFILE",
                "default": "isolated",
                "required": False,
                "description": "User profile type (isolated or persistent)",
                "validator": "in:isolated,persistent"
            },
            "viewport_width": {
                "env_var": "PLAYWRIGHT_VIEWPORT_WIDTH",
                "default": 1280,
                "required": False,
                "description": "Browser viewport width",
                "transform": "int"
            },
            "viewport_height": {
                "env_var": "PLAYWRIGHT_VIEWPORT_HEIGHT",
                "default": 720,
                "required": False,
                "description": "Browser viewport height",
                "transform": "int"
            }
        },
        "components": {
            "task_manager": "src.mcp_services.playwright.playwright_task_manager.PlaywrightTaskManager",
            "state_manager": "src.mcp_services.playwright.playwright_state_manager.PlaywrightStateManager",
            "login_helper": "src.mcp_services.playwright.playwright_login_helper.PlaywrightLoginHelper",
        },
        "config_mapping": {
            "state_manager": {
                "browser": "browser",
                "headless": "headless",
                "network_origins": "network_origins",
                "user_profile": "user_profile",
                "viewport_width": "viewport_width",
                "viewport_height": "viewport_height",
            },
            "login_helper": {
                "browser": "browser",
                "headless": "headless",
            }
        },
        "mcp_server": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@playwright/mcp@latest", "--headless"],
            "timeout": 120,
            "cache_tools": True,
            "requires_config": {
                "args_append": [
                    "--browser", "{browser}"
                ]
            }
        },
        "eval_config": {
            "browser": "browser",
            "headless": "headless",
            "network_origins": "network_origins",
            "user_profile": "user_profile",
            "viewport_width": "viewport_width",
            "viewport_height": "viewport_height"
        }
    },
    
    "postgres": {
        "config_schema": {
            "host": {
                "env_var": "POSTGRES_HOST",
                "default": "localhost",
                "required": False,
                "description": "PostgreSQL server host"
            },
            "port": {
                "env_var": "POSTGRES_PORT",
                "default": 5432,
                "required": False,
                "description": "PostgreSQL server port",
                "transform": "int",
                "validator": "port"  # Validates port range 1-65535
            },
            "database": {
                "env_var": "POSTGRES_DATABASE",
                "required": True,
                "description": "PostgreSQL database name"
            },
            "username": {
                "env_var": "POSTGRES_USERNAME",
                "required": True,
                "description": "PostgreSQL username"
            },
            "password": {
                "env_var": "POSTGRES_PASSWORD",
                "required": True,
                "description": "PostgreSQL password"
            }
        },
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