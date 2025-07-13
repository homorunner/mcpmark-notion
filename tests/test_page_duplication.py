#!/usr/bin/env python3
"""
Test Page Duplication Functionality
===================================

Tests for the page duplication manager and related functionality.
"""

import os
import sys
import time
from pathlib import Path

# Add src and tasks to path
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from tasks.utils.page_duplication import duplicate_current_page, log, _extract_page_id_from_url

def test_page_duplication_utilities():
    """Test page duplication utility functions."""
    print("🔍 Testing page duplication utilities...")
    
    # Get Notion API key from environment
    notion_key = os.getenv('NOTION_API_KEY')
    if not notion_key:
        print("❌ NOTION_API_KEY not found in environment")
        return False
    
    print("✅ NOTION_API_KEY found in environment")
    
    try:
        # Test URL parsing functionality
        test_urls = [
            "https://www.notion.so/Test-Page-12345678901234567890123456789012",
            "https://notion.so/workspace/Test-Page-abc123def456ghi789012345678901234?v=123",
            "https://www.notion.so/12345678901234567890123456789012"
        ]
        
        print("🔍 Testing page ID extraction...")
        for url in test_urls:
            try:
                page_id = _extract_page_id_from_url(url)
                print(f"✅ URL: {url[:50]}... → Page ID: {page_id}")
            except Exception as e:
                print(f"❌ Failed to parse URL {url[:50]}...: {e}")
        
        # Test log function
        print("🔍 Testing log function...")
        log("Test log message")
        print("✅ Log function works")
        
        print("ℹ️  Page duplication utilities are functional")
        print("ℹ️  Full duplication testing requires browser automation")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing page duplication utilities: {e}")
        return False

def test_task_template_manager():
    """Test task template manager functionality."""
    print("\n🔍 Testing task template manager...")
    
    try:
        from core.task_template_manager import TaskTemplateManager
        
        template_manager = TaskTemplateManager()
        print("✅ TaskTemplateManager initialized successfully")
        
        # Test template replacement functionality
        sample_description = """
# Task Description

Find page named "Maya Zhang" and perform the following actions:

1. Navigate to the Skills section
2. Add a new skill entry
3. Set the proficiency level

The page should be located by searching for "Maya Zhang".
"""
        
        test_page_id = "12345678-1234-5678-1234-567812345678"
        
        # Test the legacy description conversion
        modified_description = template_manager.convert_legacy_description(
            sample_description, test_page_id
        )
        
        print("✅ Legacy description conversion completed")
        
        # Verify the replacement worked
        if test_page_id in modified_description:
            print("✅ Page ID successfully inserted into description")
        else:
            print("❌ Page ID not found in modified description")
            return False
        
        # Test extracting page name
        page_name = template_manager.extract_page_name_from_description(sample_description)
        if page_name == "Maya Zhang":
            print("✅ Page name extraction works correctly")
        else:
            print(f"❌ Expected 'Maya Zhang', got '{page_name}'")
        
        # Test template functionality
        template = 'Use page with ID: {{PAGE_ID}}, then add skill "Python" with 80% proficiency.'
        templated_result = template_manager.inject_page_id(template, test_page_id)
        if test_page_id in templated_result:
            print("✅ Template injection works correctly")
        else:
            print("❌ Template injection failed")
        
        print("\n📄 Modified description preview:")
        print(modified_description[:200] + "..." if len(modified_description) > 200 else modified_description)
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing task template manager: {e}")
        return False

def test_environment_setup():
    """Test that required environment variables are set."""
    print("\n🔍 Testing environment setup...")
    
    required_vars = [
        'NOTION_API_KEY',
        'MCPBENCH_API_KEY', 
        'MCPBENCH_BASE_URL',
        'MCPBENCH_MODEL_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} is missing")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {missing_vars}")
        print("Make sure to set these before running the full pipeline")
        return False
    
    print("\n✅ All required environment variables are set")
    return True

if __name__ == "__main__":
    print("=== Page Duplication & Environment Tests ===\n")
    
    success1 = test_environment_setup()
    success2 = test_page_duplication_utilities()
    success3 = test_task_template_manager()
    
    if success1 and success2 and success3:
        print("\n🎉 Page duplication tests passed!")
    else:
        print("\n❌ Some page duplication tests failed!")
        sys.exit(1)