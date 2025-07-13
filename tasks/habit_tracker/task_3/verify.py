import sys
from typing import List, Tuple
from notion_client import Client
from tasks.utils import notion_utils

EXPECTED_HEADERS = [
    "Habit name",
    "# of days completed",
    "Status",
    "Missed completely?",
]

# (habit name, days_completed(int), status lowercase, missed lowercase yes/no)
EXPECTED_ROWS: List[Tuple[str, int, str, str]] = [
    ("10k steps", 4, "making progress", "no"),
    ("8 hours of sleep", 3, "making progress", "no"),
    ("drink 2l of water", 2, "barely started", "no"),
    ("1 fruit", 2, "barely started", "no"),
    ("skin care", 2, "barely started", "no"),
    ("read 5 pages", 0, "barely started", "yes"),
    ("meditation", 0, "barely started", "yes"),
]


def _plain_text_from_cell(cell):
    return "".join(rt.get("plain_text", "") for rt in cell).strip()


def _normalize_row(cells: List[str]) -> Tuple[str, int, str, str]:
    """Convert raw strings to canonical tuple."""
    habit = cells[0].strip().lower()
    # Days completed to int
    try:
        days = int(cells[1].strip())
    except ValueError:
        days = -1  # invalid
    status = cells[2].strip().lower()
    missed = cells[3].strip().lower()
    return (habit, days, status, missed)


def verify(notion: Client) -> bool:
    # Locate Habit Tracker page
    page_id = notion_utils.find_page(notion, "habit tracker") or notion_utils.find_page(notion, "Habit Tracker")
    if not page_id:
        print("Error: Habit Tracker page not found.", file=sys.stderr)
        return False

    # Fetch only direct child blocks of the page (one level) to find the summary table
    try:
        blocks = notion.blocks.children.list(block_id=page_id).get("results", [])
    except Exception as e:
        print(f"Error retrieving child blocks of Habit Tracker page: {e}", file=sys.stderr)
        return False

    table_blocks = [b for b in blocks if b.get("type") == "table"]
    if not table_blocks:
        print("Error: No table blocks found in Habit Tracker page.", file=sys.stderr)
        return False

    target_table_id = None
    header_row = None

    # Identify the table whose header matches expected
    for tb in table_blocks:
        rows = notion.blocks.children.list(block_id=tb["id"]).get("results", [])
        if not rows:
            continue
        first_row_cells = rows[0].get("table_row", {}).get("cells", [])
        header_texts = [_plain_text_from_cell(c) for c in first_row_cells]
        if [h.lower() for h in header_texts] == [h.lower() for h in EXPECTED_HEADERS]:
            target_table_id = tb["id"]
            header_row = rows[0]
            data_rows = rows[1:]
            break

    if not target_table_id:
        print("Error: Table with expected headers not found.", file=sys.stderr)
        return False

    # Parse data rows
    parsed_rows: List[Tuple[str, int, str, str]] = []
    for r in data_rows:
        cells = r.get("table_row", {}).get("cells", [])
        if len(cells) < 4:
            continue
        texts = [_plain_text_from_cell(c) for c in cells]
        parsed_rows.append(_normalize_row(texts))

    # Validate row count
    if len(parsed_rows) != len(EXPECTED_ROWS):
        print(f"Error: Expected {len(EXPECTED_ROWS)} data rows, found {len(parsed_rows)}.", file=sys.stderr)
        return False

    expected_set = set(EXPECTED_ROWS)
    actual_set = set(parsed_rows)

    if expected_set != actual_set:
        missing = expected_set - actual_set
        extra = actual_set - expected_set
        if missing:
            print(f"Error: Missing rows: {missing}", file=sys.stderr)
        if extra:
            print(f"Error: Unexpected extra rows: {extra}", file=sys.stderr)
        return False

    print("Success: Weekly summary table verified successfully.")
    return True


def main():
    notion = notion_utils.get_notion_client()
    if verify(notion):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main() 