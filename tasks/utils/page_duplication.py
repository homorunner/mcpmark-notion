"""page_duplication.py
Utility helpers for duplicating Notion pages using Playwright + Notion SDK.

Main entry points
-----------------
• duplicate_child_page(parent_url, source_title, target_title, *, headless=False)
    Recursively locate a child page under *parent_url*, duplicate it via Playwright,
    then rename the duplicated copy using the Notion API.

• duplicate_current_page(page: playwright.sync_api.Page, new_title: str | None)
    Low-level helper that operates on an *already opened* Page object.

All other functions are considered private.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Final, Optional

from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
    Browser,
    Page,
)

# ---------------------------------------------------------------------------
# Configurable selectors (update here if Notion UI changes)
# ---------------------------------------------------------------------------
PAGE_MENU_BUTTON_SELECTOR: Final[str] = "div.notion-topbar-more-button"
DUPLICATE_MENU_ITEM_SELECTOR: Final[str] = 'text="Duplicate"'


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Lightweight console logger."""
    print(f"[NotionDup] {msg}")


# ---------------------------------------------------------------------------
# Notion-SDK helpers (no Playwright)
# ---------------------------------------------------------------------------

def _extract_page_id_from_url(url: str) -> str:
    """Extract canonical UUID page ID from a Notion URL."""
    url = url.split("?")[0].split("#")[0]
    slug = url.rstrip("/").split("/")[-1]
    compact = "".join(c for c in slug if c.isalnum())
    if len(compact) < 32:
        raise ValueError(f"Could not parse page ID from URL: {url}")
    compact = compact[-32:]
    return f"{compact[0:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:]}"


def _rename_page_via_api(page_id: str, new_title: str) -> None:
    """Rename a Notion page using the official Notion SDK."""
    token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
    if not token:
        log("⚠️  NOTION_API_KEY/NOTION_TOKEN not set – skipping rename.")
        return

    try:
        from notion_client import Client  # imported lazily
    except ImportError:
        log("⚠️  notion-client library not available – skipping rename.")
        return

    client = Client(auth=token)
    try:
        client.pages.update(
            page_id=page_id,
            properties={
                "title": {
                    "title": [
                        {"type": "text", "text": {"content": new_title}}
                    ]
                }
            },
        )
        log(f"✅ Renamed page to '{new_title}' via Notion API")
    except Exception as exc:
        log(f"❌ Failed to rename page via Notion API: {exc}")


# ---------------------------------------------------------------------------
# Recursive search helper
# ---------------------------------------------------------------------------

def _find_child_page_id_recursive(notion_client, block_id: str, title: str) -> Optional[str]:
    """Recursively search *block_id* for a child page with the exact *title*."""
    start_cursor: Optional[str] = None
    while True:
        resp = (
            notion_client.blocks.children.list(block_id=block_id, start_cursor=start_cursor)
            if start_cursor
            else notion_client.blocks.children.list(block_id=block_id)
        )

        for blk in resp.get("results", []):
            blk_type = blk.get("type")
            if blk_type == "child_page" and blk.get("child_page", {}).get("title") == title:
                return blk["id"]

            if blk.get("has_children"):
                found = _find_child_page_id_recursive(notion_client, blk["id"], title)
                if found:
                    return found

        start_cursor = resp.get("next_cursor")
        if not start_cursor:
            break
    return None


# ---------------------------------------------------------------------------
# Playwright driven duplication helpers
# ---------------------------------------------------------------------------

def duplicate_current_page(page: Page, new_title: str | None = None) -> None:
    """Duplicate the *currently open* Notion page and optionally rename it."""
    try:
        log("Opening page menu…")
        page.wait_for_selector(PAGE_MENU_BUTTON_SELECTOR, state="visible", timeout=20_000)
        page.click(PAGE_MENU_BUTTON_SELECTOR)

        log("Clicking Duplicate…")
        page.wait_for_selector(DUPLICATE_MENU_ITEM_SELECTOR, timeout=15_000)
        page.click(DUPLICATE_MENU_ITEM_SELECTOR)

        original_url = page.url
        duplicated_url: str | None = None

        log("Waiting for duplicated page to load (up to 60 s)…")
        try:
            page.wait_for_url(lambda url: url != original_url, timeout=60_000)
            duplicated_url = page.url
            log(f"✅ Duplicated page loaded at {duplicated_url}")
        except PlaywrightTimeoutError:
            log("❌ Timed out waiting for the duplicated page. Please check manually.")
            page.pause()

        if new_title and duplicated_url:
            try:
                page_id = _extract_page_id_from_url(duplicated_url)
                _rename_page_via_api(page_id, new_title)
            except Exception as exc:
                log(f"⚠️  Skipped renaming due to error: {exc}")
    except PlaywrightTimeoutError:
        log("❌ Failed to duplicate. Ensure the page is fully loaded, duplicate manually if needed.")
        page.pause()


# ---------------------------------------------------------------------------
# High-level workflow
# ---------------------------------------------------------------------------

def duplicate_child_page(
    parent_url: str,
    source_title: str,
    target_title: str,
    *,
    headless: bool = False,
) -> None:
    """Duplicate *source_title* under *parent_url* and rename to *target_title*."""

    token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
    if not token:
        raise EnvironmentError("NOTION_API_KEY or NOTION_TOKEN must be set to use duplicate_child_page().")

    try:
        from notion_client import Client
    except ImportError as exc:
        raise RuntimeError("notion-client library is required but not installed") from exc

    notion = Client(auth=token)

    parent_id = _extract_page_id_from_url(parent_url)
    src_page_id = _find_child_page_id_recursive(notion, parent_id, source_title)
    if not src_page_id:
        raise ValueError(f"Could not locate a child page titled '{source_title}' under the parent page.")

    src_page_info = notion.pages.retrieve(page_id=src_page_id)
    src_page_url = src_page_info.get("url") or f"https://www.notion.so/{src_page_id.replace('-', '')}"

    log(f"Source page found: {src_page_url} (ID: {src_page_id})")

    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=headless)
        state_file = Path("notion_state.json")
        context = browser.new_context(storage_state=str(state_file) if state_file.exists() else None)
        page = context.new_page()

        log("Navigating to source page…")
        page.goto(src_page_url, wait_until="load")

        if "notion.so/login" in page.url:
            log("Login required – please sign in manually, then press ▶ resume to continue…")
            page.pause()

        context.storage_state(path=str(state_file))

        duplicate_current_page(page, target_title)

        log("Workflow complete – browser may be closed.")
        context.storage_state(path=str(state_file)) 