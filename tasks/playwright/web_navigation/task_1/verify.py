#!/usr/bin/env python3
"""
Verification script for Playwright web navigation task.

This script verifies that the web navigation task was completed successfully
by checking for screenshots, extracted content, and navigation evidence.
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

# Expected URLs
EXPECTED_HOMEPAGE_URL = "httpbin.org"
EXPECTED_GET_URL = "httpbin.org/get"

# Expected files
EXPECTED_HOMEPAGE_SCREENSHOT = "httpbin_homepage.png"
EXPECTED_GET_SCREENSHOT = "httpbin_get.png"
EXPECTED_TITLE_FILE = "page_title.txt"
EXPECTED_JSON_FILE = "get_response.json"

# Expected content patterns
EXPECTED_TITLE_PATTERNS = ["httpbin", "HTTP Request & Response Service"]
EXPECTED_JSON_FIELDS = ["origin", "url", "headers"]  # Common fields in /get response

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_working_directory() -> Path:
    """Get the working directory where output files should be."""
    work_dir = os.getenv("PLAYWRIGHT_WORK_DIR", ".")
    return Path(work_dir).resolve()

def check_screenshots(work_dir: Path) -> int:
    """Check for screenshot files and return count found."""
    screenshot_files = (
        list(work_dir.glob("*screenshot*.png")) +
        list(work_dir.glob("*httpbin*.png")) +
        list(work_dir.glob("*homepage*.png")) +
        list(work_dir.glob("*get*.png"))
    )
    
    valid_screenshots = 0
    for screenshot in screenshot_files:
        if screenshot.stat().st_size > 1024:  # At least 1KB
            print(f"✅ Screenshot found: {screenshot.name} ({screenshot.stat().st_size} bytes)")
            valid_screenshots += 1
        else:
            print(f"⚠️  Screenshot found but too small: {screenshot.name}")
    
    if valid_screenshots == 0:
        print("❌ No valid screenshots found")
    elif valid_screenshots == 1:
        print("⚠️  Only 1 screenshot found (expected 2: homepage and /get page)")
    else:
        print(f"✅ {valid_screenshots} screenshots found (expected 2)")
    
    return valid_screenshots

def check_page_title(work_dir: Path) -> bool:
    """Check if page title was extracted."""
    title_files = (
        list(work_dir.glob("*title*.txt")) +
        list(work_dir.glob("*title*.json")) +
        list(work_dir.glob("*extracted*.txt")) +
        list(work_dir.glob("*extracted*.json"))
    )
    
    title_found = False
    
    # Check text files
    for title_file in title_files:
        if title_file.suffix in ['.txt', '.log']:
            try:
                content = title_file.read_text().lower()
                if any(pattern.lower() in content for pattern in EXPECTED_TITLE_PATTERNS):
                    print(f"✅ Page title found in {title_file.name}: {content.strip()[:50]}...")
                    title_found = True
                    break
            except IOError:
                continue
    
    # Check JSON files for title
    if not title_found:
        json_files = list(work_dir.glob("*.json"))
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Look for title in various possible keys
                title_keys = ['title', 'page_title', 'heading', 'h1']
                for key in title_keys:
                    if key in data:
                        title_value = str(data[key]).lower()
                        if any(pattern.lower() in title_value for pattern in EXPECTED_TITLE_PATTERNS):
                            print(f"✅ Page title found in {json_file.name}: {data[key]}")
                            title_found = True
                            break
                
                if title_found:
                    break
                    
            except (json.JSONDecodeError, IOError):
                continue
    
    if not title_found:
        print("❌ No page title found")
    
    return title_found

def check_json_response(work_dir: Path) -> bool:
    """Check if JSON response from /get endpoint was captured."""
    json_files = list(work_dir.glob("*.json"))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Check if this looks like a /get response
            if isinstance(data, dict):
                # Look for typical /get response fields
                found_fields = []
                for field in EXPECTED_JSON_FIELDS:
                    if field in data:
                        found_fields.append(field)
                
                # Also check for the URL in the response
                url_evidence = False
                if 'url' in data and isinstance(data['url'], str):
                    if EXPECTED_GET_URL in data['url']:
                        url_evidence = True
                
                if len(found_fields) >= 2 or url_evidence:
                    print(f"✅ JSON response from /get endpoint found in {json_file.name}")
                    print(f"   Fields found: {found_fields}")
                    if url_evidence:
                        print(f"   URL confirmed: {data.get('url', 'N/A')}")
                    return True
                    
        except (json.JSONDecodeError, IOError):
            continue
    
    print("❌ No valid JSON response from /get endpoint found")
    return False

def check_navigation_evidence(work_dir: Path) -> bool:
    """Check for evidence that both URLs were visited."""
    log_files = list(work_dir.glob("*.log")) + list(work_dir.glob("*.txt"))
    
    homepage_visited = False
    get_endpoint_visited = False
    
    # Check log files
    for log_file in log_files:
        try:
            content = log_file.read_text().lower()
            if EXPECTED_HOMEPAGE_URL in content:
                homepage_visited = True
            if EXPECTED_GET_URL in content:
                get_endpoint_visited = True
        except IOError:
            continue
    
    # Also check JSON files for URL evidence
    json_files = list(work_dir.glob("*.json"))
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                content = f.read().lower()
                if EXPECTED_HOMEPAGE_URL in content:
                    homepage_visited = True
                if EXPECTED_GET_URL in content:
                    get_endpoint_visited = True
        except (IOError, UnicodeDecodeError):
            continue
    
    if homepage_visited:
        print("✅ Evidence of homepage navigation found")
    else:
        print("⚠️  No clear evidence of homepage navigation")
    
    if get_endpoint_visited:
        print("✅ Evidence of /get endpoint navigation found")
    else:
        print("⚠️  No clear evidence of /get endpoint navigation")
    
    return homepage_visited  # At minimum, homepage should have been visited

# =============================================================================
# MAIN VERIFICATION
# =============================================================================

def verify_task() -> bool:
    """Verify that the web navigation task was completed successfully."""
    print("🔍 Verifying Playwright Web Navigation Task")
    print("=" * 50)
    
    # Get working directory
    work_dir = get_working_directory()
    print(f"📁 Working directory: {work_dir}")
    
    success = True
    
    # 1. Check for screenshots (expecting 2)
    print("\n📸 Checking for screenshots...")
    screenshot_count = check_screenshots(work_dir)
    if screenshot_count < 1:
        success = False
    elif screenshot_count < 2:
        print("⚠️  Expected 2 screenshots but found fewer")
        # Don't fail completely, but note the issue
    
    # 2. Check for page title
    print("\n📄 Checking for extracted page title...")
    if not check_page_title(work_dir):
        success = False
    
    # 3. Check for JSON response
    print("\n🔧 Checking for JSON response from /get endpoint...")
    if not check_json_response(work_dir):
        success = False
    
    # 4. Check for navigation evidence
    print("\n🌐 Checking for navigation evidence...")
    if not check_navigation_evidence(work_dir):
        success = False
    
    return success

def main():
    """Main verification function."""
    try:
        success = verify_task()
        
        if success:
            print("\n🎉 Web navigation task verification: PASSED")
            print("Navigation completed successfully with required outputs")
            sys.exit(0)
        else:
            print("\n❌ Web navigation task verification: FAILED")
            print("Some required navigation outputs missing")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()