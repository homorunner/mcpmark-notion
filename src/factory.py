#!/usr/bin/env python3
"""
MCP Service Factory for MCPBench
=================================

This module provides a simplified factory pattern for creating service-specific managers
with centralized configuration management.

Features:
- Generic factory with service components registration
- Centralized configuration with validation
- Support for env vars, config files, and defaults
- Backward compatibility maintained
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type

from src.base.login_helper import BaseLoginHelper
from src.base.state_manager import BaseStateManager
from src.base.task_manager import BaseTaskManager
from src.config.config_schema import ConfigRegistry
from src.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


@dataclass
class ServiceComponents:
    """Container for service-specific component classes and configuration."""
    task_manager_class: Type[BaseTaskManager]
    state_manager_class: Type[BaseStateManager]
    login_helper_class: Type[BaseLoginHelper]
    
    # Configuration adapter functions
    task_manager_adapter: Optional[Callable[[dict], dict]] = None
    state_manager_adapter: Optional[Callable[[dict], dict]] = None
    login_helper_adapter: Optional[Callable[[dict], dict]] = None


class GenericServiceFactory:
    """Generic factory that creates service components with centralized config."""
    
    def __init__(self, components: ServiceComponents, service_name: str):
        self.components = components
        self.service_name = service_name
        self.config = ConfigRegistry.get_config(service_name)
    
    def create_task_manager(self, **kwargs) -> BaseTaskManager:
        """Create task manager with configuration."""
        config_dict = self.config.get_all()
        
        if self.components.task_manager_adapter:
            adapted_config = self.components.task_manager_adapter(config_dict)
            kwargs = {**kwargs, **adapted_config}
        
        return self.components.task_manager_class(**kwargs)
    
    def create_state_manager(self, **kwargs) -> BaseStateManager:
        """Create state manager with configuration."""
        config_dict = self.config.get_all()
        
        if self.components.state_manager_adapter:
            adapted_config = self.components.state_manager_adapter(config_dict)
            kwargs = {**kwargs, **adapted_config}
        
        return self.components.state_manager_class(**kwargs)
    
    def create_login_helper(self, **kwargs) -> BaseLoginHelper:
        """Create login helper with configuration."""
        config_dict = self.config.get_all()
        
        if self.components.login_helper_adapter:
            adapted_config = self.components.login_helper_adapter(config_dict)
            kwargs = {**kwargs, **adapted_config}
        
        return self.components.login_helper_class(**kwargs)


class ServiceRegistry:
    """Central registry for all MCP services."""
    
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
                state_manager_adapter=lambda cfg: {
                    "source_notion_key": cfg["source_api_key"],
                    "eval_notion_key": cfg["eval_api_key"],
                    "headless": cfg["playwright_headless"],
                    "browser": cfg["playwright_browser"],
                    "eval_parent_page_title": cfg["eval_parent_page_title"],
                },
                login_helper_adapter=lambda cfg: {
                    "headless": cfg["playwright_headless"],
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
                state_manager_adapter=lambda cfg: {
                    "github_token": cfg["api_key"],
                    "base_repo_owner": cfg["base_repo_owner"],
                    "base_repo_name": cfg["base_repo_name"],
                    "fork_owner": cfg["fork_owner"],
                },
                login_helper_adapter=lambda cfg: {
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
                state_manager_adapter=lambda cfg: {
                    "test_root": cfg["test_root"],
                    "cleanup_on_exit": cfg["cleanup_on_exit"],
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
    def create_factory(cls, service_name: str) -> GenericServiceFactory:
        """Create a factory for the specified service."""
        components = cls.register_components(service_name)
        return GenericServiceFactory(components, service_name)


class MCPServiceFactory:
    """Main factory interface with centralized configuration."""
    
    @classmethod
    def create_service_config(cls, service_name: str):
        """Create service configuration (backward compatible)."""
        config = ConfigRegistry.get_config(service_name)
        
        # Create a backward-compatible ServiceConfig-like object
        class ServiceConfigCompat:
            def __init__(self, service_name: str, config_dict: dict):
                self.service_name = service_name
                self.config = config_dict
                self.api_key = config_dict.get("api_key")
        
        return ServiceConfigCompat(service_name, config.get_all())
    
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
    
    @classmethod
    def validate_config(cls, service_name: Optional[str] = None) -> Dict[str, bool]:
        """Validate configuration for one or all services."""
        if service_name:
            try:
                ConfigRegistry.get_config(service_name)
                return {service_name: True}
            except Exception as e:
                logger.error(f"Configuration validation failed for {service_name}: {e}")
                return {service_name: False}
        else:
            return ConfigRegistry.validate_all()
    
    @classmethod
    def export_config_template(cls, service_name: str, output_path: str) -> None:
        """Export a configuration template for a service."""
        ConfigRegistry.export_template(service_name, Path(output_path))
    
    @classmethod
    def get_config_info(cls, service_name: str) -> dict:
        """Get detailed configuration information for debugging."""
        config = ConfigRegistry.get_config(service_name)
        return config.get_debug_info()
    
    @classmethod
    def get_supported_services(cls) -> list:
        """Get list of supported services."""
        return ["notion", "github", "filesystem", "postgres"]