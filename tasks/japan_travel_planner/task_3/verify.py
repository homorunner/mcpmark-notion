import sys
from notion_client import Client
from tasks.utils import notion_utils

def verify(notion: Client, main_id: str = None) -> bool:
    """
    Verifies that the new expense 'OpenAI API cost' has been added correctly.
    """
    page_id = None
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(notion, main_id)
        if found_id and object_type == 'page':
            page_id = found_id
    
    if not page_id:
        page_id = notion_utils.find_page(notion, "Japan Travel Planner")
    if not page_id:
        print("Error: Page 'Japan Travel Planner' not found.", file=sys.stderr)
        return False

    database_id = notion_utils.find_database_in_block(notion, page_id, "Expenses")
    if not database_id:
        print("Error: Database 'Expenses' not found.", file=sys.stderr)
        return False

    results = notion.databases.query(database_id=database_id).get("results")

    for page in results:
        props = page["properties"]

        title_prop = props.get("Expense", {})
        title_text = "".join(t["plain_text"] for t in title_prop.get("title", []))
        if title_text != "OpenAI API cost":
            continue

        date_start = props.get("Date", {}).get("date", {}).get("start")
        if date_start != "2025-01-03":
            continue

        amount = props.get("Transaction Amount", {}).get("number")
        if amount != 300:
            continue

        categories = props.get("Category", {}).get("multi_select", [])
        if "AI" not in [c["name"] for c in categories]:
            continue
        
        print("Success: Found matching expense entry for 'OpenAI API cost'.")
        return True

    print("Failure: Could not find a matching expense entry for 'OpenAI API cost'.", file=sys.stderr)
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
