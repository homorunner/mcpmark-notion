"""Example – Duplicate a single page by URL

Provide the page URL and the desired *new* title for the copy. The duplicated
page will appear alongside the original (same parent).

Run:
    python example/duplicate_current_page_demo.py
"""
from pathlib import Path

from tasks.utils.page_duplication import duplicate_current_page, log
from playwright.sync_api import sync_playwright, Browser

# ----- CONFIG – replace below ------------------------------------------------
PAGE_URL = "https://www.notion.so/YOUR-PAGE-URL"  # ← replace
NEW_TITLE = "My New Copy"                         # ← replace
HEADLESS = True                                   # run without UI
# -----------------------------------------------------------------------------


def main() -> None:
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=HEADLESS)
        state_file = Path("notion_state.json")
        context = browser.new_context(storage_state=str(state_file) if state_file.exists() else None)
        page = context.new_page()

        log("Navigating to target page…")
        page.goto(PAGE_URL, wait_until="load")

        if "notion.so/login" in page.url:
            log("Please complete login in the browser window, then resume…")
            page.pause()

        # Persist session for future runs
        context.storage_state(path=str(state_file))

        duplicate_current_page(page, NEW_TITLE)

        log("All done – you can close the browser now.")
        context.storage_state(path=str(state_file))


if __name__ == "__main__":
    main() 