#!/usr/bin/env python3
"""
Verification script for Playwright form interaction task.

This script uses dual verification:
1. Independent Playwright verification of form functionality
2. Parsing and comparison of MCP agent results vs independent verification
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any
from playwright.sync_api import sync_playwright

# =============================================================================
# CONFIGURATION
# =============================================================================

TARGET_URL = "https://mcp-eval-website.vercel.app/forms/"

# Test data for form submission (matches task requirements)
TEST_FORM_DATA = {
    "custname": "John Doe",
    "custtel": "123-456-7890", 
    "custemail": "john.doe@example.com",
    "size": "Large",
    "delivery": "Afternoon",
    "comments": "This is a test submission for MCPBench"
}

EXPECTED_FIELD_COUNT = 6

# =============================================================================
# CORE VERIFICATION
# =============================================================================

def get_field_selectors(field_name: str) -> list[str]:
    """Get common selectors for a form field."""
    return [
        f"input[name='{field_name}']",
        f"textarea[name='{field_name}']", 
        f"select[name='{field_name}']",
        f"input[id='{field_name}']",
        f"textarea[id='{field_name}']",
        f"select[id='{field_name}']"
    ]

def fill_form_field(page, field_name: str, value: str) -> bool:
    """Fill a single form field with the given value."""
    for selector in get_field_selectors(field_name):
        try:
            if page.locator(selector).count() > 0:
                element = page.locator(selector).first
                tag_name = element.evaluate("element => element.tagName.toLowerCase()", timeout=1000)
                
                if tag_name == "select":
                    page.select_option(selector, value=value)
                elif element.get_attribute("type") == "radio":
                    # For radio buttons, use lowercase values as that's what the form expects
                    radio_value = value.lower()
                    page.check(f"{selector}[value='{radio_value}']")
                else:
                    page.fill(selector, value)
                return True
        except:
            continue
    return False

def test_form_functionality() -> Dict[str, Any]:
    """Test complete form functionality: fill, submit, validate result."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"🌐 Testing form on: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle")
            
            # Check form exists
            if not page.locator("form").count():
                browser.close()
                return {"success": False, "error": "No form found"}
            
            # Fill all form fields
            filled_count = 0
            for field_name, value in TEST_FORM_DATA.items():
                if fill_form_field(page, field_name, value):
                    filled_count += 1
            
            # Submit form
            submit_selectors = ["input[type='submit']", "button[type='submit']", "button:has-text('Submit')"]
            submitted = False
            
            for selector in submit_selectors:
                if page.locator(selector).count() > 0:
                    page.click(selector)
                    submitted = True
                    break
            
            if not submitted:
                browser.close()
                return {"success": False, "error": "No submit button found"}
            
            # Wait for redirect and validate result page
            page.wait_for_url(lambda url: "/forms/result/" in url, timeout=10000)
            current_url = page.url
            
            # Extract submission ID
            match = re.search(r'/forms/result/(\d+)', current_url)
            if not match:
                browser.close()
                return {"success": False, "error": f"Invalid result URL: {current_url}"}
            
            submission_id = int(match.group(1))
            print(f"✅ Redirected to result page with submission ID: {submission_id}")
            
            # Wait for content to load and validate
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            result_validation = validate_result_page(page)
            browser.close()
            
            return {
                "success": True,
                "fields_filled": filled_count,
                "submission_id": submission_id,
                "result_validation": result_validation
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def validate_result_page(page) -> Dict[str, Any]:
    """Validate the backend result page content.""" 
    try:
        page_text = page.inner_text('body')
        
        # Extract submission data using patterns
        patterns = {
            "customer_name": r"Customer Name:\s*(.+?)(?:\n|$)",
            "phone_number": r"Phone Number:\s*(.+?)(?:\n|$)", 
            "email_address": r"Email Address:\s*(.+?)(?:\n|$)",
            "size": r"Size:\s*(.+?)(?:\n|$)",
            "delivery_time": r"Delivery Time:\s*(.+?)(?:\n|$)",
            "comments": r"Comments:\s*(.+?)(?:\n|$)"
        }
        
        extracted_data = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                extracted_data[key] = match.group(1).strip()
        
        # Compare with expected test data (backend normalizes to lowercase)
        expected_mapping = {
            "customer_name": TEST_FORM_DATA["custname"],
            "phone_number": TEST_FORM_DATA["custtel"],
            "email_address": TEST_FORM_DATA["custemail"], 
            "size": TEST_FORM_DATA["size"].lower(),  # Backend stores as lowercase
            "delivery_time": TEST_FORM_DATA["delivery"].lower(),  # Backend stores as lowercase
            "comments": TEST_FORM_DATA["comments"]
        }
        
        all_correct = True
        for key, expected in expected_mapping.items():
            actual = extracted_data.get(key, "").lower().strip()
            if actual != expected.lower().strip():
                all_correct = False
                break
        
        return {
            "has_success_message": "Form Submission Successful" in page_text,
            "data_extracted": extracted_data, 
            "all_data_correct": all_correct
        }
        
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# MCP RESULT PARSING  
# =============================================================================

def parse_mcp_results() -> Dict[str, Any]:
    """Parse MCP agent results from messages.json."""
    messages_file = Path.cwd() / "messages.json"
    if not messages_file.exists():
        return {"success": False, "error": "No messages.json found"}
    
    try:
        with open(messages_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"Failed to read messages.json: {e}"}
    
    # Check for key activities in agent conversation
    agent_activities = {
        "form_filled": False,
        "form_submitted": False, 
        "result_page_visited": False,
        "data_verified": False
    }
    
    for message in messages:
        # Check assistant messages
        if message.get("role") == "assistant":
            content = str(message.get("content", ""))
            if isinstance(message.get("content"), list):
                content = " ".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in message.get("content", [])
                )
            content_lower = content.lower()
            
            # Check for evidence of key activities  
            if any(word in content_lower for word in ["fill", "enter", "input", "type", "typed", "typing"]):
                agent_activities["form_filled"] = True
            if any(word in content_lower for word in ["submit", "click", "send"]):
                agent_activities["form_submitted"] = True  
            if any(phrase in content_lower for phrase in ["result", "redirect", "/forms/result"]):
                agent_activities["result_page_visited"] = True
            if any(phrase in content_lower for phrase in ["verify", "validation", "data appears", "correct", "capture", "content"]):
                agent_activities["data_verified"] = True
        
        # Check function call outputs (where the actual playwright commands show)
        elif message.get("type") == "function_call_output":
            output = str(message.get("output", ""))
            output_lower = output.lower()
            
            if any(word in output_lower for word in ["fill", "enter", "input", "type", "typed", "typing"]):
                agent_activities["form_filled"] = True
            if any(word in output_lower for word in ["submit", "click", "send"]):
                agent_activities["form_submitted"] = True  
            if any(phrase in output_lower for phrase in ["result", "redirect", "/forms/result"]):
                agent_activities["result_page_visited"] = True
    
    return {"success": True, "activities": agent_activities}

# =============================================================================
# MAIN VERIFICATION
# =============================================================================

def verify_task() -> bool:
    """Main verification function."""
    print("🔍 Verifying Playwright Form Interaction Task")
    print("=" * 50)
    
    # Test independent functionality
    print("\n🎭 Running independent verification...")
    test_result = test_form_functionality()
    
    if not test_result["success"]:
        print(f"❌ Form functionality test failed: {test_result.get('error')}")
        return False
    
    # Validate results
    success = True
    
    # Check field filling
    if test_result["fields_filled"] == EXPECTED_FIELD_COUNT:
        print(f"✅ Form fields: {test_result['fields_filled']}/{EXPECTED_FIELD_COUNT} filled successfully")
    else:
        print(f"❌ Form fields: Only {test_result['fields_filled']}/{EXPECTED_FIELD_COUNT} filled")
        success = False
    
    # Check submission ID
    if test_result.get("submission_id"):
        print(f"✅ Submission ID: {test_result['submission_id']}")
    else:
        print("❌ Submission ID: Not found")
        success = False
    
    # Check result page validation
    result_validation = test_result.get("result_validation", {})
    if result_validation.get("all_data_correct"):
        print("✅ Result page: All data validated correctly")
    else:
        print("❌ Result page: Data validation failed")
        success = False
    
    if not success:
        print("\n❌ Form functionality requirements not met")
        return False
    
    # Parse MCP results if available
    print("\n🤖 Checking MCP agent results...")
    mcp_result = parse_mcp_results()
    
    if not mcp_result["success"]:
        print(f"⚠️  {mcp_result.get('error')} - treating as independent verification only")
        return True
    
    # Evaluate MCP performance
    activities = mcp_result["activities"]
    mcp_success = True
    
    for activity, completed in activities.items():
        activity_name = activity.replace("_", " ").title()
        if completed:
            print(f"✅ MCP {activity_name}: Detected")
        else:
            print(f"❌ MCP {activity_name}: Not detected")
            mcp_success = False
    
    if mcp_success:
        print("\n🎉 Both form functionality and MCP agent performance verified successfully!")
    else:
        print("\n⚠️  Form functionality verified, but MCP agent performance incomplete")
    
    return mcp_success

def main():
    """Entry point."""
    try:
        success = verify_task()
        if success:
            print("\n🎉 Form interaction task verification: PASSED")
            sys.exit(0)
        else:
            print("\n❌ Form interaction task verification: FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()