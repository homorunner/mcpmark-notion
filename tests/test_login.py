#!/usr/bin/env python3
"""Test Notion Login State
=========================

This script verifies if the existing ``notion_state.json`` is still valid by
launching a browser, loading the saved state, and checking if Notion
automatically redirects away from the login page.

This provides a quick way to check if you need to run ``notion_login.py``
again before starting a longer evaluation task.

Example usage
-------------

    # Verify login state in headless mode (default)
    python tests/test_login.py

    # Verify login state in a visible browser window
    python tests/test_login.py --gui
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ---------------------------------------------------------------------------
# Ensure the "src" directory is importable even when running from project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = PROJECT_ROOT / "notion_state.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the validity of the existing notion_state.json.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Run the verification in a visible browser window (headless by default).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    is_headless = not args.gui

    print("🚀 Starting Notion login verification…")

    if not STATE_PATH.exists():
        print(f"❌ State file not found at: {STATE_PATH}")
        print("Please run `python notion_login.py` first to create it.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=is_headless)
        context = browser.new_context(storage_state=STATE_PATH)
        page = context.new_page()

        login_url = "https://www.notion.so/login"
        print(f"🔗 Navigating to {login_url} to test session...")

        try:
            page.goto(login_url, wait_until="domcontentloaded")
            # Wait for the URL to change, indicating a successful redirect.
            # We use a generous timeout to account for network speed.
            page.wait_for_url(lambda url: url != login_url, timeout=30_000)

            final_url = page.url
            print(f"✅ Login state is valid. Redirected successfully to: {final_url}")

        except PlaywrightTimeoutError:
            print("❌ Login state appears to be invalid or expired.")
            print("Failed to redirect from the login page within the time limit.")
            print("Please run `python notion_login.py` again.")
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            sys.exit(1)
        finally:
            browser.close()

    print("🎉 Verification complete.")


if __name__ == "__main__":
    main() 