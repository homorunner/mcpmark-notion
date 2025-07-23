#!/usr/bin/env python3
"""explore_notion.py
A small CLI helper to quickly inspect the structure and contents of a Notion page or database
by providing its title.

Usage examples:
    python -m examples.explore_notion --title "My Project" --type page
    python -m examples.explore_notion --title "Tasks" --type database --show-rows --max-rows 10

The script relies on an environment variable NOTION_API_KEY set in a .env file at the project
root (handled by tasks.utils.notion_utils.get_notion_client).
"""

import argparse
import sys
from typing import Optional

from notion_client import Client

# Local utilities
try:
    from tasks.utils import notion_utils as nutils
except ModuleNotFoundError:
    # Fallback: allow running when executed from within the tasks directory
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "tasks")))
    from utils import notion_utils as nutils  # type: ignore


def _print_rich_text(rich_text_list):
    return "".join([rt.get("plain_text", "") for rt in rich_text_list])

# Helper to truncate/preview a string to a given length
def _preview(text: str, length: int) -> str:
    if length <= 0:
        return ""
    return text[:length]

# Convert a property object to a plain string for preview purposes
def _property_to_str(prop: dict) -> str:
    prop_type = prop.get("type")
    if prop_type == "title":
        return _print_rich_text(prop.get("title", []))
    if prop_type == "rich_text":
        return _print_rich_text(prop.get("rich_text", []))
    if prop_type == "number":
        return str(prop.get("number"))
    if prop_type in {"select", "status"}:
        option = prop.get(prop_type)
        return option.get("name") if option else ""
    if prop_type == "multi_select":
        return ", ".join(o.get("name", "") for o in prop.get("multi_select", []))
    if prop_type == "checkbox":
        return str(prop.get("checkbox"))
    if prop_type == "date":
        date_obj = prop.get("date")
        if date_obj:
            return date_obj.get("start", "")
        return ""
    if prop_type in {"url", "email", "phone_number"}:
        return prop.get(prop_type, "")
    if prop_type in {"relation", "people"}:
        # Show count of related items / people
        return f"{len(prop.get(prop_type, []))} item(s)"
    # Fallback to empty string
    return ""


def _print_block(block: dict, indent: int = 0, preview_len: int = 10):
    prefix = "  " * indent
    block_type = block.get("type", "unknown")
    text = _preview(nutils.get_block_plain_text(block), preview_len)
    print(f"{prefix}- [{block_type}] {text}")


def _print_block_recursive(notion: Client, block_id: str, indent: int = 0, preview_len: int = 10):
    try:
        children = notion.blocks.children.list(block_id=block_id).get("results", [])
    except Exception as exc:
        print(f"  {'  '*indent}(Failed to fetch children: {exc})")
        return

    for child in children:
        _print_block(child, indent, preview_len)
        if child.get("has_children"):
            _print_block_recursive(notion, child["id"], indent + 1, preview_len)


def explore_page(notion: Client, page_id: str, preview_len: int):
    """Print a human-readable tree of blocks under the given page."""
    try:
        page = notion.pages.retrieve(page_id)
    except Exception as exc:
        print(f"Error retrieving page {page_id}: {exc}")
        return

    title_prop = page.get("properties", {}).get("title")
    if title_prop:
        title = _print_rich_text(title_prop.get("title", []))
    else:
        title = "<untitled page>"

    print(f"\n=== PAGE: {title} ({page_id}) ===")
    _print_block_recursive(notion, page_id, indent=0, preview_len=preview_len)


def explore_database(
    notion: Client,
    database_id: str,
    show_rows: bool = False,
    max_rows: Optional[int] = None,
    preview_len: int = 10,
):
    """Print the schema of a Notion database and optionally preview its rows."""
    try:
        database = notion.databases.retrieve(database_id)
    except Exception as exc:
        print(f"Error retrieving database {database_id}: {exc}")
        return

    db_title = _print_rich_text(database.get("title", [])) or "<untitled database>"
    print(f"\n=== DATABASE: {db_title} ({database_id}) ===")

    # Print properties
    print("\nProperties:")
    for prop_name, prop in database.get("properties", {}).items():
        print(f"  - {prop_name}: {prop.get('type')}")

    if not show_rows:
        return

    print("\nRows:")
    try:
        rows_response = notion.databases.query(database_id=database_id)
    except Exception as exc:
        print(f"  (Failed to query rows: {exc})")
        return

    rows = rows_response.get("results", [])
    if max_rows is not None:
        rows = rows[: max_rows]

    for idx, row in enumerate(rows, 1):
        row_props = row.get("properties", {})
        # Title property preview
        title_preview = "<no title>"
        for prop in row_props.values():
            if prop.get("type") == "title":
                title_preview = _preview(_print_rich_text(prop.get("title", [])), preview_len) or title_preview
                break
        # Build preview of other properties
        prop_snippets = []
        for name, prop in row_props.items():
            if prop.get("type") == "title":
                continue
            val_str = _preview(_property_to_str(prop), preview_len)
            if val_str:
                prop_snippets.append(f"{name}: {val_str}")
        snippets_str = "; ".join(prop_snippets)
        if snippets_str:
            print(f"  {idx}. {title_preview} ({snippets_str}) [row id: {row['id']}]")
        else:
            print(f"  {idx}. {title_preview} [row id: {row['id']}]")


def main():
    parser = argparse.ArgumentParser(description="Explore a Notion page or database by title.")
    parser.add_argument("--title", required=True, help="Title (or partial title) of the page/database to explore.")
    parser.add_argument(
        "--type",
        choices=["page", "database"],
        default="page",
        help="Specify whether the title refers to a page or a database (default: page).",
    )
    parser.add_argument(
        "--show-rows",
        action="store_true",
        help="When exploring a database, also list its rows (pages).",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=10,
        help="Maximum number of rows to show when --show-rows is enabled (default: 10).",
    )
    parser.add_argument(
        "--preview-len",
        type=int,
        default=10,
        help="Number of characters to preview for block text and property values (default: 10)",
    )

    args = parser.parse_args()

    notion = nutils.get_notion_client()

    if args.type == "page":
        page_id = nutils.find_page(notion, args.title)
        if not page_id:
            print(f"No page found with title containing '{args.title}'.")
            sys.exit(1)
        explore_page(notion, page_id, preview_len=args.preview_len)
    else:  # database
        db_id = nutils.find_database(notion, args.title)
        if not db_id:
            print(f"No database found with title containing '{args.title}'.")
            sys.exit(1)
        explore_database(
            notion,
            db_id,
            show_rows=args.show_rows,
            max_rows=args.max_rows,
            preview_len=args.preview_len,
        )


if __name__ == "__main__":
    main() 