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

    browsers_to_try = ["chromium", "firefox"]

    with sync_playwright() as p:
        success_browsers: list[str] = []

        for browser_name in browsers_to_try:
            try:
                print(f"🔍 Attempting verification using {browser_name}…")
                browser_type = getattr(p, browser_name)
                browser = browser_type.launch(headless=is_headless)

                context = browser.new_context(storage_state=STATE_PATH)
                page = context.new_page()

                login_url = "https://www.notion.so/login"
                print(f"🔗 Navigating to {login_url} to test session…")

                page.goto(login_url, wait_until="domcontentloaded")
                # Wait for the URL to change, indicating a successful redirect.
                page.wait_for_url(lambda url: url != login_url, timeout=30_000)

                final_url = page.url
                print(
                    f"✅ Login state validated in {browser_name}. Redirected to: {final_url}"
                )
                success_browsers.append(browser_name)
                browser.close()

            except PlaywrightTimeoutError:
                print(f"⚠️  {browser_name.capitalize()} could not verify login (timeout).")
                browser.close()
            except Exception as e:
                print(f"⚠️  {browser_name.capitalize()} launch/verification failed: {e}")
                try:
                    browser.close()
                except Exception:
                    pass
        if not success_browsers:
            print("❌ Login state appears to be invalid in both Chromium and Firefox.")
            print("Please run `python notion_login.py` again.")
            sys.exit(1)
        elif len(success_browsers) == len(browsers_to_try):
            print("✅ Login state validated in both Chromium and Firefox.")
        else:
            succeeded = success_browsers[0]
            print(
                f"ℹ️  Only {succeeded} succeeded. Consider using this browser engine for future runs."
            )

    print("🎉 Verification complete.")


if __name__ == "__main__":
    main() 