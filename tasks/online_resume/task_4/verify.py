import sys
from notion_client import Client
from tasks.utils import notion_utils

def verify(notion: Client, main_id: str = None) -> bool:
    """
    Verifies that the 'Bees Together Landing Page' project has been updated correctly.
    """
    page_id = None
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(notion, main_id)
        if found_id and object_type == 'page':
            page_id = found_id
    
    if not page_id:
        page_id = notion_utils.find_page(notion, "Maya Zhang")
    if not page_id:
        print("Error: Page 'Maya Zhang' not found.", file=sys.stderr)
        return False

    database_id = notion_utils.find_database_in_block(notion, page_id, "Projects")
    if not database_id:
        print("Error: Database 'Projects' not found.", file=sys.stderr)
        return False

    TARGET_NAME = "Bees Together Landing Page"
    EXPECTED_START_STR = "2023-08-15"
    
    pages = notion.databases.query(database_id=database_id).get("results")
    
    for page in pages:
        props = page.get("properties", {})

        title_fragments = props.get("Name", {}).get("title", [])
        name = "".join(t["plain_text"] for t in title_fragments).strip()
        if name != TARGET_NAME:
            continue

        tags_prop = props.get("Tags", {})
        tag_names = [t["name"] for t in tags_prop.get("multi_select", [])]

        if "UI Design" in tag_names:
            print(f"Failure: 'UI Design' tag is still present for '{TARGET_NAME}'.", file=sys.stderr)
            return False
        
        expected_tags = {"Non-Profit", "Design Assets", "Website Dev"}
        if not expected_tags.issubset(set(tag_names)):
             print(f"Failure: Expected tags not found for '{TARGET_NAME}'.", file=sys.stderr)
             return False

        date_info = props.get("Date", {}).get("date", {})
        start_raw = date_info.get("start")
        if not start_raw:
            print(f"Failure: Start date is missing for '{TARGET_NAME}'.", file=sys.stderr)
            return False

        if str(start_raw).split('T')[0] != EXPECTED_START_STR:
            print(f"Failure: Start date for '{TARGET_NAME}' is not '{EXPECTED_START_STR}'.", file=sys.stderr)
            return False

        print(f"Success: Project '{TARGET_NAME}' was updated correctly.")
        return True
    
    print(f"Failure: Project '{TARGET_NAME}' not found.", file=sys.stderr)
    return False

def main():
    """
    Executes the verification process and exits with a status code.
    """
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
