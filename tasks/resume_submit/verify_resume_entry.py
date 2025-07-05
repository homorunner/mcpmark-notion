#!/usr/bin/env python3
"""
Verify that the resume entry page has been created/updated as expected.

Usage:
    python verify_resume_entry.py <page_id>

Expected properties:
    Full Name      : Zijian Wu
    Email          : zijian.wu@u.nus.edu
    Phone Number   : +65 80390985
    Relevant Links : https://www.linkedin.com/in/zijian-wu-7780231a3/
    Cover Letter   : Hi there👋
    Status         : Applied (status property)

The script exits with code 0 when all checks pass and prints a success
message. Otherwise it prints which field mismatched and exits with a
non-zero status.
"""

import os
import sys
from notion_client import Client

# ---------------------------------------------------------------------------
# Expected constants
# ---------------------------------------------------------------------------

EXPECTED_FULL_NAME = "Zijian Wu"
EXPECTED_EMAIL = "zijian.wu@u.nus.edu"
EXPECTED_PHONE = "+65 80390985"
EXPECTED_LINK = "https://www.linkedin.com/in/zijian-wu-7780231a3/"
EXPECTED_COVER_LETTER = "Hi there👋"
EXPECTED_STATUS_NAME = "Applied"


# ---------------------------------------------------------------------------
# Verification helper
# ---------------------------------------------------------------------------

def verify_page(page_id: str) -> None:
    """Retrieve the page from Notion and assert that it matches expectations."""

    notion = Client(auth=os.environ["NOTION_API_KEY"])
    page = notion.pages.retrieve(page_id=page_id)

    mismatches = []

    properties = page.get("properties", {})

    # --- Verify Full Name (title) ---
    title_parts = properties.get("Full Name", {}).get("title", [])
    full_name = "".join(part["plain_text"] for part in title_parts)
    if full_name != EXPECTED_FULL_NAME:
        mismatches.append(
            f"Full Name mismatch: got '{full_name}', expect '{EXPECTED_FULL_NAME}'"
        )

    # --- Verify Email ---
    email_val = properties.get("Email", {}).get("email")
    if email_val != EXPECTED_EMAIL:
        mismatches.append(
            f"Email mismatch: got '{email_val}', expect '{EXPECTED_EMAIL}'"
        )

    # --- Verify Phone Number ---
    phone_val = properties.get("Phone Number", {}).get("phone_number")
    if phone_val != EXPECTED_PHONE:
        mismatches.append(
            f"Phone Number mismatch: got '{phone_val}', expect '{EXPECTED_PHONE}'"
        )

    # --- Verify Relevant Links (url) ---
    url_val = properties.get("Relevant Links", {}).get("url")
    if url_val != EXPECTED_LINK:
        mismatches.append(
            f"Relevant Links mismatch: got '{url_val}', expect '{EXPECTED_LINK}'"
        )

    # --- Verify Cover Letter (rich_text) ---
    cover_parts = properties.get("Cover Letter", {}).get("rich_text", [])
    cover_letter = "".join(part["plain_text"] for part in cover_parts)
    if cover_letter != EXPECTED_COVER_LETTER:
        mismatches.append(
            f"Cover Letter mismatch: got '{cover_letter}', expect '{EXPECTED_COVER_LETTER}'"
        )

    # --- Verify Status (name) ---
    status_info = properties.get("Status", {}).get("status")
    status_name = status_info.get("name") if status_info else None
    if status_name != EXPECTED_STATUS_NAME:
        mismatches.append(
            f"Status mismatch: got '{status_name}', expect '{EXPECTED_STATUS_NAME}'"
        )

    # ---------------------------------------------------------------------
    # Report mismatches / success
    # ---------------------------------------------------------------------
    if mismatches:
        for msg in mismatches:
            print(f"❌ {msg}", file=sys.stderr)
        sys.exit(1)

    print("✅ All checks passed")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: verify_resume_entry.py <page_id>")
        sys.exit(1)

    page_id = sys.argv[1]
    verify_page(page_id)


if __name__ == "__main__":
    main() 