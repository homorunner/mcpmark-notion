#!/usr/bin/env python3
"""
Notion State Manager for MCPBench
=================================

This module handles the duplication and management of Notion templates
(pages and databases) for consistent task evaluation using Playwright automation.
"""
import os
from pathlib import Path
from typing import Optional, Tuple

from notion_client import Client
from playwright.sync_api import (
    Browser,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from src.base.state_manager import BaseStateManager
from src.logger import get_logger
from src.mcp_services.notion.notion_task_manager import NotionTask

# Initialize logger
logger = get_logger(__name__)

# Selectors for Notion UI elements
PAGE_MENU_BUTTON_SELECTOR = '[data-testid="more-button"], div.notion-topbar-more-button, [aria-label="More"], button[aria-label="More"]'
DUPLICATE_MENU_ITEM_SELECTOR = 'text="Duplicate"'
DUPLICATE_WITH_CONTENT_SELECTOR = 'text="Duplicate with content"'


class NotionStateManager(BaseStateManager):
    """
    Manages the state of Notion templates using Playwright and the Notion API.
    """

    def __init__(
        self,
        notion_key: str,
        model_name: str,
        headless: bool = True,
        browser: str = "firefox",
    ):
        """
        Initializes the Notion state manager.

        Args:
            notion_key: The Notion API key.
            model_name: The name of the model being evaluated, used for naming templates.
            headless: Whether to run Playwright in headless mode.
            browser: The browser engine to use ('chromium' or 'firefox').
        """
        super().__init__()
        supported_browsers = {"chromium", "firefox"}
        if browser not in supported_browsers:
            raise ValueError(
                f"Unsupported browser '{browser}'. Supported browsers are: {', '.join(supported_browsers)}"
            )

        self.browser_name = browser
        self.notion_client = Client(auth=notion_key)
        self.headless = headless
        self.state_file = Path("notion_state.json")
        self.model_name = model_name

    def initialize(self, **kwargs):
        """Initializes the state manager (handled in __init__ for this implementation)."""
        pass

    def clean_up(self, task: NotionTask) -> bool:
        """
        Archives the duplicated Notion template to clean up the workspace.
        """
        template_id = task.duplicated_template_id
        if not template_id:
            logger.warning("No duplicated template ID found for task %s, skipping cleanup.", task.name)
            return False

        try:
            # Attempt to archive as a page first, then as a database
            self.notion_client.pages.update(page_id=template_id, archived=True)
            logger.info("Archived page template: %s", template_id)
            return True
        except Exception:
            try:
                self.notion_client.databases.update(
                    database_id=template_id, archived=True
                )
                logger.info("Archived database template: %s", template_id)
                return True
            except Exception as e:
                logger.error("Failed to archive template %s: %s", template_id, e)
                return False

    def set_up(self, task: NotionTask) -> bool:
        """
        Sets up the state for a task by duplicating the relevant Notion template.
        """
        template_title = self._category_to_template_title(task.category)
        template_info = self._find_template_by_title(template_title)

        if not template_info:
            logger.error("Template not found for category '%s' (title: '%s')", task.category, template_title)
            return False

        _, template_url = template_info
        task.original_template_url = template_url

        try:
            duplicated_url, duplicated_id = self._duplicate_template_for_task(
                template_url, task.category, task.name
            )
            task.duplicated_template_url = duplicated_url
            task.duplicated_template_id = duplicated_id
            return True
        except Exception as e:
            logger.error("Failed to duplicate template for %s: %s", task.name, e)
            return False

    def _rename_template_via_api(
        self, template_id: str, new_title: str, template_type: str
    ) -> None:
        """Renames a Notion page or database using the API."""
        try:
            if template_type == "page":
                self.notion_client.pages.update(
                    page_id=template_id,
                    properties={"title": {"title": [{"text": {"content": new_title}}]}},
                )
            else:
                self.notion_client.databases.update(
                    database_id=template_id, title=[{"text": {"content": new_title}}]
                )
        except Exception as e:
            logger.error("Failed to rename %s via API: %s", template_type, e)

    def _category_to_template_title(self, category: str) -> str:
        """Converts a category name to a capitalized template title."""
        return " ".join(word.capitalize() for word in category.split("_"))

    def _extract_template_id_from_url(self, url: str) -> str:
        """Extracts the template ID from a Notion URL."""
        slug = url.split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
        compact = "".join(c for c in slug if c.isalnum())
        if len(compact) < 32:
            raise ValueError(f"Could not parse template ID from URL: {url}")
        compact = compact[-32:]
        return f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:]}"

    def _find_template_by_title(self, title: str) -> Optional[Tuple[str, str]]:
        """Finds a Notion page or database by its exact title."""
        try:
            # Search for pages first
            response = self.notion_client.search(query=title, filter={"property": "object", "value": "page"})
            for result in response.get("results", []):
                props = result.get("properties", {})
                title_prop = props.get("title", {}).get("title") or props.get("Name", {}).get("title")
                if title_prop and "".join(t.get("plain_text", "") for t in title_prop).strip() == title:
                    return result.get("id"), result.get("url")

            # Then search for databases
            response = self.notion_client.search(query=title, filter={"property": "object", "value": "database"})
            for result in response.get("results", []):
                title_prop = result.get("title", [])
                if title_prop and "".join(t.get("plain_text", "") for t in title_prop).strip() == title:
                    return result.get("id"), result.get("url")
        except Exception as e:
            logger.error("Error searching for template '%s': %s", title, e)
        return None

    def _detect_template_type(self, template_id: str) -> str:
        """Detects whether a template is a page or a database."""
        try:
            self.notion_client.databases.retrieve(database_id=template_id)
            return "database"
        except Exception:
            return "page"

    def _duplicate_current_template(
        self,
        page: Page,
        new_title: Optional[str] = None,
        *,
        template_type: str = "page",
        wait_timeout: int = 180_000,
    ) -> str:
        """Duplicates the currently open Notion template using Playwright."""
        try:
            logger.info("- Opening page menu...")
            page.wait_for_selector(PAGE_MENU_BUTTON_SELECTOR, state="visible", timeout=30_000)
            page.click(PAGE_MENU_BUTTON_SELECTOR)

            logger.info("- Clicking 'Duplicate'...")
            page.hover(DUPLICATE_MENU_ITEM_SELECTOR)
            page.click(DUPLICATE_MENU_ITEM_SELECTOR)

            if template_type == "database":
                logger.info("- Selecting 'Duplicate with content' for the database...")
                page.wait_for_selector(DUPLICATE_WITH_CONTENT_SELECTOR, timeout=30_000)
                page.click(DUPLICATE_WITH_CONTENT_SELECTOR)

            original_url = page.url
            logger.info("- Waiting for duplicated template to load (up to %.1f s)...", wait_timeout / 1000)
            page.wait_for_url(lambda url: url != original_url, timeout=wait_timeout)
            
            duplicated_url = page.url
            duplicated_template_id = self._extract_template_id_from_url(duplicated_url)

            if new_title:
                self._rename_template_via_api(duplicated_template_id, new_title, template_type)

            return duplicated_template_id
        except PlaywrightTimeoutError as e:
            logger.error("Playwright timed out while duplicating template.")
            raise RuntimeError("Playwright timeout during duplication") from e

    def _duplicate_template_for_task(
        self,
        template_url: str,
        category: str,
        task_name: str,
        *,
        max_retries: int = 2,
        initial_wait_ms: int = 180_000,
    ) -> Tuple[str, str]:
        """Duplicates a template for a task, with retries for reliability."""
        if not self.state_file.exists():
            raise FileNotFoundError(
                "Authentication state 'notion_state.json' not found. "
                "Run the Notion login helper first."
            )

        last_exc = None
        for attempt in range(max_retries + 1):
            wait_timeout = initial_wait_ms * (attempt + 1)
            try:
                with sync_playwright() as p:
                    browser_type = getattr(p, self.browser_name)
                    browser: Browser = browser_type.launch(headless=self.headless)
                    context = browser.new_context(storage_state=str(self.state_file))
                    page = context.new_page()

                    logger.info("- Navigating to template for %s...", category)
                    page.goto(template_url, wait_until="load")
                    context.storage_state(path=str(self.state_file))

                    duplicate_title = f"[EVAL IN PROGRESS - {self.model_name.upper()}] {task_name}"
                    template_id = self._extract_template_id_from_url(template_url)
                    template_type = self._detect_template_type(template_id)

                    duplicated_id = self._duplicate_current_template(
                        page,
                        duplicate_title,
                        template_type=template_type,
                        wait_timeout=wait_timeout,
                    )
                    duplicated_url = page.url
                    logger.info("✓ Template duplicated successfully on attempt %d:", attempt + 1)
                    logger.info("  → Page URL: %s", duplicated_url)
                    logger.info("  → Renamed to: %s", duplicate_title)
                    context.storage_state(path=str(self.state_file))
                    return duplicated_url, duplicated_id
            except Exception as e:
                last_exc = e
                if attempt < max_retries:
                    logger.warning("⚠️ Duplication attempt %d failed: %s. Retrying...", attempt + 1, e)
        
        raise RuntimeError(
            f"Template duplication failed for task '{task_name}' after {max_retries + 1} attempts: {last_exc}"
        )
