#!/usr/bin/env python3
"""
Verify that the calendar event page has been updated as expected.

Usage:
    python verify_calendar_event.py <page_id>

Expected properties:
    Icon     : 💻 (emoji)
    Location : "Zoom meeting" (case-insensitive)
    Date     : 2025-07-02 (start date)

The script exits with code 0 when all checks pass and prints a success
message.  Otherwise it prints which field mismatched and exits with a
non-zero status.
"""

import os
import sys
from notion_client import Client

EXPECTED_ICON = "💻"
EXPECTED_LOCATION = "Zoom meeting"  # lower-case for case-insensitive comparison
EXPECTED_DATE = "2025-07-02"


def verify_page(page_id: str) -> None:
    """Retrieve the page from Notion and assert that it matches expectations."""

    notion = Client(auth=os.environ["NOTION_API_KEY"])
    page = notion.pages.retrieve(page_id=page_id)

    mismatches = []

    # --- Verify Icon ---
    icon = page.get("icon")
    if not (icon and icon.get("type") == "emoji" and icon.get("emoji") == EXPECTED_ICON):
        mismatches.append(f"Icon mismatch: got '{icon}', expect emoji '{EXPECTED_ICON}'")

    # --- Verify Location ---
    location_parts = page["properties"]["Location"]["rich_text"]
    location = "".join(part["plain_text"] for part in location_parts)
    if location.lower() != EXPECTED_LOCATION.lower():
        mismatches.append(
            f"Location mismatch: got '{location}', expect '{EXPECTED_LOCATION}' (case-insensitive)"
        )

    # --- Verify Date ---
    date_start = page["properties"]["Date"]["date"]["start"]
    if date_start != EXPECTED_DATE:
        mismatches.append(f"Date mismatch: got '{date_start}', expect '{EXPECTED_DATE}'")

    if mismatches:
        for msg in mismatches:
            print(f"❌ {msg}", file=sys.stderr)
        sys.exit(1)

    print("✅ All checks passed")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: verify_calendar_event.py <page_id>")
        sys.exit(1)

    page_id = sys.argv[1]
    verify_page(page_id)


if __name__ == "__main__":
    main() 