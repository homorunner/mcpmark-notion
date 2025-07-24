#!/usr/bin/env python3
"""
MCP Service Factory for MCPBench
=================================

This module provides a simplified factory pattern for creating service-specific managers
and configurations for different MCP services like Notion, GitHub, and PostgreSQL.

Uses a generic factory with service components registration to reduce code duplication.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type

from dotenv import load_dotenv

from src.base.login_helper import BaseLoginHelper
from src.base.state_manager import BaseStateManager
from src.base.task_manager import BaseTaskManager
from src.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


@dataclass
class ServiceComponents:
    """Container for service-specific component classes and configuration."""
    task_manager_class: Type[BaseTaskManager]
    state_manager_class: Type[BaseStateManager]
    login_helper_class: Type[BaseLoginHelper]
    
    # Configuration factory functions
    task_manager_config: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    state_manager_config: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    login_helper_config: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None


class ServiceConfig:
    """Enhanced configuration container that supports schema validation."""
    
    def __init__(
        self,
        service_name: str,
        env_vars: Dict[str, str],
        defaults: Optional[Dict[str, Any]] = None,
    ):
        self.service_name = service_name
        self.env_vars = env_vars
        self.defaults = defaults or {}
        
        # Load environment variables from .mcp_env file
        load_dotenv(dotenv_path=".mcp_env", override=False)
        
        # Load all configured environment variables
        self.config = {}
        for key, env_var in env_vars.items():
            value = os.getenv(env_var, self.defaults.get(key))
            if value is None and key not in self.defaults:
                raise ValueError(f"Missing required environment variable: {env_var} for {key}")
            self.config[key] = value
        
        # Add defaults that weren't in env_vars
        for key, value in self.defaults.items():
            if key not in self.config:
                self.config[key] = value
        
        # Special handling for primary API key
        self.api_key = self.config.get("api_key")
    
    def validate(self) -> bool:
        """Validate the configuration."""
        # Override in subclasses for specific validation
        return True


class GenericServiceFactory:
    """Generic factory that creates service components based on registered configurations."""
    
    def __init__(self, components: ServiceComponents, config: ServiceConfig):
        self.components = components
        self.config = config
    
    def create_task_manager(self, **kwargs) -> BaseTaskManager:
        """Create task manager with merged configuration."""
        if self.components.task_manager_config:
            kwargs = {**kwargs, **self.components.task_manager_config(self.config.config)}
        return self.components.task_manager_class(**kwargs)
    
    def create_state_manager(self, **kwargs) -> BaseStateManager:
        """Create state manager with merged configuration."""
        if self.components.state_manager_config:
            kwargs = {**kwargs, **self.components.state_manager_config(self.config.config)}
        return self.components.state_manager_class(**kwargs)
    
    def create_login_helper(self, **kwargs) -> BaseLoginHelper:
        """Create login helper with merged configuration."""
        if self.components.login_helper_config:
            kwargs = {**kwargs, **self.components.login_helper_config(self.config.config)}
        return self.components.login_helper_class(**kwargs)


class ServiceRegistry:
    """Central registry for all MCP services."""
    
    # Service configurations
    SERVICE_CONFIGS = {
        "notion": {
            "env_vars": {
                "source_api_key": "SOURCE_NOTION_API_KEY",
                "eval_api_key": "EVAL_NOTION_API_KEY",
                "eval_parent_page_title": "EVAL_PARENT_PAGE_TITLE",
                "playwright_browser": "PLAYWRIGHT_BROWSER",
                "playwright_headless": "PLAYWRIGHT_HEADLESS",
            },
            "defaults": {
                "playwright_browser": "chromium",
                "playwright_headless": "true",
            }
        },
        "github": {
            "env_vars": {
                "api_key": "GITHUB_TOKEN",
            },
            "defaults": {}
        },
        "filesystem": {
            "env_vars": {
                "test_root": "FILESYSTEM_TEST_ROOT",
            },
            "defaults": {}
        },
        "postgres": {
            "env_vars": {
                "api_key": "POSTGRES_PASSWORD",
                "host": "POSTGRES_HOST",
                "port": "POSTGRES_PORT",
                "database": "POSTGRES_DATABASE",
                "username": "POSTGRES_USERNAME",
            },
            "defaults": {
                "host": "localhost",
                "port": "5432",
            }
        },
    }
    
    # Service components (lazy-loaded)
    _components: Dict[str, ServiceComponents] = {}
    
    @classmethod
    def register_components(cls, service_name: str) -> ServiceComponents:
        """Lazy-load and register service components."""
        if service_name in cls._components:
            return cls._components[service_name]
        
        if service_name == "notion":
            from src.mcp_services.notion.notion_login_helper import NotionLoginHelper
            from src.mcp_services.notion.notion_state_manager import NotionStateManager
            from src.mcp_services.notion.notion_task_manager import NotionTaskManager
            
            components = ServiceComponents(
                task_manager_class=NotionTaskManager,
                state_manager_class=NotionStateManager,
                login_helper_class=NotionLoginHelper,
                state_manager_config=lambda cfg: {
                    "source_notion_key": cfg["source_api_key"],
                    "eval_notion_key": cfg["eval_api_key"],
                    "headless": cfg["playwright_headless"] == "true",
                    "browser": cfg["playwright_browser"],
                    "eval_parent_page_title": cfg["eval_parent_page_title"],
                },
                login_helper_config=lambda cfg: {
                    "headless": cfg["playwright_headless"] == "true",
                    "browser": cfg["playwright_browser"],
                }
            )
        
        elif service_name == "github":
            from src.mcp_services.github.github_login_helper import GitHubLoginHelper
            from src.mcp_services.github.github_state_manager import GitHubStateManager
            from src.mcp_services.github.github_task_manager import GitHubTaskManager
            
            components = ServiceComponents(
                task_manager_class=GitHubTaskManager,
                state_manager_class=GitHubStateManager,
                login_helper_class=GitHubLoginHelper,
                state_manager_config=lambda cfg: {
                    "github_token": cfg["api_key"],
                    "base_repo_owner": "mcpbench",
                    "base_repo_name": "eval-dev-quality",
                    "fork_owner": "mcpbench-eval",
                },
                login_helper_config=lambda cfg: {
                    "token": cfg["api_key"],
                }
            )
        
        elif service_name == "filesystem":
            from src.mcp_services.filesystem.filesystem_login_helper import FilesystemLoginHelper
            from src.mcp_services.filesystem.filesystem_state_manager import FilesystemStateManager
            from src.mcp_services.filesystem.filesystem_task_manager import FilesystemTaskManager
            
            components = ServiceComponents(
                task_manager_class=FilesystemTaskManager,
                state_manager_class=FilesystemStateManager,
                login_helper_class=FilesystemLoginHelper,
                state_manager_config=lambda cfg: {
                    "test_root": Path(cfg["test_root"]) if cfg.get("test_root") else None,
                }
            )
        
        elif service_name == "postgres":
            # Placeholder for PostgreSQL
            raise NotImplementedError(f"Service {service_name} not yet implemented")
        
        else:
            raise ValueError(f"Unknown service: {service_name}")
        
        cls._components[service_name] = components
        return components
    
    @classmethod
    def create_service_config(cls, service_name: str) -> ServiceConfig:
        """Create service configuration."""
        if service_name not in cls.SERVICE_CONFIGS:
            raise ValueError(f"Unknown service: {service_name}")
        
        config_def = cls.SERVICE_CONFIGS[service_name]
        return ServiceConfig(
            service_name=service_name,
            env_vars=config_def["env_vars"],
            defaults=config_def["defaults"]
        )
    
    @classmethod
    def create_factory(cls, service_name: str) -> GenericServiceFactory:
        """Create a factory for the specified service."""
        config = cls.create_service_config(service_name)
        components = cls.register_components(service_name)
        return GenericServiceFactory(components, config)


class MCPServiceFactory:
    """Main factory interface - simplified implementation."""
    
    @classmethod
    def create_service_config(cls, service_name: str) -> ServiceConfig:
        """Create service configuration."""
        return ServiceRegistry.create_service_config(service_name)
    
    @classmethod
    def create_task_manager(cls, service_name: str, **kwargs) -> BaseTaskManager:
        """Create task manager for the specified service."""
        factory = ServiceRegistry.create_factory(service_name)
        return factory.create_task_manager(**kwargs)
    
    @classmethod
    def create_state_manager(cls, service_name: str, **kwargs) -> BaseStateManager:
        """Create state manager for the specified service."""
        factory = ServiceRegistry.create_factory(service_name)
        return factory.create_state_manager(**kwargs)
    
    @classmethod
    def create_login_helper(cls, service_name: str, **kwargs) -> BaseLoginHelper:
        """Create login helper for the specified service."""
        factory = ServiceRegistry.create_factory(service_name)
        return factory.create_login_helper(**kwargs)