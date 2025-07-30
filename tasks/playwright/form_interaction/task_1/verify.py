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
import os
from pathlib import Path
from typing import Dict, Any
from playwright.sync_api import sync_playwright

# =============================================================================
# CONFIGURATION
# =============================================================================

# Target website for verification
TARGET_URL = "https://mcp-eval-website.vercel.app/forms/"

# Expected form fields based on task description (6 fields total)
EXPECTED_FORM_FIELDS = {
    "custname": "Customer Name",
    "custtel": "Phone",
    "custemail": "Email", 
    "size": "Size",
    "delivery": "Delivery Time",
    "comments": "Comments"
}

# Test data for form submission (matches task requirements)
TEST_FORM_DATA = {
    "custname": "John Doe",
    "custtel": "123-456-7890",
    "custemail": "john.doe@example.com",
    "size": "large",
    "delivery": "afternoon",
    "comments": "This is a test submission for MCPBench"
}

# Accuracy thresholds for comparison
MIN_ACCURACY_THRESHOLD = 1.0  # 100% accuracy required to pass

# =============================================================================
# INDEPENDENT PLAYWRIGHT VERIFICATION
# =============================================================================

def verify_form_fields() -> Dict[str, Any]:
    """Use Playwright to verify form fields exist and are functional."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"🌐 Navigating to: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle")
            
            # Check if form exists
            form_selector = "form"
            if not page.locator(form_selector).count():
                browser.close()
                return {"success": False, "error": "No form found on page"}
            
            form_fields_found = {}
            
            # Check each expected form field
            for field_name, field_label in EXPECTED_FORM_FIELDS.items():
                # Try different selectors for each field
                selectors = [
                    f"input[name='{field_name}']",
                    f"textarea[name='{field_name}']",
                    f"select[name='{field_name}']",
                    f"input[id='{field_name}']",
                    f"textarea[id='{field_name}']",
                    f"select[id='{field_name}']"
                ]
                
                field_found = False
                field_type = None
                
                for selector in selectors:
                    if page.locator(selector).count() > 0:
                        field_found = True
                        element = page.locator(selector).first
                        field_type = element.get_attribute("type")
                        if not field_type:
                            # Get tag name as fallback
                            try:
                                field_type = element.evaluate("element => element.tagName.toLowerCase()")
                            except:
                                field_type = "unknown"
                        break
                
                form_fields_found[field_name] = {
                    "found": field_found,
                    "type": field_type
                }
            
            browser.close()
            
            return {
                "success": True,
                "form_fields": form_fields_found,
                "total_fields": len([f for f in form_fields_found.values() if f["found"]]),
                "expected_fields": len(EXPECTED_FORM_FIELDS)
            }
            
    except Exception as e:
        print(f"❌ Error during form verification: {e}")
        return {"success": False, "error": str(e)}

def test_form_submission() -> Dict[str, Any]:
    """Test form submission functionality."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"🌐 Testing form submission on: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle")
            
            # Fill out the form with test data
            submission_success = True
            filled_fields = {}
            
            for field_name, test_value in TEST_FORM_DATA.items():
                selectors = [
                    f"input[name='{field_name}']",
                    f"textarea[name='{field_name}']",
                    f"select[name='{field_name}']",
                    f"input[id='{field_name}']",
                    f"textarea[id='{field_name}']",
                    f"select[id='{field_name}']"
                ]
                
                field_filled = False
                for selector in selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            element = page.locator(selector).first
                            try:
                                tag_name = element.evaluate("element => element.tagName.toLowerCase()")
                            except:
                                tag_name = "input"
                            if tag_name == "select":
                                # For select elements, try to select by value or text
                                page.select_option(selector, value=test_value)
                            elif element.get_attribute("type") == "radio":
                                # For radio buttons, check the one with matching value
                                page.check(f"{selector}[value='{test_value}']")
                            else:
                                # For text inputs and textareas
                                page.fill(selector, test_value)
                            field_filled = True
                            break
                    except Exception as e:
                        continue
                
                filled_fields[field_name] = field_filled
                if not field_filled:
                    submission_success = False
            
            # Try to submit the form
            submit_attempted = False
            try:
                # Look for submit button
                submit_selectors = [
                    "input[type='submit']",
                    "button[type='submit']",
                    "button:has-text('Submit')",
                    "input[value*='Submit']"
                ]
                
                for selector in submit_selectors:
                    if page.locator(selector).count() > 0:
                        page.click(selector)
                        submit_attempted = True
                        break
                
                if not submit_attempted:
                    # Try pressing Enter in the form
                    page.keyboard.press("Enter")
                    submit_attempted = True
                    
            except Exception as e:
                print(f"⚠️  Form submission attempt failed: {e}")
            
            browser.close()
            
            return {
                "success": True,
                "filled_fields": filled_fields,
                "fields_filled_count": sum(1 for f in filled_fields.values() if f),
                "submit_attempted": submit_attempted,
                "submission_success": submission_success
            }
            
    except Exception as e:
        print(f"❌ Error during form submission test: {e}")
        return {"success": False, "error": str(e)}

# =============================================================================
# MCP RESULT PARSING
# =============================================================================

def get_working_directory() -> Path:
    """Get the working directory where messages.json should be."""
    # For MCPBench, check current directory first
    current_dir = Path.cwd()
    if (current_dir / "messages.json").exists():
        return current_dir
    
    # Fallback to environment variable
    work_dir = os.getenv("PLAYWRIGHT_WORK_DIR", ".")
    return Path(work_dir).resolve()

def parse_mcp_agent_results(work_dir: Path) -> Dict[str, Any]:
    """Extract what the MCP agent actually found from messages.json"""
    messages_file = work_dir / "messages.json"
    if not messages_file.exists():
        return {"success": False, "error": "No messages.json found"}
    
    try:
        with open(messages_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return {"success": False, "error": f"Failed to read messages.json: {e}"}
    
    # Initialize findings
    agent_findings = {
        "form_fields_found": [],
        "form_filled": False,
        "form_submitted": False,
        "form_data_used": {}
    }
    
    # Parse agent's findings from conversation
    for message in messages:
        if message.get("role") == "assistant":
            content = str(message.get("content", ""))
            
            # Handle both string and list content formats
            if isinstance(message.get("content"), list):
                content = " ".join(
                    item.get("text", "") if isinstance(item, dict) else str(item) 
                    for item in message.get("content", [])
                )
            
            content_lower = content.lower()
            
            # Check for form field interactions
            for field_name in EXPECTED_FORM_FIELDS.keys():
                if field_name in content_lower and field_name not in agent_findings["form_fields_found"]:
                    agent_findings["form_fields_found"].append(field_name)
            
            # Check for form filling evidence
            if any(word in content_lower for word in ["filled", "fill", "entered", "input", "typing"]):
                agent_findings["form_filled"] = True
            
            # Check for form submission evidence
            if any(word in content_lower for word in ["submit", "click", "send", "post"]):
                agent_findings["form_submitted"] = True
            
            # Extract form data used
            for field_name, test_value in TEST_FORM_DATA.items():
                if test_value.lower() in content_lower:
                    agent_findings["form_data_used"][field_name] = test_value
    
    return {"success": True, "findings": agent_findings}

# =============================================================================
# COMPARISON AND EVALUATION
# =============================================================================

def compare_mcp_vs_independent(mcp_results: Dict, field_data: Dict, submission_data: Dict) -> Dict[str, Any]:
    """Compare MCP agent findings with independent verification"""
    comparison = {}
    
    # Compare form fields found
    mcp_fields = set(mcp_results["findings"]["form_fields_found"])
    actual_fields = set(field_name for field_name, field_info in field_data["form_fields"].items() if field_info["found"])
    
    if actual_fields:
        field_accuracy = len(mcp_fields.intersection(actual_fields)) / len(actual_fields)
        missing_fields = list(actual_fields - mcp_fields)
        extra_fields = list(mcp_fields - actual_fields)
    else:
        field_accuracy = 0.0
        missing_fields = []
        extra_fields = list(mcp_fields)
    
    comparison["form_fields"] = {
        "mcp_count": len(mcp_fields),
        "independent_count": len(actual_fields),
        "accuracy": field_accuracy,
        "match": field_accuracy >= MIN_ACCURACY_THRESHOLD,
        "missing": missing_fields,
        "extra": extra_fields
    }
    
    # Compare form interaction (filling) - require all 6 fields
    mcp_filled = mcp_results["findings"]["form_filled"]
    actual_filled = submission_data["fields_filled_count"] == len(EXPECTED_FORM_FIELDS)
    
    fill_accuracy = 1.0 if (mcp_filled and actual_filled) or (not mcp_filled and not actual_filled) else 0.0
    
    comparison["form_filling"] = {
        "mcp_filled": mcp_filled,
        "independent_filled": actual_filled,
        "accuracy": fill_accuracy,
        "match": fill_accuracy >= MIN_ACCURACY_THRESHOLD
    }
    
    # Compare form submission
    mcp_submitted = mcp_results["findings"]["form_submitted"]
    actual_submitted = submission_data["submit_attempted"]
    
    submit_accuracy = 1.0 if (mcp_submitted and actual_submitted) or (not mcp_submitted and not actual_submitted) else 0.0
    
    comparison["form_submission"] = {
        "mcp_submitted": mcp_submitted,
        "independent_submitted": actual_submitted,
        "accuracy": submit_accuracy,
        "match": submit_accuracy >= MIN_ACCURACY_THRESHOLD
    }
    
    return comparison

def verify_form_requirements(field_data: Dict[str, Any], submission_data: Dict[str, Any]) -> bool:
    """Verify that the form meets task requirements."""
    if not field_data.get("success") or not submission_data.get("success"):
        print(f"❌ Independent verification failed: {field_data.get('error', '')} {submission_data.get('error', '')}")
        return False
    
    success = True
    
    # Check that all expected form fields are present
    total_fields = field_data["total_fields"]
    expected_fields = field_data["expected_fields"]
    
    if total_fields == expected_fields:
        print(f"✅ Form fields: {total_fields}/{expected_fields} found")
    else:
        print(f"❌ Form fields: {total_fields}/{expected_fields} found (missing some fields)")
        success = False
    
    # Check form submission capability (require all 6 fields)
    fields_filled = submission_data["fields_filled_count"]
    expected_fields_count = len(EXPECTED_FORM_FIELDS)
    if fields_filled == expected_fields_count:
        print(f"✅ Form interaction: {fields_filled} fields successfully filled")
    else:
        print(f"❌ Form interaction: Only {fields_filled}/{expected_fields_count} fields could be filled (expected exactly {expected_fields_count})")
        success = False
    
    # Check if form submission was attempted
    if submission_data["submit_attempted"]:
        print("✅ Form submission: Submit attempt successful")
    else:
        print("❌ Form submission: Could not attempt form submission")
        success = False
    
    return success

# =============================================================================
# MAIN VERIFICATION
# =============================================================================

def verify_task() -> bool:
    """Verify both independent requirements AND MCP agent accuracy"""
    print("🔍 Verifying Playwright Form Interaction Task")
    print("=" * 50)
    
    # Step 1: Independent verification
    print("\n🎭 Running independent Playwright verification...")
    field_data = verify_form_fields()
    submission_data = test_form_submission()
    independent_success = verify_form_requirements(field_data, submission_data)
    
    if not independent_success:
        print("\n❌ Task requirements cannot be met - form doesn't meet expected functionality")
        return False
    
    # Step 2: Parse MCP agent results
    print("\n🤖 Parsing MCP agent results...")
    work_dir = get_working_directory()
    print(f"📁 Working directory: {work_dir}")
    
    mcp_data = parse_mcp_agent_results(work_dir)
    
    if not mcp_data["success"]:
        print(f"❌ Could not parse MCP results: {mcp_data.get('error')}")
        print("⚠️  Task cannot be evaluated - treating as independent verification only")
        return independent_success
    
    # Step 3: Compare MCP vs Independent
    print("\n📊 Comparing MCP agent results with independent verification...")
    comparison = compare_mcp_vs_independent(mcp_data, field_data, submission_data)
    
    # Step 4: Evaluation
    overall_success = True
    
    for category, results in comparison.items():
        accuracy = results["accuracy"] * 100
        category_name = category.replace("_", " ").title()
        
        if results["match"]:
            print(f"✅ {category_name}: {accuracy:.1f}% accuracy")
        else:
            print(f"❌ {category_name}: {accuracy:.1f}% accuracy")
            overall_success = False
    
    # Step 5: Detailed breakdown
    if not overall_success:
        print(f"\n📋 Detailed comparison (threshold: {MIN_ACCURACY_THRESHOLD*100}%):")
        
        # Form fields detail
        field_results = comparison["form_fields"]
        if field_results["missing"] or field_results["extra"]:
            print(f"   Form Fields:")
            if field_results["missing"]:
                print(f"     • Missing: {field_results['missing']}")
            if field_results["extra"]:
                print(f"     • Extra: {field_results['extra']}")
        
        # Show what MCP found vs actual
        print(f"\n   MCP Found: {len(mcp_data['findings']['form_fields_found'])} form fields")
        print(f"   Actually: {field_data['total_fields']} form fields functional")
        print(f"   MCP Form Filled: {mcp_data['findings']['form_filled']}")
        print(f"   Actually Fillable: {submission_data['fields_filled_count']} fields")
    
    else:
        print(f"\n🎉 MCP agent successfully interacted with form with {MIN_ACCURACY_THRESHOLD*100}% accuracy in all categories!")
    
    return overall_success

def main():
    """Main verification function."""
    try:
        success = verify_task()
        
        if success:
            print("\n🎉 Form interaction task verification: PASSED")
            print("Both form functionality and MCP agent accuracy meet requirements")
            sys.exit(0)
        else:
            print("\n❌ Form interaction task verification: FAILED")
            print("Either form functionality or MCP agent accuracy below requirements")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()