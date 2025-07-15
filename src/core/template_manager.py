#!/usr/bin/env python3
"""
Template Duplication Manager for MCPBench
========================================

This module handles duplication of Notion templates (pages/databases) for 
consistent task evaluation using Playwright automation.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
from notion_client import Client
from core.task_manager import Task
from playwright.sync_api import sync_playwright, Browser, Page as PlaywrightPage
import logging

# Add project root to path for tasks import
sys.path.append(str(Path(__file__).parent.parent.parent))
from tasks.utils.page_duplication import duplicate_current_template, log

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages duplication of Notion templates using Playwright."""
    
    def __init__(self, notion_key: str, model_name: str, headless: bool = True, browser: str = "firefox"):
        """Initialize a new ``TemplateManager`` instance.

        Args:
            notion_key: Notion API key.
            headless: Whether Playwright should run in headless mode.
            browser: The underlying browser engine to use (``"chromium"`` or ``"firefox"``).
                Defaults to ``"firefox"`` to match the default used by the ``notion_login`` helper.
        """

        supported_browsers = {"chromium", "firefox"}
        if browser not in supported_browsers:
            raise ValueError(
                f"Unsupported browser '{browser}'. Supported browsers are: {', '.join(supported_browsers)}"
            )

        self.browser_name = browser
        self.notion_key = notion_key
        self.notion_client = Client(auth=notion_key)
        self.headless = headless
        self.state_file = Path("notion_state.json")
        self.model_name = model_name
        
    def _category_to_template_title(self, category: str) -> str:
        """Convert task category to template title format.
        
        Args:
            category: Task category (e.g., 'online_resume', 'habit_tracker')
            
        Returns:
            Template title (e.g., 'Online Resume', 'Habit Tracker')
        """
        return ' '.join(word.capitalize() for word in category.split('_'))
    
    def _extract_template_id_from_url(self, url: str) -> str:
        """Extract the template ID from a Notion URL.
        
        Args:
            url: Notion template URL
            
        Returns:
            Page ID in UUID format
        """
        # Remove query parameters and fragments
        url = url.split("?")[0].split("#")[0]
        
        # Extract the last part of the URL
        slug = url.rstrip("/").split("/")[-1]
        
        # Remove non-alphanumeric characters
        compact = "".join(c for c in slug if c.isalnum())
        
        # Validate length
        if len(compact) < 32:
            raise ValueError(f"Could not parse template ID from URL: {url}")
        
        # Take last 32 characters
        compact = compact[-32:]
        
        # Format as UUID
        return f"{compact[0:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:]}"
    
    def find_template_by_title(self, title: str) -> Optional[Tuple[str, str]]:
        """Find a template (page or database) by title using Notion API.
        
        Args:
            title: Template title to search for
            
        Returns:
            Tuple of (template_id, template_url) if found, None otherwise
        """
        try:
            # Search for pages with the title
            response = self.notion_client.search(
                query=title,
                filter={
                    "property": "object",
                    "value": "page"
                }
            )
            
            for result in response.get("results", []):
                page_title = None
                
                # Extract title from properties
                if "properties" in result:
                    if "title" in result["properties"]:
                        title_prop = result["properties"]["title"]
                        if title_prop.get("title"):
                            page_title = "".join(
                                t["plain_text"] for t in title_prop["title"]
                            )
                    elif "Name" in result["properties"]:
                        name_prop = result["properties"]["Name"]
                        if name_prop.get("title"):
                            page_title = "".join(
                                t["plain_text"] for t in name_prop["title"]
                            )
                
                if page_title and page_title.strip() == title:
                    return result["id"], result.get("url", "")
            
            # If not found as page, search for databases
            response = self.notion_client.search(
                query=title,
                filter={
                    "property": "object",
                    "value": "database"
                }
            )
            
            for result in response.get("results", []):
                db_title = None
                
                # Extract title from database
                if "title" in result:
                    db_title = "".join(
                        t["plain_text"] for t in result["title"]
                    )
                
                if db_title and db_title.strip() == title:
                    return result["id"], result.get("url", "")
                    
        except Exception as e:
            logger.error(f"Error searching for template '{title}': {e}")
            
        return None
    
    def duplicate_template_for_task(
        self,
        template_url: str,
        category: str,
        task_name: str,
        *,
        max_retries: int = 2,
        initial_wait_ms: int = 180_000,
    ) -> Tuple[str, str]:
        """Duplicate a template for a specific task using Playwright.
        
        Args:
            template_url: URL of the template to duplicate
            category: Task category
            task_name: Name of the task (for the duplicated template title)
            
        Returns:
            Tuple of (duplicated_url, duplicated_id)
        """
        # ------------------------------------------------------------------
        # Ensure authentication state is present *before* launching Playwright
        # ------------------------------------------------------------------
        if not self.state_file.exists():
            raise FileNotFoundError(
                "Authentication state 'notion_state.json' not found. "
                "Run 'python notion_login.py' (or the Notion login helper) before executing the pipeline."
            )

        attempt = 0
        last_exc: Optional[Exception] = None

        while attempt <= max_retries:
            wait_timeout = initial_wait_ms * (attempt + 1)

            try:
                with sync_playwright() as p:
                    # Dynamically select the requested browser engine for each attempt
                    browser_type = getattr(p, self.browser_name)
                    browser: Browser = browser_type.launch(headless=self.headless)

                    # Use saved state if available
                    context = browser.new_context(
                        storage_state=str(self.state_file) if self.state_file.exists() else None
                    )
                    page = context.new_page()

                    # Set the Notion API key in environment for the duplication helper
                    if self.notion_key:
                        os.environ["NOTION_API_KEY"] = self.notion_key

                    log(f"[{attempt+1}/{max_retries+1}] Navigating to template for {category}…")
                    page.goto(template_url, wait_until="load")

                    # Save authentication state
                    context.storage_state(path=str(self.state_file))

                    duplicate_title = f"[EVAL IN PROGRESS - {self.model_name.upper()}] {task_name}"

                    # Determine template type (page vs database) *before* duplication
                    template_id = self._extract_template_id_from_url(template_url)
                    template_type = self._detect_template_type(template_id)

                    duplicated_id = duplicate_current_template(
                        page,
                        duplicate_title,
                        wait_timeout=wait_timeout,
                        template_type=template_type,
                    )

                    duplicated_url = page.url

                    log(
                        f"✅ Template duplicated successfully on attempt {attempt+1}: {duplicated_id}"
                    )

                    # Save state again for future use
                    context.storage_state(path=str(self.state_file))

                    return duplicated_url, duplicated_id

            except Exception as exc:
                last_exc = exc
                attempt += 1
                if attempt > max_retries:
                    break
                log(
                    f"⚠️  Duplication attempt {attempt}/{max_retries+1} failed: {exc}. "
                    f"Retrying with timeout {initial_wait_ms * (attempt + 1)/1000:.1f}s…"
                )

            finally:
                # Ensure browser is closed if opened inside with-block; the context manager handles it.
                pass

        # If we reach here all attempts failed
        raise RuntimeError(
            f"Template duplication failed for task '{task_name}' in category '{category}' after {max_retries + 1} attempts: {last_exc}"
        )
    
    def delete_template(self, template_id: str) -> bool:
        """Delete (archive) a template.
        
        Args:
            template_id: ID of the template to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try as page first
            self.notion_client.pages.update(
                page_id=template_id,
                archived=True
            )
            log(f"✅ Template {template_id} archived successfully")
            return True
        except:
            try:
                # Try as database
                self.notion_client.databases.update(
                    database_id=template_id,
                    archived=True
                )
                log(f"✅ Template {template_id} archived successfully")
                return True
            except Exception as e:
                log(f"❌ Failed to archive template {template_id}: {e}")
                return False
    
    def process_task_templates(self, task: Task) -> bool:
        """Duplicate and attach a Notion template for *one* task.

        This helper **mutates** the provided ``task`` object, setting
        ``original_template_url``, ``duplicated_template_url`` and
        ``duplicated_template_id`` in-place.

        It consolidates the former bulk logic (which operated on a list of
        tasks) into a *single-task* workflow because the caller now invokes
        this method inside a per-task loop.

        Args:
            task: The task to prepare a template for.

        Returns:
            ``True`` when the template was duplicated successfully, ``False``
            otherwise (e.g. template not found or duplication failed after all
            retries).
        """

        category = task.category

        # ------------------------------------------------------------------
        # Locate the *source* template for this category
        # ------------------------------------------------------------------
        template_title = self._category_to_template_title(category)
        template_info = self.find_template_by_title(template_title)

        if not template_info:
            logger.warning(
                f"Template not found for category '{category}' (title: '{template_title}')"
            )
            task.original_template_url = None
            task.duplicated_template_url = None
            task.duplicated_template_id = None
            return False

        _, template_url = template_info

        # ------------------------------------------------------------------
        # Attempt duplication (with built-in retry handled by the helper)
        # ------------------------------------------------------------------
        try:
            duplicated_url, duplicated_id = self.duplicate_template_for_task(
                template_url, category, task.name
            )

            task.original_template_url = template_url
            task.duplicated_template_url = duplicated_url
            task.duplicated_template_id = duplicated_id

            return True  # Success ✅

        except Exception as e:
            # duplicate_template_for_task already performed retries – treat any
            # raised exception as a definitive failure.
            logger.error(f"Failed to duplicate template for {task.name}: {e}")

            task.original_template_url = template_url
            task.duplicated_template_url = None
            task.duplicated_template_id = None

            return False  # Failure ❌

# ------------------------------------------------------------------
# Helper: detect whether a Notion object ID is a page or a database
# ------------------------------------------------------------------

    def _detect_template_type(self, template_id: str) -> str:
        """Return "database" if *template_id* refers to a database, else "page"."""

        # 1) Fast path: use the generic blocks endpoint (works for both)
        try:
            blk = self.notion_client.blocks.retrieve(block_id=template_id)
            blk_type = blk.get("type")
            if blk_type == "child_database":
                return "database"
            if blk_type == "page":
                return "page"
        except Exception:
            # Ignore and fall back
            pass

        # 2) Fallback: explicit database retrieval
        try:
            self.notion_client.databases.retrieve(database_id=template_id)
            return "database"
        except Exception:
            return "page"