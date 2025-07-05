#!/usr/bin/env python3
"""
Verify that the resume entry page has been created/updated as expected.

Usage:
    python verify_resume_modify.py <page_id>

Expected properties:
    Skill          : LLM Training (title)
    Type           : Machine Learning Engineer (select)
    Skill Level    : <= 0.3 (number)

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

EXPECTED_SKILL_TITLE = "LLM Training"
EXPECTED_TYPE = "Machine Learning Engineer"
SKILL_LEVEL_THRESHOLD = 0.3


# ---------------------------------------------------------------------------
# Verification helper
# ---------------------------------------------------------------------------

def verify_page(page_id: str) -> None:
    """Retrieve the page from Notion and assert that it matches expectations."""

    notion = Client(auth=os.environ["NOTION_API_KEY"])
    page = notion.pages.retrieve(page_id=page_id)

    mismatches = []

    properties = page.get("properties", {})

    # --- Verify Skill (title) ---
    title_parts = properties.get("Skill", {}).get("title", [])
    skill_title = "".join(part["plain_text"] for part in title_parts)
    if skill_title != EXPECTED_SKILL_TITLE:
        mismatches.append(
            f"Skill title mismatch: got '{skill_title}', expect '{EXPECTED_SKILL_TITLE}'"
        )

    # --- Verify Type (select) ---
    type_info = properties.get("Type", {}).get("select")
    type_name = type_info.get("name") if type_info else None
    if type_name != EXPECTED_TYPE:
        mismatches.append(
            f"Type mismatch: got '{type_name}', expect '{EXPECTED_TYPE}'"
        )

    # --- Verify Skill Level (number) ---
    skill_level_val = properties.get("Skill Level", {}).get("number")
    if skill_level_val is None or skill_level_val > SKILL_LEVEL_THRESHOLD:
        mismatches.append(
            f"Skill Level mismatch: got '{skill_level_val}', expect <= '{SKILL_LEVEL_THRESHOLD}'"
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
        print("Usage: verify_resume_modify.py <page_id>")
        sys.exit(1)

    page_id = sys.argv[1]
    verify_page(page_id)


if __name__ == "__main__":
    main() 