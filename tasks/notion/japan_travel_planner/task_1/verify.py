import sys
from notion_client import Client
from tasks.utils import notion_utils

def verify(notion: Client, main_id: str = None) -> bool:
    """
    Verifies that 'Osaka Castle' is in 'Day 2' of the 'Travel Itinerary'.
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

    database_id = notion_utils.find_database_in_block(notion, page_id, "Travel Itinerary")
    if not database_id:
        print("Error: Database 'Travel Itinerary' not found.", file=sys.stderr)
        return False

    results = notion.databases.query(database_id=database_id).get("results")
    
    for page in results:
        properties = page.get("properties", {})
        
        name_list = properties.get("Name", {}).get("title", [])
        card_name = name_list[0].get("text", {}).get("content") if name_list else None
        
        if card_name == "Osaka Castle":
            day_property = properties.get("Day", {}).get("select", {})
            day_name = day_property.get("name") if day_property else "Not specified"
            if day_name == "Day 2":
                print("Success: 'Osaka Castle' is in 'Day 2'.")
                return True
    
    print("Failure: 'Osaka Castle' is not in 'Day 2'.", file=sys.stderr)
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
