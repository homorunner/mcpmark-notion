"""
Demo script to search for a Notion page named "STUDY PLANNER" and create a sample database under it.

Usage:
  1. Export your integration token before running:
       export NOTION_TOKEN="your_secret_token"
  2. Ensure the integration has access to the page titled "STUDY PLANNER".
  3. Run the script:
       python create_notion_database_demo.py
"""

import os
from typing import Optional, Dict, Any

from notion_client import Client


def find_page(client: Client, page_title: str) -> Optional[Dict[str, Any]]:
    """Search for a page by its title and return the corresponding page object.

    Args:
        client: An authenticated Notion Client instance.
        page_title: The exact title of the page to look for.

    Returns:
        The first matching page object, or None if not found.
    """
    search_response = client.search(
        query=page_title,
        filter={"property": "object", "value": "page"},
        page_size=25,
    )

    for result in search_response.get("results", []):
        # Notion stores the page title inside the first property of type "title".
        title_text = ""
        if "properties" in result:
            for prop in result["properties"].values():
                if prop["type"] == "title":
                    title_text = "".join(rt["plain_text"] for rt in prop["title"])
                    break
        # Fallback for older page objects (rare)
        if not title_text and "title" in result:
            title_text = "".join(rt["plain_text"] for rt in result["title"])

        if title_text == page_title:
            return result

    return None


def create_demo_database(client: Client, parent_page_id: str) -> Dict[str, Any]:
    """Create a demo database under the specified page ID with a simple schema."""
    database_title = "Demo Database"
    sample_properties = {
        "Name": {"title": {}},
        "Status": {
            "select": {
                "options": [
                    {"name": "Not Started", "color": "red"},
                    {"name": "In Progress", "color": "yellow"},
                    {"name": "Completed", "color": "green"},
                ]
            }
        },
        "Priority": {
            "select": {
                "options": [
                    {"name": "Low", "color": "green"},
                    {"name": "Medium", "color": "yellow"},
                    {"name": "High", "color": "red"},
                ]
            }
        },
        "Due Date": {"date": {}},
    }

    return client.databases.create(
        parent={"page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": database_title}}],
        properties=sample_properties,
    )


def main() -> None:
    token = os.getenv("NOTION_API_KEY")
    if not token:
        raise EnvironmentError(
            "Environment variable NOTION_TOKEN is missing. "
            "Create an internal integration at https://www.notion.so/my-integrations and "
            "share the target page with it, then export its token: \n"
            "  export NOTION_TOKEN='secret_xxx'"
        )

    client = Client(auth=token)

    page = find_page(client, "STUDY PLANNER")
    if page is None:
        print("[!] Could not find a page titled 'STUDY PLANNER'. Ensure the integration has access to it.")
        return

    page_id = page["id"]
    print(f"[+] Found page 'STUDY PLANNER' (ID: {page_id}). Creating a demo database under it…")

    database = create_demo_database(client, page_id)

    print("[✓] Database created successfully!")
    print("    • Database ID:", database["id"])
    print("    • URL:", database.get("url", "<URL unavailable>"))


if __name__ == "__main__":
    main() 