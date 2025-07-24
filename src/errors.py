#!/usr/bin/env python3
"""
Unified Error Taxonomy and Handling for MCPBench
=================================================

This module provides a centralized error handling system with:
- Clear error categories and taxonomy
- Consistent error messages
- Retry strategies based on error types
- Error context propagation
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union


class ErrorCategory(Enum):
    """Categories of errors in the MCPBench system."""
    
    # Configuration errors
    CONFIG_MISSING = "config_missing"
    CONFIG_INVALID = "config_invalid"
    
    # Authentication errors
    AUTH_FAILED = "auth_failed"
    AUTH_EXPIRED = "auth_expired"
    
    # Network errors
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_CONNECTION = "network_connection"
    
    # MCP-specific errors
    MCP_SERVER_ERROR = "mcp_server_error"
    MCP_TOOL_ERROR = "mcp_tool_error"
    
    # Task errors
    TASK_NOT_FOUND = "task_not_found"
    TASK_VERIFICATION_FAILED = "task_verification_failed"
    
    # State management errors
    STATE_SETUP_FAILED = "state_setup_failed"
    STATE_CLEANUP_FAILED = "state_cleanup_failed"
    STATE_DUPLICATION_ERROR = "state_duplication_error"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    
    # General errors
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorInfo:
    """Detailed error information."""
    category: ErrorCategory
    message: str
    original_error: Optional[Exception] = None
    context: Dict[str, Any] = None
    retryable: bool = False
    retry_after: Optional[int] = None  # seconds
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


class MCPBenchError(Exception):
    """Base exception for all MCPBench errors."""
    
    def __init__(self, error_info: ErrorInfo):
        self.error_info = error_info
        super().__init__(error_info.message)
    
    @property
    def category(self) -> ErrorCategory:
        return self.error_info.category
    
    @property
    def retryable(self) -> bool:
        return self.error_info.retryable
    
    @property
    def context(self) -> Dict[str, Any]:
        return self.error_info.context


# Specific error types

class ConfigurationError(MCPBenchError):
    """Configuration-related errors."""
    pass


class AuthenticationError(MCPBenchError):
    """Authentication-related errors."""
    pass


class NetworkError(MCPBenchError):
    """Network-related errors."""
    pass


class MCPError(MCPBenchError):
    """MCP-specific errors."""
    pass


class TaskError(MCPBenchError):
    """Task-related errors."""
    pass


class StateError(MCPBenchError):
    """State management errors."""
    pass


class ResourceError(MCPBenchError):
    """Resource-related errors."""
    pass


class ErrorClassifier:
    """Classifies errors and provides standardized handling."""
    
    # Error patterns for classification
    PATTERNS = {
        ErrorCategory.CONFIG_MISSING: [
            "Missing required environment variable",
            "configuration.*not found",
            "Missing.*API.*key",
        ],
        ErrorCategory.CONFIG_INVALID: [
            "Invalid.*configuration",
            "Invalid value for",
            "configuration.*invalid",
        ],
        ErrorCategory.AUTH_FAILED: [
            "Authentication failed",
            "Invalid.*token",
            "invalid.*token",
            "Unauthorized",
            "401",
        ],
        ErrorCategory.AUTH_EXPIRED: [
            "Token.*expired",
            "token.*expired",
            "Session.*expired",
            "session.*expired",
            "Authentication.*expired",
            "expired.*login",
        ],
        ErrorCategory.NETWORK_TIMEOUT: [
            "timeout",
            "timed out",
            "ETIMEDOUT",
        ],
        ErrorCategory.NETWORK_CONNECTION: [
            "ECONNREFUSED",
            "Connection refused",
            "Network.*error",
            "Failed to connect",
        ],
        ErrorCategory.MCP_SERVER_ERROR: [
            "MCP.*server.*error",
            "Error invoking MCP",
            "MCP.*failed",
            "MCP Network Error",
        ],
        ErrorCategory.MCP_TOOL_ERROR: [
            "MCP.*tool.*error",
            "Tool.*not found",
            "Tool.*failed",
        ],
        ErrorCategory.STATE_DUPLICATION_ERROR: [
            "State.*duplication.*error",
            "State duplication error",
            "Failed to duplicate",
            "Page.*already exists",
            "already exists",
        ],
    }
    
    # Retry strategies by category
    RETRY_STRATEGIES = {
        ErrorCategory.NETWORK_TIMEOUT: {"retryable": True, "max_retries": 3, "backoff": 5},
        ErrorCategory.NETWORK_CONNECTION: {"retryable": True, "max_retries": 3, "backoff": 10},
        ErrorCategory.MCP_SERVER_ERROR: {"retryable": True, "max_retries": 2, "backoff": 5},
        ErrorCategory.AUTH_EXPIRED: {"retryable": True, "max_retries": 1, "backoff": 0},
        ErrorCategory.STATE_DUPLICATION_ERROR: {"retryable": True, "max_retries": 2, "backoff": 2},
    }
    
    @classmethod
    def classify(cls, error: Exception) -> ErrorInfo:
        """Classify an exception into an ErrorInfo object."""
        error_str = str(error).lower()
        
        # Check patterns
        for category, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in error_str:
                    retry_strategy = cls.RETRY_STRATEGIES.get(category, {})
                    return ErrorInfo(
                        category=category,
                        message=cls._standardize_message(category, str(error)),
                        original_error=error,
                        retryable=retry_strategy.get("retryable", False),
                        retry_after=retry_strategy.get("backoff"),
                        context={"original_message": str(error)}
                    )
        
        # Default to unknown error
        return ErrorInfo(
            category=ErrorCategory.UNKNOWN_ERROR,
            message=str(error),
            original_error=error,
            retryable=False,
            context={"original_message": str(error)}
        )
    
    @classmethod
    def _standardize_message(cls, category: ErrorCategory, original: str) -> str:
        """Standardize error messages by category."""
        standardized = {
            ErrorCategory.CONFIG_MISSING: "Required configuration is missing",
            ErrorCategory.CONFIG_INVALID: "Configuration validation failed",
            ErrorCategory.AUTH_FAILED: "Authentication failed",
            ErrorCategory.AUTH_EXPIRED: "Authentication expired",
            ErrorCategory.NETWORK_TIMEOUT: "Network operation timed out",
            ErrorCategory.NETWORK_CONNECTION: "Network connection failed",
            ErrorCategory.MCP_SERVER_ERROR: "MCP server error",
            ErrorCategory.MCP_TOOL_ERROR: "MCP tool error",
            ErrorCategory.STATE_DUPLICATION_ERROR: "State duplication error",
        }
        
        base_msg = standardized.get(category, "Unknown error")
        
        # Add service context if available
        for service in ["notion", "github", "filesystem", "postgres"]:
            if service in original.lower():
                return f"{service.title()} {base_msg}"
        
        return base_msg
    
    @classmethod
    def create_error(cls, category: ErrorCategory, message: str, **kwargs) -> MCPBenchError:
        """Create a specific error type based on category."""
        error_info = ErrorInfo(
            category=category,
            message=message,
            retryable=cls.RETRY_STRATEGIES.get(category, {}).get("retryable", False),
            **kwargs
        )
        
        # Map categories to error classes
        error_class_map = {
            ErrorCategory.CONFIG_MISSING: ConfigurationError,
            ErrorCategory.CONFIG_INVALID: ConfigurationError,
            ErrorCategory.AUTH_FAILED: AuthenticationError,
            ErrorCategory.AUTH_EXPIRED: AuthenticationError,
            ErrorCategory.NETWORK_TIMEOUT: NetworkError,
            ErrorCategory.NETWORK_CONNECTION: NetworkError,
            ErrorCategory.MCP_SERVER_ERROR: MCPError,
            ErrorCategory.MCP_TOOL_ERROR: MCPError,
            ErrorCategory.TASK_NOT_FOUND: TaskError,
            ErrorCategory.TASK_VERIFICATION_FAILED: TaskError,
            ErrorCategory.STATE_SETUP_FAILED: StateError,
            ErrorCategory.STATE_CLEANUP_FAILED: StateError,
            ErrorCategory.STATE_DUPLICATION_ERROR: StateError,
            ErrorCategory.RESOURCE_NOT_FOUND: ResourceError,
            ErrorCategory.RESOURCE_LIMIT_EXCEEDED: ResourceError,
        }
        
        error_class = error_class_map.get(category, MCPBenchError)
        return error_class(error_info)


class ErrorHandler:
    """Handles errors with context and retry logic."""
    
    def __init__(self, service_name: Optional[str] = None):
        self.service_name = service_name
        self.error_history: List[ErrorInfo] = []
    
    def handle(self, error: Exception) -> ErrorInfo:
        """Handle an error and return error info."""
        # Classify the error
        error_info = ErrorClassifier.classify(error)
        
        # Add service context
        if self.service_name:
            error_info.context["service"] = self.service_name
        
        # Track error history
        self.error_history.append(error_info)
        
        return error_info
    
    def should_retry(self, error_info: ErrorInfo, attempt: int = 1) -> bool:
        """Determine if an error should be retried."""
        if not error_info.retryable:
            return False
        
        strategy = ErrorClassifier.RETRY_STRATEGIES.get(error_info.category, {})
        max_retries = strategy.get("max_retries", 0)
        
        return attempt <= max_retries
    
    def get_retry_delay(self, error_info: ErrorInfo, attempt: int = 1) -> int:
        """Get the retry delay for an error."""
        if not error_info.retryable:
            return 0
        
        strategy = ErrorClassifier.RETRY_STRATEGIES.get(error_info.category, {})
        base_backoff = strategy.get("backoff", 5)
        
        # Exponential backoff
        return base_backoff * attempt
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of errors encountered."""
        summary = {
            "total_errors": len(self.error_history),
            "by_category": {},
            "retryable_errors": 0,
        }
        
        for error_info in self.error_history:
            category_name = error_info.category.value
            summary["by_category"][category_name] = summary["by_category"].get(category_name, 0) + 1
            if error_info.retryable:
                summary["retryable_errors"] += 1
        
        return summary


# Convenience functions

def standardize_error_message(error: Union[str, Exception], service: Optional[str] = None) -> str:
    """Standardize an error message (backward compatible)."""
    if isinstance(error, str):
        error = Exception(error)
    
    handler = ErrorHandler(service_name=service)
    error_info = handler.handle(error)
    return error_info.message


def is_retryable_error(error: Union[str, Exception]) -> bool:
    """Check if an error is retryable."""
    if isinstance(error, str):
        error = Exception(error)
    
    error_info = ErrorClassifier.classify(error)
    return error_info.retryable