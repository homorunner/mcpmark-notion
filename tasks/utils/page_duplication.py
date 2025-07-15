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
from typing import Final, Optional, Tuple

from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
    Browser,
    Page,
)

# ---------------------------------------------------------------------------
# Configurable selectors (update here if Notion UI changes)
# ---------------------------------------------------------------------------
PAGE_MENU_BUTTON_SELECTOR: Final[str] = '[data-testid="more-button"], div.notion-topbar-more-button, [aria-label="More"], button[aria-label="More"]'
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
            print(blk_type)
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

def duplicate_current_page(
    page: Page,
    new_title: str | None = None,
    *,
    wait_timeout: int = 120_000,
) -> str:
    """Duplicate the *currently open* Notion page and optionally rename it.

    Parameters
    ----------
    page : playwright.sync_api.Page
        The page object pointing to the Notion page that should be duplicated – **must already be loaded**.
    new_title : str | None, optional
        If provided, the newly-created duplicate will be renamed via the Notion API.
    wait_timeout : int, default 120_000
        Maximum time (in **milliseconds**) to wait for the browser to navigate to the duplicated page.

    Returns
    -------
    str
        The page ID of the duplicated page.

    Raises
    ------
    RuntimeError
        If the duplication fails or the page ID cannot be determined within the timeout.
    """
    try:
        log("Opening page menu…")
        page.wait_for_selector(PAGE_MENU_BUTTON_SELECTOR, state="visible", timeout=20_000)
        page.click(PAGE_MENU_BUTTON_SELECTOR)

        log("Clicking Duplicate…")
        page.wait_for_selector(DUPLICATE_MENU_ITEM_SELECTOR, timeout=15_000)
        page.click(DUPLICATE_MENU_ITEM_SELECTOR)

        original_url = page.url
        duplicated_url: str | None = None
        duplicated_page_id: str | None = None

        log("Waiting for duplicated page to load (up to %.1f s)…" % (wait_timeout / 1000))
        try:
            page.wait_for_url(lambda url: url != original_url, timeout=wait_timeout)
            duplicated_url = page.url
            log(f"✅ Duplicated page loaded at {duplicated_url}")
            try:
                duplicated_page_id = _extract_page_id_from_url(duplicated_url)
            except Exception:
                duplicated_page_id = None
        except PlaywrightTimeoutError:
            # Even if Playwright timed out, the duplication might still have succeeded but the navigation was slow.
            # Attempt to parse the current URL anyway – if it changed we can still continue without interactive pause.
            duplicated_url = page.url
            if duplicated_url != original_url:
                log("⚠️  Navigation timeout – attempting to parse page ID from current URL anyway…")
                try:
                    duplicated_page_id = _extract_page_id_from_url(duplicated_url)
                except Exception as exc:
                    log(f"❌ Failed to parse page ID after timeout: {exc}")
                    duplicated_page_id = None
            else:
                log("❌ Timed out waiting for the duplicated page and URL has not changed. Please check manually.")
                if not page.context.browser.is_connected():
                    # Defensive: if browser is already closed no interactive pause possible
                    raise RuntimeError("Timed out waiting for duplicated page – URL did not change, duplication likely failed.")
                page.pause()

        if new_title and duplicated_page_id:
            try:
                _rename_page_via_api(duplicated_page_id, new_title)
            except Exception as exc:
                log(f"⚠️  Skipped renaming due to error: {exc}")

        if duplicated_page_id is None:
            raise RuntimeError("Failed to duplicate current Notion page – no page ID could be determined.")

        return duplicated_page_id
    except PlaywrightTimeoutError as exc:
        log(
            "❌ Playwright timed out while duplicating page. Ensure the page is fully loaded and try again."
        )
        if page.context.browser.is_connected():
            page.pause()
        raise RuntimeError("Playwright timeout during duplication") from exc


# ---------------------------------------------------------------------------
# High-level workflow
# ---------------------------------------------------------------------------

def duplicate_child_page(
    parent_url: str,
    source_title: str,
    target_title: str,
    *,
    headless: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Duplicate *source_title* under *parent_url* and rename to *target_title*.

    Returns
    -------
    Tuple[bool, Optional[str]]
        A tuple ``(success, page_id)`` where ``success`` is ``True`` if the page was duplicated
        successfully, and ``page_id`` is the ID of the duplicated page (``None`` if unsuccessful).
    """

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

    duplicated_page_id: Optional[str] = None  # Initialize for scope safety

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

        duplicated_page_id = duplicate_current_page(page, target_title)

        log("Workflow complete – browser may be closed.")
        context.storage_state(path=str(state_file))

    success = duplicated_page_id is not None
    return success, duplicated_page_id