#!/usr/bin/env python3
"""
Utility helpers for interacting with the Notion MCP server.

This module centralizes shared functionality previously defined in
`notion_agent.py`, which has now been removed.
"""

import os
from dotenv import load_dotenv
from agents.mcp.server import MCPServerStdio

__all__ = [
    "load_environment",
    "create_mcp_server",
]


def load_environment() -> str:
    """Load environment variables and return the Notion API key.

    Raises
    ------
    ValueError
        If the NOTION_API_KEY environment variable is missing.
    """
    # Load variables from a .env file if present
    load_dotenv()

    notion_key = os.getenv("NOTION_API_KEY")
    if not notion_key:
        raise ValueError(
            "NOTION_API_KEY environment variable is required. "
            "Please add it to your .env file or set it as an environment variable."
        )

    return notion_key


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
        client_session_timeout_seconds=30,
        cache_tools_list=True,
    ) 