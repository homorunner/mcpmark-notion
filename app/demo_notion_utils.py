"""
Simplified Notion utilities for demo
====================================

This module provides Notion utilities that accept API key as parameter
instead of reading from environment variables.
"""

import os
from notion_client import Client


def get_notion_client(api_key: str = None):
    """Get Notion client with provided API key.
    
    Args:
        api_key: Notion API key. If not provided, tries EVAL_NOTION_API_KEY env var.
    
    Returns:
        Authenticated Notion Client
    """
    if not api_key:
        api_key = os.getenv("EVAL_NOTION_API_KEY")
    
    if not api_key:
        raise ValueError("Notion API key must be provided or set in EVAL_NOTION_API_KEY")
    
    return Client(auth=api_key)


def _find_object(notion: Client, title: str, object_type: str):
    """Generic helper to find a Notion page or database by title.

    Args:
        notion: Authenticated Notion Client.
        title: Title (or partial title) to search for.
        object_type: Either "page" or "database".

    Returns:
        The ID string if found, otherwise None.
    """
    search_results = (
        notion.search(query=title, filter={"property": "object", "value": object_type}).get("results")
        or []
    )

    if not search_results:
        return None

    # Shortcut when there is only one match
    if len(search_results) == 1:
        return search_results[0]["id"]

    # Attempt to find a case-insensitive match on the title field
    for result in search_results:
        if object_type == "page":
            # Pages store their title inside the "properties.title.title" rich text list
            title_rich_texts = result.get("properties", {}).get("title", {}).get("title", [])
        else:  # database
            title_rich_texts = result.get("title", [])

        for text_obj in title_rich_texts:
            if title.lower() in text_obj.get("plain_text", "").lower():
                return result["id"]

    return None


def find_page(notion: Client, title: str):
    """Find a Notion page by title."""
    return _find_object(notion, title, "page")


def find_database(notion: Client, title: str):
    """Find a Notion database by title."""
    return _find_object(notion, title, "database")


def find_page_or_database_by_id(notion: Client, object_id: str):
    """Find a Notion page or database by ID and return (id, type)."""
    try:
        # Try to retrieve as a page
        notion.pages.retrieve(page_id=object_id)
        return object_id, "page"
    except:
        pass
    
    try:
        # Try to retrieve as a database
        notion.databases.retrieve(database_id=object_id)
        return object_id, "database"
    except:
        pass
    
    return None, None


def find_database_in_block(notion: Client, page_id: str, db_title: str):
    """Find a database within a page by searching its blocks."""
    blocks = notion.blocks.children.list(block_id=page_id).get("results", [])
    
    for block in blocks:
        if block.get("type") == "child_database":
            db_info = block.get("child_database", {})
            if db_title.lower() in db_info.get("title", "").lower():
                return block["id"]
    
    return None