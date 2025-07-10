"""notion_duplicate_page.py
Automate duplication of a Notion page via Playwright.

Usage (environment variables preferred):
    export NOTION_EMAIL="your_email"
    export NOTION_PASSWORD="your_password"
    python notion_duplicate_page.py --page https://www.notion.so/your-workspace/page-id

CLI flags override env vars:
    --email EMAIL          Notion login email
    --password PASSWORD    Notion login password
    --page PAGE_URL        Absolute URL of the page to duplicate (required)
    --headless             Run browser in headless mode (default off)

Notes:
1. Two-factor authentication flows are NOT handled – log into Notion once in an
   interactive (non-headless) run and the session will be cached in the browser
   profile for subsequent executions.
2. Selectors are based on current Notion DOM and may break if the UI changes.
   Adjust the *_SELECTOR constants below if the script stops working.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright, Browser, Page

# ---------------------------------------------------------------------------
# Configurable selectors (keep them close together for easy updates)
# ---------------------------------------------------------------------------
PAGE_MENU_BUTTON_SELECTOR: Final[str] = 'div.notion-topbar-more-button'
# Use plain text to avoid relying on Notion internal roles/structure
DUPLICATE_MENU_ITEM_SELECTOR: Final[str] = 'text="Duplicate"'

LOGIN_EMAIL_INPUT: Final[str] = 'input[type="email"]'
LOGIN_CONTINUE_BUTTON: Final[str] = 'button:has-text("Continue with email")'
LOGIN_PASSWORD_INPUT: Final[str] = 'input[type="password"]'
LOGIN_SUBMIT_BUTTON: Final[str] = 'button:has-text("Continue with password")'

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[NotionDup] {msg}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Duplicate a Notion page via Playwright")
    parser.add_argument("--page", required=True, help="Absolute URL of the Notion page to duplicate")
    parser.add_argument(
        "--headless", action="store_true", help="Run browser in headless mode (default brings up a visible window)"
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Core automation logic
# ---------------------------------------------------------------------------

def login_if_needed(page: Page, email: str, password: str) -> None:
    """Perform login if Notion redirects to the sign-in page."""
    if "notion.so/login" not in page.url:
        return  # Already authenticated

    if not email or not password:
        log("Missing credentials and interactive login required – aborting.")
        sys.exit(1)

    log("Filling email…")
    page.fill(LOGIN_EMAIL_INPUT, email)
    page.click(LOGIN_CONTINUE_BUTTON)
    page.wait_for_selector(LOGIN_PASSWORD_INPUT)

    log("Filling password…")
    page.fill(LOGIN_PASSWORD_INPUT, password)
    page.click(LOGIN_SUBMIT_BUTTON)
    # Wait for workspace to load (any internal URL)
    page.wait_for_url("https://www.notion.so/*", timeout=90_000)
    log("Logged in successfully ✅")


def duplicate_current_page(page: Page) -> None:
    """Open the page menu (•••) and click Duplicate once."""
    try:
        log("Opening page menu…")
        page.wait_for_selector(PAGE_MENU_BUTTON_SELECTOR, state="visible", timeout=20_000)
        page.click(PAGE_MENU_BUTTON_SELECTOR)

        log("Clicking Duplicate…")
        page.wait_for_selector(DUPLICATE_MENU_ITEM_SELECTOR, timeout=15_000)
        page.click(DUPLICATE_MENU_ITEM_SELECTOR)

        original_url = page.url
        log("Waiting for duplicated page to load (up to 60 s)…")
        try:
            page.wait_for_url(lambda url: url != original_url, timeout=60_000)
            log(f"✅ Duplicated page loaded at {page.url}")
        except PlaywrightTimeoutError:
            log("❌ Timed out waiting for the duplicated page. Please check manually.")
            page.pause()
    except PlaywrightTimeoutError:
        log("❌ Failed to duplicate. Ensure the page is fully loaded, duplicate manually if needed.")
        page.pause()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    # Ensure Playwright browsers are installed (run once)
    if not (Path.home() / ".cache/ms-playwright").exists():
        log("First-time setup – downloading browsers (this may take a minute)…")
        import subprocess, sys

        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=args.headless)
        state_file = Path("notion_state.json")
        context = browser.new_context(
            storage_state=str(state_file) if state_file.exists() else None
        )
        page = context.new_page()

        log("Navigating to page to duplicate…")
        page.goto(args.page, wait_until="load")

        # 1) If we are on the login page, let the user log in manually
        if "notion.so/login" in page.url:
            log("Login required – please sign in manually in the browser window, then press ▶ resume to continue…")
            page.pause()

        # Immediately save cookies after login to reuse the session next time
        context.storage_state(path=str(state_file))

        # Ensure we are back on the target page after login
        if page.url != args.page:
            log("Returning to target page…")
            page.goto(args.page, wait_until="load")

        duplicate_current_page(page)

        log("Script finished – you may close the browser window now.")
        context.storage_state(path=str(state_file))


if __name__ == "__main__":
    main() 