#!/usr/bin/env python3
"""
Utility helpers for interacting with the Notion MCP server.

This module centralizes shared functionality for setting up the Notion agent
environment, including API key management, model provider creation, and MCP
server setup.
"""

import os
from dotenv import load_dotenv
from agents.mcp.server import MCPServerStdio
from openai import AsyncOpenAI
from agents import Model, ModelProvider, OpenAIChatCompletionsModel

__all__ = [
    "get_notion_key",
    "create_model_provider",
    "create_mcp_server",
]


def get_notion_key(notion_key: str = None) -> str:
    """Load environment variables and return the Notion API key.

    Parameters
    ----------
    notion_key : str, optional
        Notion API key. If not provided, will use NOTION_API_KEY environment variable.

    Raises
    ------
    ValueError
        If the notion_key parameter and NOTION_API_KEY environment variable are both missing.
    """
    # Load variables from a .env file if present
    load_dotenv()

    notion_key = notion_key or os.getenv("NOTION_API_KEY")
    if not notion_key:
        raise ValueError(
            "Please provide notion_key as parameter or set NOTION_API_KEY "
            "environment variable in your .env file."
        )
    return notion_key


def create_model_provider(base_url: str = None, api_key: str = None, model_name: str = None) -> ModelProvider:
    """Create and return a custom model provider.

    Parameters
    ----------
    base_url : str, optional
        Model provider base URL. If not provided, will use MCPBENCH_BASE_URL environment variable.
    api_key : str, optional
        API key for model provider. If not provided, will use MCPBENCH_API_KEY environment variable.
    model_name : str, optional
        Model name to use. If not provided, will use MCPBENCH_MODEL_NAME environment variable.

    Raises
    ------
    ValueError
        If required model-related parameters are missing from both arguments and environment variables.
    """
    load_dotenv(override=True)

    # Use provided parameters or fall back to environment variables
    base_url = base_url or os.getenv("MCPBENCH_BASE_URL") or ""
    api_key = api_key or os.getenv("MCPBENCH_API_KEY") or ""
    model_name = model_name or os.getenv("MCPBENCH_MODEL_NAME") or ""

    if not base_url or not api_key or not model_name:
        raise ValueError(
            "Please provide base_url, api_key, and model_name as parameters or set "
            "MCPBENCH_BASE_URL, MCPBENCH_API_KEY, and MCPBENCH_MODEL_NAME "
            "in your .env file or as environment variables."
        )

    client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    class CustomModelProvider(ModelProvider):
        def get_model(self, model_name_override: str | None) -> Model:
            return OpenAIChatCompletionsModel(
                model=model_name_override or model_name, openai_client=client
            )

    return CustomModelProvider()


async def create_mcp_server(notion_key: str) -> MCPServerStdio:
    """Create and return an MCP server connection for Notion."""
    return MCPServerStdio(
        params={
            "command": "npx",
            "args": ["-y", "@notionhq/notion-mcp-server"],
            "env": {
                "OPENAPI_MCP_HEADERS": (
                    '{"Authorization": "Bearer ' + notion_key + '", '
                    '"Notion-Version": "2022-06-28"}'
                )
            },
        },
        client_session_timeout_seconds=120,
        cache_tools_list=True,
    )