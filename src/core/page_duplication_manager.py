#!/usr/bin/env python3
"""
Page Duplication Manager for MCPBench Evaluation
===============================================

This module manages the lifecycle of page duplications for consistent evaluation,
ensuring each task runs on a fresh copy of the source page.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from notion_client import Client
from playwright.sync_api import sync_playwright, Browser, Page as PlaywrightPage

# Add project root to path for tasks import
sys.path.append(str(Path(__file__).parent.parent.parent))
from tasks.utils.page_duplication import duplicate_current_page, log


class PageDuplicationManager:
    """Manages page duplication lifecycle for evaluation tasks."""
    
    def __init__(self, notion_key: str, config: Dict[str, Any], headless: bool = True):
        """Initialize the page duplication manager.
        
        Args:
            notion_key: Notion API key
            config: Configuration containing source page URLs
            headless: Whether to run browser in headless mode
        """
        self.notion_key = notion_key
        self.notion_client = Client(auth=notion_key)
        self.config = config
        self.headless = headless
        self.state_file = Path("notion_state.json")
    
    def get_source_page_url(self, category: str) -> str:
        """Get the source page URL for a given task category.
        
        Args:
            category: Task category (e.g., 'online_resume')
            
        Returns:
            Source page URL
            
        Raises:
            ValueError: If category not found in config
        """
        source_pages = self.config.get("source_pages", {})
        if category not in source_pages:
            raise ValueError(f"Source page URL not configured for category: {category}")
        return source_pages[category]
    
    def extract_page_id_from_url(self, url: str) -> str:
        """Extract the page ID from a Notion URL.
        
        Args:
            url: Notion page URL
            
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
            raise ValueError(f"Could not parse page ID from URL: {url}")
        
        # Take last 32 characters
        compact = compact[-32:]
        
        # Format as UUID
        return f"{compact[0:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:]}"
    
    def duplicate_page_for_task(self, category: str, task_name: str) -> tuple[str, str]:
        """Duplicate the source page for a specific task.
        
        Args:
            category: Task category
            task_name: Name of the task (for the duplicated page title)
            
        Returns:
            Tuple of (duplicated_page_url, duplicated_page_id)
        """
        source_url = self.get_source_page_url(category)
        
        with sync_playwright() as p:
            browser: Browser = p.chromium.launch(headless=self.headless)
            
            # Use saved state if available
            context = browser.new_context(
                storage_state=str(self.state_file) if self.state_file.exists() else None
            )
            page = context.new_page()
            
            try:
                log(f"Navigating to source page for {category}...")
                page.goto(source_url, wait_until="load")
                
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
                
                # Store original URL before duplication
                original_url = page.url
                
                # Duplicate the page with a specific title
                duplicate_title = f"[EVAL] {task_name} - Copy"
                duplicate_current_page(page, duplicate_title)
                
                # Wait for URL to change and get the new URL
                page.wait_for_url(lambda url: url != original_url, timeout=60_000)
                duplicated_url = page.url
                
                # Extract page ID from the duplicated URL
                duplicated_page_id = self.extract_page_id_from_url(duplicated_url)
                
                log(f"✅ Page duplicated successfully: {duplicated_page_id}")
                
                # Save state again for future use
                context.storage_state(path=str(self.state_file))
                
                return duplicated_url, duplicated_page_id
                
            finally:
                browser.close()
    
    def delete_page(self, page_id: str) -> bool:
        """Delete a Notion page.
        
        Args:
            page_id: ID of the page to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Archive the page (Notion API doesn't support direct deletion)
            self.notion_client.pages.update(
                page_id=page_id,
                archived=True
            )
            log(f"✅ Page {page_id} archived successfully")
            return True
            
        except Exception as e:
            log(f"❌ Failed to archive page {page_id}: {e}")
            return False
    
    def verify_page_exists(self, page_id: str) -> bool:
        """Verify that a page exists and is accessible.
        
        Args:
            page_id: ID of the page to verify
            
        Returns:
            True if page exists and is accessible, False otherwise
        """
        try:
            page = self.notion_client.pages.retrieve(page_id=page_id)
            return not page.get("archived", False)
        except Exception:
            return False
    
    async def duplicate_page_async(self, category: str, task_name: str) -> tuple[str, str]:
        """Async wrapper for duplicate_page_for_task.
        
        Args:
            category: Task category
            task_name: Name of the task
            
        Returns:
            Tuple of (duplicated_page_url, duplicated_page_id)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.duplicate_page_for_task, 
            category, 
            task_name
        )
    
    async def delete_page_async(self, page_id: str) -> bool:
        """Async wrapper for delete_page.
        
        Args:
            page_id: ID of the page to delete
            
        Returns:
            True if successful, False otherwise
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.delete_page, page_id)


def main():
    """Example usage of PageDuplicationManager."""
    # Example configuration
    config = {
        "source_pages": {
            "online_resume": "https://www.notion.so/example-page-id",
            "japan_travel_planner": "https://www.notion.so/another-page-id"
        }
    }
    
    # Initialize manager
    notion_key = os.getenv("NOTION_API_KEY")
    if not notion_key:
        print("Error: NOTION_API_KEY not set")
        return
    
    manager = PageDuplicationManager(notion_key, config, headless=False)
    
    try:
        # Duplicate a page
        url, page_id = manager.duplicate_page_for_task("online_resume", "test_task_1")
        print(f"Duplicated page: {url}")
        print(f"Page ID: {page_id}")
        
        # Verify it exists
        exists = manager.verify_page_exists(page_id)
        print(f"Page exists: {exists}")
        
        # Clean up
        input("Press Enter to delete the duplicated page...")
        deleted = manager.delete_page(page_id)
        print(f"Page deleted: {deleted}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()