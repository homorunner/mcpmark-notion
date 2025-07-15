#!/usr/bin/env python3
"""Notion Login Helper for MCPBench
=================================

Run this script *once* before executing the evaluation pipeline or any
Playwright-driven utilities. It guides you through the Notion authentication
flow (either in a visible browser window or via terminal prompts in headless
mode) and saves the resulting session cookies / localStorage to
``notion_state.json`` in the project root.

Example usage
-------------

    # Open a visible browser window and let the user login manually
    python notion_login.py --url https://www.notion.so/your-template

    # Perform login fully headless (prompts for credentials in the terminal)
    python notion_login.py --url https://www.notion.so/your-template --headless
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the "src" directory is importable even when running from project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.notion_login_helper import NotionLoginHelper  # noqa: E402  pylint: disable=wrong-import-position


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Authenticate to Notion and generate notion_state.json for subsequent tasks.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the login flow in headless mode (prompts for credentials in the terminal).",
    )

    parser.add_argument(
        "--browser",
        default="firefox",
        choices=["chromium", "firefox"],
        help="Which browser engine to use for Playwright.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("🚀 Starting Notion login helper…")

    # URL is no longer passed; NotionLoginHelper will default to the login page.
    client = NotionLoginHelper(headless=args.headless, browser=args.browser)
    try:
        client.login()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Login failed: {exc}")
        sys.exit(1)
    finally:
        client.close()

    print("🎉 All done! You can now run the evaluation pipeline.")


if __name__ == "__main__":
    main() 