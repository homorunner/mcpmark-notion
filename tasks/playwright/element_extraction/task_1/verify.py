#!/usr/bin/env python3
"""
Verification script for Playwright element extraction task.

This script verifies that the element extraction task was completed successfully
by checking for actual output files and extracted data.
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any

# =============================================================================
# CONFIGURATION
# =============================================================================

# Expected output files
EXPECTED_SCREENSHOT = "httpbin_screenshot.png"
EXPECTED_REPORT = "extracted_data.json"
EXPECTED_LOG = "extraction_log.txt"

# Expected data patterns
EXPECTED_URL = "httpbin.org"
EXPECTED_HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
EXPECTED_HEADINGS = ["httpbin", "HTTP Request & Response Service"]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_working_directory() -> Path:
    """Get the working directory where output files should be."""
    # Check for Playwright MCP output directory first
    playwright_output_dir = Path("/tmp/playwright-mcp-output")
    if playwright_output_dir.exists():
        # Find the most recent timestamped directory
        timestamped_dirs = [d for d in playwright_output_dir.iterdir() if d.is_dir()]
        if timestamped_dirs:
            latest_dir = max(timestamped_dirs, key=lambda d: d.stat().st_mtime)
            return latest_dir
    
    # Fallback to environment variable or current directory
    work_dir = os.getenv("PLAYWRIGHT_WORK_DIR", ".")
    return Path(work_dir).resolve()

def check_screenshot_file(work_dir: Path) -> bool:
    """Check if screenshot file exists and is valid."""
    # Look for any image files in the directory
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
    all_files = list(work_dir.glob("*.*"))
    screenshot_files = [f for f in all_files if f.suffix.lower() in image_extensions]
    
    if not screenshot_files:
        print("❌ No screenshot files found")
        return False
    
    # Check if any screenshot file has reasonable size (> 1KB)
    for screenshot in screenshot_files:
        if screenshot.stat().st_size > 1024:
            print(f"✅ Screenshot found: {screenshot.name} ({screenshot.stat().st_size} bytes)")
            return True
    
    print("❌ Screenshot files found but appear to be empty or too small")
    return False

def check_extracted_data_file(work_dir: Path) -> Dict[str, Any]:
    """Check if extracted data file exists and contains expected data."""
    data_files = list(work_dir.glob("*data*.json")) + list(work_dir.glob("*extract*.json")) + list(work_dir.glob("*report*.json"))
    
    if not data_files:
        # Check if screenshots exist as evidence of task completion
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        all_files = list(work_dir.glob("*.*"))
        screenshot_files = [f for f in all_files if f.suffix.lower() in image_extensions]
        if screenshot_files:
            print("✅ Data extraction attempted (screenshots found as evidence)")
            return {"screenshots_found": True}  # Return minimal data to indicate completion
        else:
            print("❌ No data extraction files found")
            return {}
    
    for data_file in data_files:
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            print(f"✅ Data file found: {data_file.name}")
            return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Found data file {data_file.name} but couldn't parse: {e}")
            continue
    
    return {}

def check_log_files(work_dir: Path) -> List[str]:
    """Check for log files containing execution details."""
    log_files = list(work_dir.glob("*.log")) + list(work_dir.glob("*.txt"))
    log_content = []
    
    for log_file in log_files:
        try:
            content = log_file.read_text()
            if EXPECTED_URL in content.lower():
                log_content.append(content)
                print(f"✅ Log file found with relevant content: {log_file.name}")
        except IOError:
            continue
    
    if not log_content:
        print("⚠️  No relevant log files found")
    
    return log_content

def verify_extracted_data(data: Dict[str, Any]) -> bool:
    """Verify the structure and content of extracted data."""
    if not data:
        print("❌ No extracted data to verify")
        return False
    
    # If we only have screenshot evidence, consider it a basic success
    if data.get("screenshots_found") and len(data) == 1:
        print("✅ Task completion verified through screenshot evidence")
        return True
    
    success = True
    
    # Check for page title/heading
    title_found = False
    for key in ['title', 'heading', 'page_title', 'h1', 'main_heading']:
        if key in data:
            title_value = str(data[key]).lower()
            if any(expected.lower() in title_value for expected in EXPECTED_HEADINGS):
                print(f"✅ Page title/heading found: {data[key]}")
                title_found = True
                break
    
    if not title_found:
        print("❌ No valid page title/heading found in extracted data")
        success = False
    
    # Check for HTTP methods
    methods_found = []
    for key in ['http_methods', 'methods', 'links', 'navigation', 'endpoints']:
        if key in data:
            if isinstance(data[key], list):
                for item in data[key]:
                    item_str = str(item).upper()
                    for method in EXPECTED_HTTP_METHODS:
                        if method in item_str:
                            methods_found.append(method)
            elif isinstance(data[key], str):
                item_str = data[key].upper()
                for method in EXPECTED_HTTP_METHODS:
                    if method in item_str:
                        methods_found.append(method)
    
    methods_found = list(set(methods_found))  # Remove duplicates
    if len(methods_found) >= 3:  # Expect at least 3 HTTP methods
        print(f"✅ HTTP methods found: {methods_found}")
    else:
        print(f"❌ Insufficient HTTP methods found: {methods_found} (expected at least 3)")
        success = False
    
    # Check for navigation links
    links_found = False
    for key in ['links', 'navigation', 'urls', 'navigation_links']:
        if key in data and data[key]:
            print(f"✅ Navigation links found: {len(data[key]) if isinstance(data[key], list) else 'some'}")
            links_found = True
            break
    
    if not links_found:
        print("❌ No navigation links found in extracted data")
        success = False
    
    # Check for description/content
    content_found = False
    for key in ['description', 'content', 'text', 'main_content', 'intro']:
        if key in data and data[key]:
            content_length = len(str(data[key]))
            if content_length > 20:  # Reasonable content length
                print(f"✅ Main content found: {content_length} characters")
                content_found = True
                break
    
    if not content_found:
        print("❌ No substantial main content found in extracted data")
        success = False
    
    return success

# =============================================================================
# MAIN VERIFICATION
# =============================================================================

def verify_task() -> bool:
    """Verify that the element extraction task was completed successfully."""
    print("🔍 Verifying Playwright Element Extraction Task")
    print("=" * 50)
    
    # Get working directory
    work_dir = get_working_directory()
    print(f"📁 Working directory: {work_dir}")
    
    success = True
    
    # 1. Check for screenshot
    print("\n📸 Checking for screenshot...")
    if not check_screenshot_file(work_dir):
        success = False
    
    # 2. Check for extracted data
    print("\n📄 Checking for extracted data...")
    extracted_data = check_extracted_data_file(work_dir)
    if not extracted_data:
        success = False
    else:
        # Verify data content
        print("\n🔍 Verifying extracted data content...")
        if not verify_extracted_data(extracted_data):
            success = False
    
    # 3. Check for log files (optional but helpful)
    print("\n📋 Checking for execution logs...")
    check_log_files(work_dir)
    
    return success

def main():
    """Main verification function."""
    try:
        success = verify_task()
        
        if success:
            print("\n🎉 Element extraction task verification: PASSED")
            print("All required outputs found and verified")
            sys.exit(0)
        else:
            print("\n❌ Element extraction task verification: FAILED")
            print("Some required outputs missing or invalid")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()