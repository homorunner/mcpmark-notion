import sys
from notion_client import Client
from tasks.utils import notion_utils


def normalize_string(s):
    return s.replace('\xa0', ' ')

def verify(notion: Client, main_id: str = None) -> bool:
    """
    Verifies that '🇨🇳 Chinese' has been added under the 'Languages' heading.
    """
    page_id = None
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(notion, main_id)
        if found_id and object_type == 'page':
            page_id = found_id
    
    if not page_id:
        page_id = notion_utils.find_page(notion, "Online Resume")
    if not page_id:
        print("Error: Page 'Online Resume' not found.", file=sys.stderr)
        return False

    all_blocks = notion_utils.get_all_blocks_recursively(notion, page_id)

    heading_text = "Languages"
    language_entry = "🇨🇳\xa0Chinese"
    
    heading_found = False
    for i, block in enumerate(all_blocks):
        block_type = block.get("type")
        if block_type in ["heading_1", "heading_2", "heading_3"]:
            if heading_found: # we've passed the languages section
                break
            if heading_text in notion_utils.get_block_plain_text(block):
                heading_found = True
                continue
        
        if heading_found:
            if normalize_string(language_entry) == normalize_string(notion_utils.get_block_plain_text(block)) and "English" in notion_utils.get_block_plain_text(all_blocks[i-1]):
                print(f"Success: Verified that '{language_entry}' was added under '{heading_text}'.")
                return True

    if not heading_found:
        print(f"Error: Could not find the '{heading_text}' heading.", file=sys.stderr)
    else:
        print(f"Failure: Could not find '{language_entry}' under the '{heading_text}' section.", file=sys.stderr)
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
