import sys
from notion_client import Client
from tasks.utils import notion_utils

def verify(notion: Client) -> bool:
    """
    Verifies that '🇨🇳 Chinese' has been added under the 'Languages' heading.
    """
    page_id = notion_utils.find_page(notion, "Maya Zhang")
    if not page_id:
        print("Error: Page 'Maya Zhang' not found.", file=sys.stderr)
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
            if language_entry == notion_utils.get_block_plain_text(block) and "English" in notion_utils.get_block_plain_text(all_blocks[i-1]):
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
    if verify(notion):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
