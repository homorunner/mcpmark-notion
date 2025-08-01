"""
Simplified Model Configuration for Demo
=======================================

This module provides model configuration management supporting multiple providers
all using OpenAI-compatible APIs.
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ModelInfo:
    """Information about a model."""
    provider: str
    api_key_var: str
    base_url_var: str
    default_base_url: str
    actual_model_name: str


class DemoModelConfig:
    """Simplified model configuration for the demo."""
    
    # Model configuration mapping with default base URLs
    MODEL_CONFIGS = {
        # OpenAI models
        "gpt-4o": ModelInfo(
            provider="openai",
            api_key_var="OPENAI_API_KEY",
            base_url_var="OPENAI_BASE_URL",
            default_base_url="https://api.openai.com/v1",
            actual_model_name="gpt-4o"
        ),
        "gpt-4o-mini": ModelInfo(
            provider="openai",
            api_key_var="OPENAI_API_KEY",
            base_url_var="OPENAI_BASE_URL",
            default_base_url="https://api.openai.com/v1",
            actual_model_name="gpt-4o-mini"
        ),
        "gpt-3.5-turbo": ModelInfo(
            provider="openai",
            api_key_var="OPENAI_API_KEY",
            base_url_var="OPENAI_BASE_URL",
            default_base_url="https://api.openai.com/v1",
            actual_model_name="gpt-3.5-turbo"
        ),
        "o3": ModelInfo(
            provider="openai",
            api_key_var="OPENAI_API_KEY",
            base_url_var="OPENAI_BASE_URL",
            default_base_url="https://api.openai.com/v1",
            actual_model_name="o3"
        ),
        
        # DeepSeek models
        "deepseek-chat": ModelInfo(
            provider="deepseek",
            api_key_var="DEEPSEEK_API_KEY",
            base_url_var="DEEPSEEK_BASE_URL",
            default_base_url="https://api.deepseek.com/v1",
            actual_model_name="deepseek-chat"
        ),
        "deepseek-reasoner": ModelInfo(
            provider="deepseek",
            api_key_var="DEEPSEEK_API_KEY",
            base_url_var="DEEPSEEK_BASE_URL",
            default_base_url="https://api.deepseek.com/v1",
            actual_model_name="deepseek-reasoner"
        ),
        
        # Anthropic models (via OpenAI-compatible proxy)
        "claude-3.5-sonnet": ModelInfo(
            provider="anthropic",
            api_key_var="ANTHROPIC_API_KEY",
            base_url_var="ANTHROPIC_BASE_URL",
            default_base_url="https://api.anthropic.com/v1",
            actual_model_name="claude-3-5-sonnet-20241022"
        ),
        "claude-3-opus": ModelInfo(
            provider="anthropic",
            api_key_var="ANTHROPIC_API_KEY",
            base_url_var="ANTHROPIC_BASE_URL",
            default_base_url="https://api.anthropic.com/v1",
            actual_model_name="claude-3-opus-20240229"
        ),
        "claude-4-sonnet": ModelInfo(
            provider="anthropic",
            api_key_var="ANTHROPIC_API_KEY",
            base_url_var="ANTHROPIC_BASE_URL",
            default_base_url="https://api.anthropic.com/v1",
            actual_model_name="claude-sonnet-4-20250514"
        ),
        
        # Google models (via OpenAI-compatible proxy)
        "gemini-2.0-flash": ModelInfo(
            provider="google",
            api_key_var="GEMINI_API_KEY",
            base_url_var="GEMINI_BASE_URL",
            default_base_url="https://generativelanguage.googleapis.com/v1beta",
            actual_model_name="gemini-2.0-flash-exp"
        ),
        "gemini-1.5-pro": ModelInfo(
            provider="google",
            api_key_var="GEMINI_API_KEY",
            base_url_var="GEMINI_BASE_URL",
            default_base_url="https://generativelanguage.googleapis.com/v1beta",
            actual_model_name="gemini-1.5-pro"
        ),
        
        # Moonshot models
        "moonshot-v1": ModelInfo(
            provider="moonshot",
            api_key_var="MOONSHOT_API_KEY",
            base_url_var="MOONSHOT_BASE_URL",
            default_base_url="https://api.moonshot.cn/v1",
            actual_model_name="moonshot-v1-8k"
        ),
    }
    
    def __init__(self, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize model configuration.
        
        Args:
            model_name: Name of the model
            api_key: Optional API key (overrides environment variable)
            base_url: Optional base URL (overrides environment variable)
        """
        self.model_name = model_name
        
        if model_name not in self.MODEL_CONFIGS:
            raise ValueError(f"Unsupported model: {model_name}")
        
        self.model_info = self.MODEL_CONFIGS[model_name]
        
        # Get API key (priority: parameter > env var)
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv(self.model_info.api_key_var)
        
        # Get base URL (priority: parameter > env var > default)
        if base_url:
            self.base_url = base_url
        else:
            self.base_url = os.getenv(self.model_info.base_url_var, self.model_info.default_base_url)
        
        self.provider = self.model_info.provider
        self.actual_model_name = self.model_info.actual_model_name
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Get list of supported model names."""
        return list(cls.MODEL_CONFIGS.keys())
    
    @classmethod
    def get_models_by_provider(cls, provider: str) -> List[str]:
        """Get models for a specific provider."""
        return [
            model_name 
            for model_name, info in cls.MODEL_CONFIGS.items() 
            if info.provider == provider
        ]
    
    @classmethod
    def get_display_info(cls) -> Dict[str, Dict[str, str]]:
        """Get display information for all models."""
        return {
            model_name: {
                "provider": info.provider,
                "display_name": f"{info.provider.title()} - {model_name}",
                "api_key_var": info.api_key_var
            }
            for model_name, info in cls.MODEL_CONFIGS.items()
        }