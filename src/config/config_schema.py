#!/usr/bin/env python3
"""
Centralized Configuration Schema for MCPBench
=============================================

This module provides a unified configuration system with validation,
type safety, and support for multiple configuration sources.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

import yaml
from dotenv import load_dotenv

from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConfigValue:
    """Represents a configuration value with metadata."""
    key: str
    value: Any
    source: str  # 'env', 'file', 'default'
    required: bool = True
    description: str = ""
    validator: Optional[callable] = None
    
    def validate(self) -> bool:
        """Validate the configuration value."""
        if self.required and self.value is None:
            raise ValueError(f"Required configuration '{self.key}' is missing")
        
        if self.validator and self.value is not None:
            if not self.validator(self.value):
                raise ValueError(f"Invalid value for '{self.key}': {self.value}")
        
        return True


class ConfigSchema(ABC):
    """Abstract base class for service configuration schemas."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._values: Dict[str, ConfigValue] = {}
        self._load_dotenv()
        self._define_schema()
        self._load_values()
        self._validate()
    
    @abstractmethod
    def _define_schema(self) -> None:
        """Define the configuration schema for this service."""
        pass
    
    def _load_dotenv(self) -> None:
        """Load environment variables from .mcp_env file."""
        load_dotenv(dotenv_path=".mcp_env", override=False)
    
    def _add_config(
        self,
        key: str,
        env_var: Optional[str] = None,
        default: Any = None,
        required: bool = True,
        description: str = "",
        validator: Optional[callable] = None,
        transform: Optional[callable] = None
    ) -> None:
        """Add a configuration value to the schema."""
        # Try to get value from environment first
        value = None
        source = "default"
        
        if env_var:
            env_value = os.getenv(env_var)
            if env_value is not None:
                value = transform(env_value) if transform else env_value
                source = "env"
        
        # Use default if no environment value
        if value is None and default is not None:
            value = default
            source = "default"
        
        self._values[key] = ConfigValue(
            key=key,
            value=value,
            source=source,
            required=required,
            description=description,
            validator=validator
        )
    
    def _load_values(self) -> None:
        """Load configuration values from file if available."""
        config_file = Path(f"config/{self.service_name}.yaml")
        if config_file.exists():
            with open(config_file) as f:
                file_config = yaml.safe_load(f)
                
            for key, value in file_config.items():
                if key in self._values and self._values[key].value is None:
                    self._values[key].value = value
                    self._values[key].source = "file"
    
    def _validate(self) -> None:
        """Validate all configuration values."""
        for config_value in self._values.values():
            config_value.validate()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        if key in self._values:
            return self._values[key].value
        return default
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values as a dictionary."""
        return {k: v.value for k, v in self._values.items()}
    
    def get_debug_info(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed configuration information for debugging."""
        return {
            k: {
                "value": v.value,
                "source": v.source,
                "required": v.required,
                "description": v.description
            }
            for k, v in self._values.items()
        }


# Concrete Schema Implementations

class NotionConfigSchema(ConfigSchema):
    """Configuration schema for Notion service."""
    
    def _define_schema(self) -> None:
        self._add_config(
            key="source_api_key",
            env_var="SOURCE_NOTION_API_KEY",
            required=True,
            description="API key for source Notion workspace (contains templates)"
        )
        
        self._add_config(
            key="eval_api_key",
            env_var="EVAL_NOTION_API_KEY",
            required=True,
            description="API key for evaluation Notion workspace"
        )
        
        self._add_config(
            key="eval_parent_page_title",
            env_var="EVAL_PARENT_PAGE_TITLE",
            required=True,
            description="Title of the parent page in evaluation workspace"
        )
        
        self._add_config(
            key="playwright_browser",
            env_var="PLAYWRIGHT_BROWSER",
            default="chromium",
            required=False,
            description="Browser to use for Playwright automation",
            validator=lambda x: x in ["chromium", "firefox", "webkit"]
        )
        
        self._add_config(
            key="playwright_headless",
            env_var="PLAYWRIGHT_HEADLESS",
            default=True,
            required=False,
            description="Run browser in headless mode",
            transform=lambda x: x.lower() in ["true", "1", "yes"]
        )


class GitHubConfigSchema(ConfigSchema):
    """Configuration schema for GitHub service."""
    
    def _define_schema(self) -> None:
        self._add_config(
            key="api_key",
            env_var="GITHUB_TOKEN",
            required=True,
            description="GitHub personal access token"
        )
        
        self._add_config(
            key="base_repo_owner",
            env_var="GITHUB_BASE_REPO_OWNER",
            default="mcpbench",
            required=False,
            description="Owner of the base repository"
        )
        
        self._add_config(
            key="base_repo_name",
            env_var="GITHUB_BASE_REPO_NAME",
            default="eval-dev-quality",
            required=False,
            description="Name of the base repository"
        )
        
        self._add_config(
            key="fork_owner",
            env_var="GITHUB_FORK_OWNER",
            default="mcpbench-eval",
            required=False,
            description="Owner for forked repositories"
        )


class FilesystemConfigSchema(ConfigSchema):
    """Configuration schema for Filesystem service."""
    
    def _define_schema(self) -> None:
        self._add_config(
            key="test_root",
            env_var="FILESYSTEM_TEST_ROOT",
            default=None,
            required=False,
            description="Root directory for filesystem tests",
            transform=lambda x: Path(x) if x else None,
            validator=lambda x: x is None or x.parent.exists()
        )
        
        self._add_config(
            key="cleanup_on_exit",
            env_var="FILESYSTEM_CLEANUP",
            default=True,
            required=False,
            description="Clean up test directories after tasks",
            transform=lambda x: x.lower() in ["true", "1", "yes"]
        )


class PostgresConfigSchema(ConfigSchema):
    """Configuration schema for PostgreSQL service."""
    
    def _define_schema(self) -> None:
        self._add_config(
            key="host",
            env_var="POSTGRES_HOST",
            default="localhost",
            required=False,
            description="PostgreSQL server host"
        )
        
        self._add_config(
            key="port",
            env_var="POSTGRES_PORT",
            default=5432,
            required=False,
            description="PostgreSQL server port",
            transform=int,
            validator=lambda x: 1 <= x <= 65535
        )
        
        self._add_config(
            key="database",
            env_var="POSTGRES_DATABASE",
            required=True,
            description="PostgreSQL database name"
        )
        
        self._add_config(
            key="username",
            env_var="POSTGRES_USERNAME",
            required=True,
            description="PostgreSQL username"
        )
        
        self._add_config(
            key="password",
            env_var="POSTGRES_PASSWORD",
            required=True,
            description="PostgreSQL password"
        )


# Configuration Registry

class ConfigRegistry:
    """Central registry for all service configurations."""
    
    _schemas: Dict[str, Type[ConfigSchema]] = {
        "notion": NotionConfigSchema,
        "github": GitHubConfigSchema,
        "filesystem": FilesystemConfigSchema,
        "postgres": PostgresConfigSchema,
    }
    
    _instances: Dict[str, ConfigSchema] = {}
    
    @classmethod
    def get_config(cls, service_name: str) -> ConfigSchema:
        """Get or create configuration for a service."""
        if service_name not in cls._instances:
            if service_name not in cls._schemas:
                raise ValueError(f"Unknown service: {service_name}")
            
            cls._instances[service_name] = cls._schemas[service_name](service_name)
        
        return cls._instances[service_name]
    
    @classmethod
    def register_schema(cls, service_name: str, schema_class: Type[ConfigSchema]) -> None:
        """Register a new configuration schema."""
        cls._schemas[service_name] = schema_class
    
    @classmethod
    def validate_all(cls) -> Dict[str, bool]:
        """Validate all registered configurations."""
        results = {}
        for service_name in cls._schemas:
            try:
                cls.get_config(service_name)
                results[service_name] = True
            except Exception as e:
                logger.error(f"Configuration validation failed for {service_name}: {e}")
                results[service_name] = False
        return results
    
    @classmethod
    def export_template(cls, service_name: str, output_path: Path) -> None:
        """Export a configuration template for a service."""
        if service_name not in cls._schemas:
            raise ValueError(f"Unknown service: {service_name}")
        
        # Create a dummy instance to get schema
        schema = cls._schemas[service_name](service_name)
        
        template = {
            "service": service_name,
            "configuration": {}
        }
        
        for key, config_value in schema._values.items():
            template["configuration"][key] = {
                "value": config_value.value if config_value.source == "default" else None,
                "description": config_value.description,
                "required": config_value.required,
                "env_var": f"${{{key.upper()}}}"
            }
        
        with open(output_path, 'w') as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)


# Backward Compatibility

def get_service_config(service_name: str) -> Dict[str, Any]:
    """Get service configuration as a dictionary (backward compatible)."""
    return ConfigRegistry.get_config(service_name).get_all()