"""page_duplication.py
Utility helpers for duplicating Notion templates (pages or databases) using
Playwright + Notion SDK.

Main entry point
----------------
• duplicate_current_template(page: playwright.sync_api.Page, new_title: str | None)
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
# When duplicating a *database*, Notion shows a submenu with two options. We
# want to pick "Duplicate with content" so that the evaluation template keeps
# all data/properties identical to the original. The selector below should be
# robust across light/dark themes because it matches the exact text label.
DUPLICATE_WITH_CONTENT_SELECTOR: Final[str] = 'text="Duplicate with content"'


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Lightweight console logger."""
    print(f"[NotionDup] {msg}")


# ---------------------------------------------------------------------------
# Notion-SDK helpers (no Playwright)
# ---------------------------------------------------------------------------

def _extract_template_id_from_url(url: str) -> str:
    """Extract canonical UUID template (page or database) ID from a Notion URL."""
    url = url.split("?")[0].split("#")[0]
    slug = url.rstrip("/").split("/")[-1]
    compact = "".join(c for c in slug if c.isalnum())
    if len(compact) < 32:
        raise ValueError(f"Could not parse template ID from URL: {url}")
    compact = compact[-32:]
    return f"{compact[0:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:]}"


def _rename_template_via_api(template_id: str, new_title: str, template_type: str) -> None:
    """Rename a Notion template (page *or* database) using the Notion SDK.

    This helper first attempts to rename the given ID as a *page*. If that
    fails (e.g. the ID refers to a database), it falls back to renaming it as
    a *database*.
    """
    token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
    if not token:
        log("⚠️  NOTION_API_KEY/NOTION_TOKEN not set – skipping rename.")
        return

    try:
        from notion_client import Client  # imported lazily to avoid heavy import at module load
    except ImportError:
        log("⚠️  notion-client library not available – skipping rename.")
        return

    client = Client(auth=token)

    try:
        if template_type == "page":
            client.pages.update(
                page_id=template_id,
                properties={
                    "title": {
                        "title": [
                            {"type": "text", "text": {"content": new_title}}
                        ]
                    }
                },
            )
        else:
            client.databases.update(
                database_id=template_id,
                title=[{"type": "text", "text": {"content": new_title}}],
            )
        log(f"✅ Renamed {template_type} to '{new_title}' via Notion API")
    except Exception as exc:
        log(f"❌ Failed to rename {template_type} via Notion API: {exc}")

# ---------------------------------------------------------------------------
# Backwards-compatibility aliases (prevent import errors in external code)
# ---------------------------------------------------------------------------

# (Backward-compatibility aliases removed – callers should migrate.)


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

def duplicate_current_template(
    page: Page,
    new_title: str | None = None,
    *,
    template_type: str = "page",  # "page" or "database"
    wait_timeout: int = 180_000,
) -> str:
    """Duplicate the *currently open* Notion template (page **or** database).

    Parameters
    ----------
    page : playwright.sync_api.Page
        The page object pointing to the Notion page that should be duplicated – **must already be loaded**.
    new_title : str | None, optional
        If provided, the newly-created duplicate will be renamed via the Notion API.
    wait_timeout : int, default 180_000
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
        page.wait_for_selector(PAGE_MENU_BUTTON_SELECTOR, state="visible", timeout=30_000)
        page.click(PAGE_MENU_BUTTON_SELECTOR)

        log("Clicking Duplicate…")
        page.wait_for_selector(DUPLICATE_MENU_ITEM_SELECTOR, timeout=30_000)
        # For databases, "Duplicate" first opens a submenu – hover is enough
        # to show it, then we need a 2nd click on "Duplicate with content".
        page.hover(DUPLICATE_MENU_ITEM_SELECTOR)
        page.click(DUPLICATE_MENU_ITEM_SELECTOR)

        if template_type == "database":
            log("Selecting 'Duplicate with content' for database…")
            page.wait_for_selector(DUPLICATE_WITH_CONTENT_SELECTOR, timeout=30_000)
            page.click(DUPLICATE_WITH_CONTENT_SELECTOR)

        original_url = page.url
        duplicated_url: str | None = None
        duplicated_template_id: str | None = None

        log("Waiting for duplicated template to load (up to %.1f s)…" % (wait_timeout / 1000))
        # Strict behaviour: if Playwright does not navigate to a different URL within
        # the timeout we consider the duplication failed and let the timeout propagate
        # so that caller-level retry logic can handle it. No fallback heuristics.
        page.wait_for_url(lambda url: url != original_url, timeout=wait_timeout)
        duplicated_url = page.url
        log(f"✅ Duplicated template loaded at {duplicated_url}")
        try:
            duplicated_template_id = _extract_template_id_from_url(duplicated_url)
        except Exception:
            duplicated_template_id = None

        if new_title and duplicated_template_id:
            try:
                _rename_template_via_api(duplicated_template_id, new_title, template_type)
            except Exception as exc:
                log(f"⚠️  Skipped renaming due to error: {exc}")

        if duplicated_template_id is None:
            raise RuntimeError("Failed to duplicate current Notion template – no template ID could be determined.")

        return duplicated_template_id
    except PlaywrightTimeoutError as exc:
        log(
            "❌ Playwright timed out while duplicating template. Ensure the template is fully loaded and try again."
        )
        if page.context.browser.is_connected():
            page.pause()
        raise RuntimeError("Playwright timeout during duplication") from exc


# ---------------------------------------------------------------------------
# Backwards-compatibility alias – remove in a future major release
# ---------------------------------------------------------------------------

# (Removed legacy alias duplicate_current_page)


# ---------------------------------------------------------------------------
# High-level workflow section removed (duplicate_child_page deprecated)
# ---------------------------------------------------------------------------