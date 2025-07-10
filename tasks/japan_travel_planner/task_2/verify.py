import sys
from notion_client import Client
from tasks.utils import notion_utils

def verify(notion: Client) -> bool:
    """
    Verifies that in the 'Packing List' for 'Clothes', 'Hat' is unchecked
    and all other items are checked.
    """
    page_id = notion_utils.find_page(notion, "Japan Travel Planner")
    if not page_id:
        print("Error: Page 'Japan Travel Planner' not found.", file=sys.stderr)
        return False

    database_id = notion_utils.find_database_in_block(notion, page_id, "Packing List")
    if not database_id:
        print("Error: Database 'Packing List' not found.", file=sys.stderr)
        return False

    results = notion.databases.query(database_id=database_id).get("results")
    
    hat_found = False
    for page in results:
        props = page["properties"]

        type_prop = props.get("Type", {})
        if type_prop.get("type") == "select":
            labels = [type_prop["select"]["name"]] if type_prop["select"] else []
        elif type_prop.get("type") == "multi_select":
            labels = [opt["name"] for opt in type_prop["multi_select"]]
        else:
            labels = []

        if "Clothes" not in labels:
            continue

        name = "".join(t["plain_text"] for t in props["Name"]["title"]).strip()
        packed = props.get("Packed", {}).get("checkbox", False)

        if name.lower() == "hat":
            if packed:
                print("Failure: Hat is marked as packed.", file=sys.stderr)
                return False
            hat_found = True
        else:
            if not packed:
                print(f"Failure: Clothes item '{name}' is not marked as packed.", file=sys.stderr)
                return False

    if not hat_found:
        print("Failure: 'Hat' row not found in 'Clothes' category.", file=sys.stderr)
        return False
    
    print("Success: Packing list for 'Clothes' is correctly updated.")
    return True

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
