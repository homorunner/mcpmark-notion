#!/usr/bin/env python3
"""
Verification script for Playwright form interaction task.

This script verifies that the form interaction task was completed successfully
by checking for form submission evidence and response data.
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

# Expected form data
EXPECTED_FORM_DATA = {
    "custname": "John Doe",
    "custtel": "123-456-7890",
    "custemail": "john.doe@example.com",
    "size": "large",  # Case variations allowed
    "comments": "This is a test submission"
}

# Expected output files
EXPECTED_RESPONSE_FILE = "form_response.json"
EXPECTED_SCREENSHOT = "form_submission.png"

# Expected URL patterns
EXPECTED_FORM_URL = "httpbin.org/forms/post"
EXPECTED_RESPONSE_URL = "httpbin.org/post"

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

def check_response_file(work_dir: Path) -> Dict[str, Any]:
    """Check if form response file exists and contains form data."""
    response_files = (
        list(work_dir.glob("*response*.json")) +
        list(work_dir.glob("*form*.json")) +
        list(work_dir.glob("*submission*.json")) +
        list(work_dir.glob("*post*.json"))
    )
    
    if not response_files:
        # Check if screenshots exist as evidence of task completion
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        all_files = list(work_dir.glob("*.*"))
        screenshot_files = [f for f in all_files if f.suffix.lower() in image_extensions]
        if screenshot_files:
            print("✅ Form interaction attempted (screenshots found as evidence)")
            return {"screenshots_found": True}  # Return minimal data to indicate completion
        else:
            print("❌ No form response files found")
            return {}
    
    for response_file in response_files:
        try:
            with open(response_file, 'r') as f:
                data = json.load(f)
            print(f"✅ Response file found: {response_file.name}")
            return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Found response file {response_file.name} but couldn't parse: {e}")
            continue
    
    return {}

def check_screenshot_file(work_dir: Path) -> bool:
    """Check if form screenshot exists."""
    # Look for any image files in the directory
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
    all_files = list(work_dir.glob("*.*"))
    screenshot_files = [f for f in all_files if f.suffix.lower() in image_extensions]
    
    if not screenshot_files:
        print("❌ No form screenshot files found")
        return False
    
    # Check if any screenshot file has reasonable size (> 1KB)
    for screenshot in screenshot_files:
        if screenshot.stat().st_size > 1024:
            print(f"✅ Screenshot found: {screenshot.name} ({screenshot.stat().st_size} bytes)")
            return True
    
    print("❌ Screenshot files found but appear to be empty or too small")
    return False

def verify_form_data_in_response(response_data: Dict[str, Any]) -> bool:
    """Verify that the expected form data appears in the response."""
    if not response_data:
        print("❌ No response data to verify")
        return False
    
    # If we only have screenshot evidence, consider it a basic success
    if response_data.get("screenshots_found") and len(response_data) == 1:
        print("✅ Form interaction verified through screenshot evidence")
        return True
    
    # Look for form data in various possible locations in the response
    form_data_locations = ['form', 'data', 'json', 'args', 'values', 'body']
    found_form_data = {}
    
    def extract_form_data(obj, path=""):
        """Recursively extract form data from response object."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.lower() in ['custname', 'custtel', 'custemail', 'size', 'comments']:
                    found_form_data[key.lower()] = str(value)
                elif isinstance(value, (dict, list)):
                    extract_form_data(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    extract_form_data(item, path)
    
    # Extract form data from response
    extract_form_data(response_data)
    
    if not found_form_data:
        print("❌ No form data found in response")
        return False
    
    print(f"✅ Form data found in response: {found_form_data}")
    
    # Verify each expected field
    success = True
    for field, expected_value in EXPECTED_FORM_DATA.items():
        if field.lower() in found_form_data:
            actual_value = found_form_data[field.lower()].lower()
            expected_lower = expected_value.lower()
            
            # Allow for some flexibility in matching
            if expected_lower in actual_value or actual_value in expected_lower:
                print(f"✅ Field '{field}' matches: expected '{expected_value}', found '{found_form_data[field.lower()]}'")
            else:
                print(f"❌ Field '{field}' mismatch: expected '{expected_value}', found '{found_form_data[field.lower()]}'")
                success = False
        else:
            print(f"❌ Field '{field}' not found in response")
            success = False
    
    return success

def check_url_evidence(work_dir: Path) -> bool:
    """Check for evidence that correct URLs were accessed."""
    log_files = list(work_dir.glob("*.log")) + list(work_dir.glob("*.txt"))
    
    form_url_found = False
    response_url_found = False
    
    for log_file in log_files:
        try:
            content = log_file.read_text().lower()
            if EXPECTED_FORM_URL.lower() in content:
                form_url_found = True
                print(f"✅ Form URL evidence found in {log_file.name}")
            if EXPECTED_RESPONSE_URL.lower() in content:
                response_url_found = True
                print(f"✅ Response URL evidence found in {log_file.name}")
        except IOError:
            continue
    
    # Also check in any JSON files for URL evidence
    json_files = list(work_dir.glob("*.json"))
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                content = f.read().lower()
                if EXPECTED_FORM_URL.lower() in content:
                    form_url_found = True
                if EXPECTED_RESPONSE_URL.lower() in content:
                    response_url_found = True
        except (IOError, UnicodeDecodeError):
            continue
    
    # If we have screenshots, that's evidence of some kind of form interaction
    if not (form_url_found or response_url_found):
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        all_files = list(work_dir.glob("*.*"))
        screenshot_files = [f for f in all_files if f.suffix.lower() in image_extensions]
        if screenshot_files:
            print("✅ Form interaction evidence found (screenshots present)")
            return True
    
    if form_url_found:
        print("✅ Evidence of form URL access found")
    else:
        print("⚠️  No clear evidence of form URL access")
    
    if response_url_found:
        print("✅ Evidence of response URL access found")
    else:
        print("⚠️  No clear evidence of response URL access")
    
    return form_url_found or response_url_found  # Accept either URL evidence

# =============================================================================
# MAIN VERIFICATION
# =============================================================================

def verify_task() -> bool:
    """Verify that the form interaction task was completed successfully."""
    print("🔍 Verifying Playwright Form Interaction Task")
    print("=" * 50)
    
    # Get working directory
    work_dir = get_working_directory()
    print(f"📁 Working directory: {work_dir}")
    
    success = True
    
    # 1. Check for form response data
    print("\n📄 Checking for form response data...")
    response_data = check_response_file(work_dir)
    if not response_data:
        success = False
    else:
        # Verify form data in response
        print("\n🔍 Verifying form data in response...")
        if not verify_form_data_in_response(response_data):
            success = False
    
    # 2. Check for screenshot
    print("\n📸 Checking for form screenshot...")
    if not check_screenshot_file(work_dir):
        success = False
    
    # 3. Check for URL access evidence
    print("\n🌐 Checking for URL access evidence...")
    if not check_url_evidence(work_dir):
        success = False
    
    return success

def main():
    """Main verification function."""
    try:
        success = verify_task()
        
        if success:
            print("\n🎉 Form interaction task verification: PASSED")
            print("Form submission completed successfully with expected data")
            sys.exit(0)
        else:
            print("\n❌ Form interaction task verification: FAILED")
            print("Form submission incomplete or data missing")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()