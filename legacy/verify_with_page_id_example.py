import sys
import os
from notion_client import Client
from tasks.utils import notion_utils

def verify(notion: Client) -> bool:
    """
    Example verification script that supports both page name search and direct page ID.
    This shows how to modify existing verification scripts to support page duplication.
    """
    # Check if a specific page ID was provided through environment variable
    page_id = os.getenv("MCPBENCH_PAGE_ID")
    
    if page_id:
        print(f"Using provided page ID: {page_id}", file=sys.stderr)
        # Verify the page exists
        try:
            page = notion.pages.retrieve(page_id=page_id)
            if page.get("archived", False):
                print(f"Error: Page {page_id} is archived.", file=sys.stderr)
                return False
        except Exception as e:
            print(f"Error: Could not retrieve page {page_id}: {e}", file=sys.stderr)
            return False
    else:
        # Fall back to searching by name (original behavior)
        print("No page ID provided, searching by name...", file=sys.stderr)
        page_id = notion_utils.find_page(notion, "Maya Zhang")
        if not page_id:
            print("Error: Page 'Maya Zhang' not found.", file=sys.stderr)
            return False

    # Continue with verification using the page_id
    database_id = notion_utils.find_database_in_block(notion, page_id, "Skills")
    if not database_id:
        print("Error: Database 'Skills' not found.", file=sys.stderr)
        return False

    skill_name = "LLM Training"
    skill_type = "Machine Learning Engineer"
    skill_level = 0.5  # 50%

    results = notion.databases.query(database_id=database_id).get("results")
    for page in results:
        properties = page.get("properties", {})
        
        current_skill_name_list = properties.get("Skill", {}).get("title", [])
        current_skill_name = current_skill_name_list[0].get("text", {}).get("content") if current_skill_name_list else None
        
        current_skill_type = properties.get("Type", {}).get("select", {}).get("name")
        current_skill_level = properties.get("Skill Level", {}).get("number")

        if (current_skill_name == skill_name and
            current_skill_type == skill_type and
            current_skill_level == skill_level):
            print(f"Success: Verified that the skill '{skill_name}' was added correctly.")
            return True

    print(f"Failure: Could not verify that the skill '{skill_name}' was added correctly.", file=sys.stderr)
    return False

def main():
    """
    Executes the verification process and exits with a status code.
    """
    notion = notion_utils.get_notion_client()
    if verify(notion):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()