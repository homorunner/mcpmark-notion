import sys
from notion_client import Client
from tasks.utils import notion_utils

def verify(notion: Client, main_id: str = None) -> bool:
    """
    For every entry in the "Social Media Content Planning System" database where:
      • Status == "Planning" (Status property)
      • Platform multi-select contains "YouTube"
    verify that Content Type == "Video".
    Returns True only if all such entries satisfy the condition and at least one
    matching entry exists.
    """
    db_title = "Social Media Content Planning System"
    database_id = None
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(notion, main_id)
        if found_id and object_type == 'database':
            database_id = found_id
    
    if not database_id:
        database_id = notion_utils.find_database(notion, db_title)
    if not database_id:
        print(f"Error: Database '{db_title}' not found.", file=sys.stderr)
        return False

    try:
        results = notion.databases.query(database_id=database_id).get("results", [])
    except Exception as e:
        print(f"Error: Failed to query database '{db_title}'. {e}", file=sys.stderr)
        return False

    target_entries = []
    failed_entries = []

    for entry in results:
        props = entry.get("properties", {})

        # Platforms list (property may be named 'Platform' or 'Platforms')
        platforms_prop = props.get("Platform") or props.get("Platforms")
        platforms = [opt.get("name") for opt in (platforms_prop or {}).get("multi_select", [])]

        # Current status (status property)
        status_prop = props.get("Status", {})
        status_name = (status_prop.get("status") or {}).get("name")

        # Filter pages that meet criteria
        if "YouTube" in platforms and status_name == "Planning":
            target_entries.append(entry)

            # Content Type (select property; sometimes named differently)
            type_prop = props.get("Content Type") or props.get("Content Type(s)") or props.get("Type")
            content_type_name = (type_prop or {}).get("select", {}).get("name")

            if content_type_name != "Video":
                failed_entries.append(entry)

    if not target_entries:
        print("Failure: No entries with Status 'Planning' and Platform containing 'YouTube' were found.", file=sys.stderr)
        return False

    if failed_entries:
        print(
            f"Failure: {len(failed_entries)}/{len(target_entries)} matching entries do not have Content Type set to 'Video'.",
            file=sys.stderr,
        )
        return False

    print(
        f"Success: All {len(target_entries)} entries with Status 'Planning' and Platform containing 'YouTube' have Content Type 'Video'."
    )
    return True


def main():
    """Executes the verification process and exits with a status code."""
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main() 