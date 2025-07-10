import sys
from notion_client import Client
from tasks.utils import notion_utils

def verify(notion: Client) -> bool:
    """
    Verifies that the skill 'LLM Training' has been added correctly.
    """
    page_id = notion_utils.find_page(notion, "Maya Zhang")
    if not page_id:
        print("Error: Page 'Maya Zhang' not found.", file=sys.stderr)
        return False

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
