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
from typing import Dict, Tuple, Optional, List
from notion_client import Client
from core.task_manager import Task
from playwright.sync_api import sync_playwright, Browser, Page as PlaywrightPage
import logging

# Add project root to path for tasks import
sys.path.append(str(Path(__file__).parent.parent.parent))
from tasks.utils.page_duplication import duplicate_current_page, log

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages duplication of Notion templates using Playwright."""
    
    def __init__(self, notion_key: str, headless: bool = True):
        """Initialize with Notion API key.
        
        Args:
            notion_key: Notion API key
            headless: Whether to run browser in headless mode
        """
        self.notion_key = notion_key
        self.notion_client = Client(auth=notion_key)
        self.headless = headless
        self.state_file = Path("notion_state.json")
        
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
    
    def duplicate_template_for_task(self, template_url: str, category: str, task_name: str) -> Tuple[str, str]:
        """Duplicate a template for a specific task using Playwright.
        
        Args:
            template_url: URL of the template to duplicate
            category: Task category
            task_name: Name of the task (for the duplicated template title)
            
        Returns:
            Tuple of (duplicated_url, duplicated_id)
        """
        with sync_playwright() as p:
            browser: Browser = p.chromium.launch(headless=self.headless)
            
            # Use saved state if available
            context = browser.new_context(
                storage_state=str(self.state_file) if self.state_file.exists() else None
            )
            page = context.new_page()
            
            try:
                # Set the Notion API key in environment for the duplication helper
                if self.notion_key:
                    os.environ["NOTION_API_KEY"] = self.notion_key
                
                log(f"Navigating to template for {category}...")
                page.goto(template_url, wait_until="load")
                
                # Handle login if needed
                if "notion.so/login" in page.url:
                    if self.headless:
                        raise RuntimeError(
                            "Login required but running in headless mode. "
                            "Please run in non-headless mode first to save authentication."
                        )
                    log("Login required – please sign in manually, then press ▶ resume to continue...")
                    page.pause()
                
                # Save authentication state
                context.storage_state(path=str(self.state_file))
                
                # Duplicate the template with a specific title
                duplicate_title = f"[EVAL] {task_name} - Copy"
                duplicated_id = duplicate_current_page(page, duplicate_title)
                
                # Fallback: try to extract ID from URL if not returned
                if not duplicated_id:
                    try:
                        duplicated_id = self._extract_template_id_from_url(page.url)
                        log(f"ℹ️  Extracted ID from URL: {duplicated_id}")
                    except Exception:
                        duplicated_id = None
                
                if not duplicated_id:
                    raise RuntimeError("Failed to get duplicated template ID")
                
                duplicated_url = page.url
                
                log(f"✅ Template duplicated successfully: {duplicated_id}")
                
                # Save state again for future use
                context.storage_state(path=str(self.state_file))
                
                return duplicated_url, duplicated_id
                
            finally:
                browser.close()
    
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
    
    def process_task_templates(self, tasks: List[Task]) -> Dict[str, Dict[str, Optional[str]]]:
        """Process templates for a list of tasks.
        
        Args:
            tasks: List of Task objects
            
        Returns:
            Dictionary mapping task names to template info
        """
        results = {}
        
        # Step 1: Group tasks by category
        categories = {}
        for task in tasks:
            if task.category not in categories:
                categories[task.category] = []
            categories[task.category].append(task)
        
        # Step 3: Duplicate template for each task
        for category, category_tasks in categories.items():
            # Obtain meta info of template
            template_title = self._category_to_template_title(category)
            template_info = self.find_template_by_title(template_title)

            if not template_info:
                logger.warning(f"Template not found for category '{category}' (title: '{template_title}')")
                for task in category_tasks:
                    results[task.name] = {
                        "original_template_url": None,
                        "duplicated_template_url": None,
                        "duplicated_template_id": None
                    }
                continue
            
            _, template_url = template_info
            
            # Duplicate
            for task in category_tasks:
                try:
                    duplicated_url, duplicated_id = self.duplicate_template_for_task(
                        template_url, category, task.name
                    )
                    
                    results[task.name] = {
                        "original_template_url": template_url,
                        "duplicated_template_url": duplicated_url,
                        "duplicated_template_id": duplicated_id
                    }
                except Exception as e:
                    logger.error(f"Failed to duplicate template for {task.name}: {e}")
                    results[task.name] = {
                        "original_template_url": template_url,
                        "duplicated_template_url": None,
                        "duplicated_template_id": None
                    }
        
        return results