import os
from notion_client import Client
import sys
from dotenv import load_dotenv

def get_notion_client():
    # Construct the absolute path to the .env file in the project root
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    load_dotenv(dotenv_path=dotenv_path)
    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        print("Error: NOTION_API_KEY not found in environment variables.", file=sys.stderr)
        sys.exit(1)
    return Client(auth=api_key)

def find_page(notion: Client, page_title: str):
    """
    Finds a page by its title.
    """
    search_results = notion.search(query=page_title, filter={"property": "object", "value": "page"}).get("results")
    if not search_results:
        return None
    return search_results[0]["id"]

def find_database_in_block(notion: Client, block_id: str, db_title: str):
    """
    Recursively find a database by title within a block.
    """
    blocks = notion.blocks.children.list(block_id=block_id).get("results")
    for block in blocks:
        if block.get("type") == "child_database" and block.get("child_database", {}).get("title") == db_title:
            return block["id"]
        if block.get("has_children"):
            db_id = find_database_in_block(notion, block["id"], db_title)
            if db_id:
                return db_id
    return None

def get_all_blocks_recursively(notion: Client, block_id: str):
    """
    Recursively fetches all blocks from a starting block ID and its children,
    returning a single flat list of block objects.
    """
    all_blocks = []
    try:
        direct_children = notion.blocks.children.list(block_id=block_id).get("results", [])
    except Exception:
        return []

    for block in direct_children:
        all_blocks.append(block)
        if block.get("has_children"):
            all_blocks.extend(get_all_blocks_recursively(notion, block["id"]))
    
    return all_blocks

def get_block_plain_text(block):
    """
    Safely extract plain_text from a block (paragraph, heading, etc.).
    """
    block_type = block.get("type")
    if not block_type:
        return ""
    
    block_content = block.get(block_type)
    if not block_content:
        return ""
    
    rich_text_list = block_content.get("rich_text", [])
    plain_text = "".join([rt.get("plain_text", "") for rt in rich_text_list])
    
    return plain_text
