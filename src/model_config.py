#!/usr/bin/env python3
"""
Model Configuration for MCPBench
================================

This module provides configuration management for different LLM models,
automatically detecting the required API keys and base URLs based on the model name.
"""
import os
from typing import Dict, List

from src.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class ModelConfig:
    """
    Configuration container for a specific model.
    It loads the necessary API key and base URL from environment variables.
    """

    # Model configuration mapping
    MODEL_CONFIGS = {
        # OpenAI models
        "gpt-4o": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "gpt-4o",
        },
        "gpt-4": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "gpt-4",
        },
        "gpt-4-turbo": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "gpt-4-turbo",
        },
        "o3": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "o3",
        },
        "o3-mini": {
            "provider": "openai",
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "actual_model_name": "o3-mini",
        },
        # DeepSeek models
        "deepseek-chat": {
            "provider": "deepseek",
            "api_key_var": "DEEPSEEK_API_KEY",
            "base_url_var": "DEEPSEEK_BASE_URL",
            "actual_model_name": "deepseek-chat",
        },
        "deepseek-coder": {
            "provider": "deepseek",
            "api_key_var": "DEEPSEEK_API_KEY",
            "base_url_var": "DEEPSEEK_BASE_URL",
            "actual_model_name": "deepseek-coder",
        },
        # Anthropic models
        "claude-3-5-sonnet": {
            "provider": "anthropic",
            "api_key_var": "ANTHROPIC_API_KEY",
            "base_url_var": "ANTHROPIC_BASE_URL",
            "actual_model_name": "claude-3-5-sonnet-20241022",
        },
        "claude-3-opus": {
            "provider": "anthropic",
            "api_key_var": "ANTHROPIC_API_KEY",
            "base_url_var": "ANTHROPIC_BASE_URL",
            "actual_model_name": "claude-3-opus-20240229",
        },
        # Google models
        "gemini-pro": {
            "provider": "google",
            "api_key_var": "GEMINI_API_KEY",
            "base_url_var": "GEMINI_BASE_URL",
            "actual_model_name": "gemini-pro",
        },
        "gemini-1.5-pro": {
            "provider": "google",
            "api_key_var": "GEMINI_API_KEY",
            "base_url_var": "GEMINI_BASE_URL",
            "actual_model_name": "gemini-1.5-pro",
        },
    }

    def __init__(self, model_name: str):
        """
        Initializes the model configuration.
        
        Args:
            model_name: The name of the model (e.g., 'gpt-4o', 'deepseek-chat').
            
        Raises:
            ValueError: If the model is not supported or environment variables are missing.
        """
        self.model_name = model_name
        model_info = self._get_model_info(model_name)

        # Load API key and base URL from environment variables
        self.api_key = os.getenv(model_info["api_key_var"])
        if not self.api_key:
            raise ValueError(
                f"Missing required environment variable: {model_info['api_key_var']}"
            )

        self.base_url = os.getenv(model_info["base_url_var"])
        if not self.base_url:
            raise ValueError(
                f"Missing required environment variable: {model_info['base_url_var']}"
            )

        # Store provider and the actual model name for the API
        self.provider = model_info["provider"]
        self.actual_model_name = model_info.get("actual_model_name", model_name)

    def _get_model_info(self, model_name: str) -> Dict[str, str]:
        """
        Retrieves the configuration details for a given model name.
        """
        if model_name not in self.MODEL_CONFIGS:
            supported_models = ", ".join(self.get_supported_models())
            raise ValueError(
                f"Unsupported model '{model_name}'. Supported models: {supported_models}"
            )
        return self.MODEL_CONFIGS[model_name]

    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Returns a list of all supported model names."""
        return list(cls.MODEL_CONFIGS.keys())


def main():
    """Example usage of the ModelConfig class."""
    logger.info("Supported models: %s", ModelConfig.get_supported_models())

    try:
        # Example: Create a model config for DeepSeek
        model_config = ModelConfig("deepseek-chat")
        logger.info("✅ DeepSeek model config created successfully.")
        logger.info("Provider: %s", model_config.provider)
        logger.info("Actual model name: %s", model_config.actual_model_name)
        logger.info("API key loaded: %s", bool(model_config.api_key))
        logger.info("Base URL: %s", model_config.base_url)

    except ValueError as e:
        logger.error("⚠️  Configuration error: %s", e)


if __name__ == "__main__":
    main()
