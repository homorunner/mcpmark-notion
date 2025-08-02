#!/usr/bin/env python3
"""
Verification script for Playwright Cloudflare Turnstile authentication task.

This script uses dual verification:
1. Independent Playwright verification of Turnstile functionality
2. Parsing and comparison of MCP agent results vs independent verification
"""

import sys
import json
import re
import os
import time
from pathlib import Path
from typing import Dict, Any
from playwright.sync_api import sync_playwright

# =============================================================================
# CONFIGURATION
# =============================================================================

# Target website for verification
TARGET_URL = "https://mcp-eval-website.vercel.app/auth/turnstile"

# Test credentials for authentication
TEST_CREDENTIALS = {
    "username": "testuser",
    "password": "password123"
}

# Expected page elements for Turnstile authentication
EXPECTED_ELEMENTS = {
    "turnstile_widget": "Turnstile challenge widget",
    "form": "Authentication form",
    "username_field": "Username input field",
    "password_field": "Password input field", 
    "submit_button": "Submit button"
}

# Expected success message
SUCCESS_MESSAGE = "Authentication successful! Security challenge verified."

# Accuracy thresholds for comparison
MIN_ACCURACY_THRESHOLD = 1.0  # 100% accuracy required to pass

# =============================================================================
# INDEPENDENT PLAYWRIGHT VERIFICATION
# =============================================================================

def verify_turnstile_page() -> Dict[str, Any]:
    """Use Playwright to verify Turnstile page loads and elements exist."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"🌐 Navigating to: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for page to fully load
            time.sleep(2)
            
            elements_found = {}
            
            # Check for Turnstile widget (Cloudflare challenge iframe)
            turnstile_selectors = [
                "iframe[src*='cloudflare']",
                "iframe[title*='Turnstile']",
                "iframe[title*='challenge']",
                ".cf-turnstile",
                "[data-sitekey]",
                "div[id*='turnstile']"
            ]
            
            turnstile_found = False
            for selector in turnstile_selectors:
                if page.locator(selector).count() > 0:
                    turnstile_found = True
                    break
            
            elements_found["turnstile_widget"] = turnstile_found
            
            # Check for form
            form_found = page.locator("form").count() > 0
            elements_found["form"] = form_found
            
            # Check for submit button
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']",
                "button:has-text('Submit')",
                "button:has-text('Verify')",
                "button:has-text('Continue')"
            ]
            
            submit_found = False
            for selector in submit_selectors:
                if page.locator(selector).count() > 0:
                    submit_found = True
                    break
            
            elements_found["submit_button"] = submit_found
            
            browser.close()
            
            return {
                "success": True,
                "elements": elements_found,
                "page_loaded": True
            }
            
    except Exception as e:
        print(f"❌ Error during page verification: {e}")
        return {"success": False, "error": str(e)}

def test_turnstile_functionality() -> Dict[str, Any]:
    """Test Turnstile authentication functionality with actual form interaction."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"🌐 Testing Turnstile functionality on: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for page to load completely
            time.sleep(3)
            
            # Check if form fields are present
            form_fields_present = False
            username_field = page.locator("input[name='username'], input[id='username']")
            password_field = page.locator("input[name='password'], input[id='password']")
            
            if username_field.count() > 0 and password_field.count() > 0:
                form_fields_present = True
            
            # Fill in credentials if form is present
            credentials_filled = False
            if form_fields_present:
                try:
                    username_field.fill(TEST_CREDENTIALS["username"])
                    password_field.fill(TEST_CREDENTIALS["password"])
                    credentials_filled = True
                    print(f"✅ Filled credentials: {TEST_CREDENTIALS['username']}")
                except Exception as e:
                    print(f"⚠️ Failed to fill credentials: {e}")
            
            # Check if Turnstile is present and functional
            turnstile_present = False
            turnstile_selectors = [
                "iframe[src*='cloudflare']",
                "iframe[title*='Turnstile']", 
                ".cf-turnstile",
                "[data-sitekey]"
            ]
            
            for selector in turnstile_selectors:
                if page.locator(selector).count() > 0:
                    turnstile_present = True
                    break
            
            # Wait for Turnstile completion (it should auto-complete with test sitekey)
            turnstile_completed = False
            if turnstile_present:
                try:
                    # Wait longer for auto-completion and check multiple times
                    for attempt in range(10):  # Try for up to 20 seconds
                        page.wait_for_timeout(2000)
                        print(f"⏳ Attempt {attempt + 1}: Checking Turnstile completion...")
                        
                        # Check for success indicators in page content
                        page_content = page.content()
                        if any(indicator in page_content.lower() for indicator in ["success!", "challenge completed", "✓"]):
                            turnstile_completed = True
                            print("✅ Turnstile challenge completed")
                            break
                            
                        # Also check if submit button is enabled (indicates Turnstile completion)
                        submit_button = page.locator("button:has-text('Sign In'), input[type='submit'], button[type='submit']")
                        if submit_button.count() > 0:
                            button_disabled = submit_button.first.is_disabled()
                            print(f"   Submit button disabled: {button_disabled}")
                            if not button_disabled:
                                turnstile_completed = True
                                print("✅ Turnstile challenge completed (button enabled)")
                                break
                        else:
                            print("   Submit button not found")
                    
                    if not turnstile_completed and attempt >= 9:
                        print("⚠️ Turnstile did not complete within timeout - this may be expected behavior")
                    
                except Exception as e:
                    print(f"⚠️ Turnstile completion check failed: {e}")
            
            # Try form submission only after Turnstile completion
            form_submitted = False
            success_message_found = False
            if turnstile_completed:
                try:
                    # Look for Sign In button specifically  
                    submit_button = page.locator("button:has-text('Sign In'), input[type='submit'], button[type='submit']")
                    
                    if submit_button.count() > 0:
                        # Wait for button to be enabled if needed
                        submit_button.first.wait_for(state="attached", timeout=5000)
                        if not submit_button.first.is_disabled():
                            submit_button.first.click()
                            form_submitted = True
                            print("✅ Form submitted")
                            
                            # Wait for response and check for success message
                            page.wait_for_timeout(3000)
                            
                            # Check for success message in page content
                            page_content = page.content()
                            if SUCCESS_MESSAGE.lower() in page_content.lower():
                                success_message_found = True
                                print("✅ Success message found")
                        else:
                            print("⚠️ Submit button still disabled after Turnstile completion")
                            
                except Exception as e:
                    print(f"⚠️ Form submission failed: {e}")
            else:
                print("⚠️ Skipping form submission - Turnstile not completed")
            
            # Get final page state
            final_url = page.url
            page_content = page.content()
            
            browser.close()
            
            return {
                "success": True,
                "form_fields_present": form_fields_present,
                "credentials_filled": credentials_filled,
                "turnstile_present": turnstile_present,
                "turnstile_completed": turnstile_completed,
                "form_submitted": form_submitted,
                "success_message_found": success_message_found,
                "final_url": final_url,
                "stayed_on_page": TARGET_URL in final_url
            }
            
    except Exception as e:
        print(f"❌ Error during functionality test: {e}")
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
        "credentials_filled": False,
        "turnstile_found": False,
        "turnstile_completed": False,
        "form_submitted": False,
        "success_message_found": False,
        "success_message_content": "",
        "authentication_successful": False
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
            
            # Check for credentials filling
            if any(word in content_lower for word in ["testuser", "password123", "username", "password", "credential"]):
                agent_findings["credentials_filled"] = True
            
            # Check for Turnstile detection
            if any(word in content_lower for word in ["turnstile", "cloudflare", "challenge", "captcha"]):
                agent_findings["turnstile_found"] = True
            
            # Check for Turnstile completion
            if any(word in content_lower for word in ["completed", "verified", "success!", "passed", "solved", "challenge completed"]):
                agent_findings["turnstile_completed"] = True
            
            # Check for form submission
            if any(word in content_lower for word in ["submit", "click", "sign in", "send", "post"]):
                agent_findings["form_submitted"] = True
            
            # Check for success message and capture content
            if any(word in content_lower for word in ["authentication successful", "security challenge verified", "success message"]):
                agent_findings["success_message_found"] = True
                # Try to extract the actual success message the agent captured
                if "authentication successful" in content_lower:
                    # Look for the specific message pattern
                    import re
                    message_pattern = r"[\"']([^\"']*authentication successful[^\"']*)[\"']"
                    match = re.search(message_pattern, content, re.IGNORECASE)
                    if match:
                        agent_findings["success_message_content"] = match.group(1)
                    else:
                        # Fallback: look for the message without quotes
                        if SUCCESS_MESSAGE.lower() in content_lower:
                            agent_findings["success_message_content"] = SUCCESS_MESSAGE
            
            # Check for overall authentication success
            if any(word in content_lower for word in ["authenticated", "authentication successful", "login successful"]):
                agent_findings["authentication_successful"] = True
    
    return {"success": True, "findings": agent_findings}

# =============================================================================
# COMPARISON AND EVALUATION
# =============================================================================

def compare_mcp_vs_independent(mcp_results: Dict, page_data: Dict, functionality_data: Dict) -> Dict[str, Any]:
    """Compare MCP agent findings with independent verification"""
    comparison = {}
    
    # Compare credentials filling
    mcp_filled = mcp_results["findings"]["credentials_filled"]
    actual_filled = functionality_data["credentials_filled"]
    
    credentials_accuracy = 1.0 if (mcp_filled and actual_filled) or (not mcp_filled and not actual_filled) else 0.0
    
    comparison["credentials_filling"] = {
        "mcp_filled": mcp_filled,
        "independent_filled": actual_filled,
        "accuracy": credentials_accuracy,
        "match": credentials_accuracy >= MIN_ACCURACY_THRESHOLD
    }
    
    # Compare Turnstile detection
    mcp_found = mcp_results["findings"]["turnstile_found"]
    actual_found = functionality_data["turnstile_present"]
    
    turnstile_detection_accuracy = 1.0 if (mcp_found and actual_found) or (not mcp_found and not actual_found) else 0.0
    
    comparison["turnstile_detection"] = {
        "mcp_found": mcp_found,
        "independent_found": actual_found,
        "accuracy": turnstile_detection_accuracy,
        "match": turnstile_detection_accuracy >= MIN_ACCURACY_THRESHOLD
    }
    
    # Compare Turnstile completion
    mcp_completed = mcp_results["findings"]["turnstile_completed"]
    actual_completed = functionality_data["turnstile_completed"]
    
    completion_accuracy = 1.0 if (mcp_completed and actual_completed) or (not mcp_completed and not actual_completed) else 0.0
    
    comparison["turnstile_completion"] = {
        "mcp_completed": mcp_completed,
        "independent_completed": actual_completed,
        "accuracy": completion_accuracy,
        "match": completion_accuracy >= MIN_ACCURACY_THRESHOLD
    }
    
    # Compare form submission
    mcp_submitted = mcp_results["findings"]["form_submitted"]
    actual_submitted = functionality_data["form_submitted"]
    
    submission_accuracy = 1.0 if (mcp_submitted and actual_submitted) or (not mcp_submitted and not actual_submitted) else 0.0
    
    comparison["form_submission"] = {
        "mcp_submitted": mcp_submitted,
        "independent_submitted": actual_submitted,
        "accuracy": submission_accuracy,
        "match": submission_accuracy >= MIN_ACCURACY_THRESHOLD
    }
    
    # Compare success message detection
    mcp_success = mcp_results["findings"]["success_message_found"]
    actual_success = functionality_data["success_message_found"]
    mcp_message_content = mcp_results["findings"]["success_message_content"]
    
    success_accuracy = 1.0 if (mcp_success and actual_success) or (not mcp_success and not actual_success) else 0.0
    
    # Also check if the captured message content is correct
    message_content_correct = False
    if mcp_message_content and actual_success:
        # Check if captured message matches expected message (case insensitive)
        message_content_correct = SUCCESS_MESSAGE.lower() in mcp_message_content.lower()
    
    comparison["success_message"] = {
        "mcp_found": mcp_success,
        "independent_found": actual_success,
        "mcp_message_content": mcp_message_content,
        "expected_message": SUCCESS_MESSAGE,
        "message_content_correct": message_content_correct,
        "accuracy": success_accuracy,
        "match": success_accuracy >= MIN_ACCURACY_THRESHOLD and (not mcp_success or message_content_correct)
    }
    
    return comparison

def verify_turnstile_requirements(page_data: Dict[str, Any], functionality_data: Dict[str, Any]) -> bool:
    """Verify that the Turnstile page meets task requirements."""
    if not page_data.get("success") or not functionality_data.get("success"):
        print(f"❌ Independent verification failed: {page_data.get('error', '')} {functionality_data.get('error', '')}")
        return False
    
    success = True
    
    # Check that form fields are present and fillable
    if functionality_data["form_fields_present"] and functionality_data["credentials_filled"]:
        print("✅ Form credentials: Form fields present and credentials filled successfully")
    else:
        print("❌ Form credentials: Missing form fields or failed to fill credentials")
        success = False
    
    # Check that Turnstile widget is present
    if functionality_data["turnstile_present"]:
        print("✅ Turnstile widget: Present on page")
    else:
        print("❌ Turnstile widget: Not found on page")
        success = False
    
    # Check form elements from page data
    elements = page_data["elements"]
    if elements["form"] and elements["submit_button"]:
        print("✅ Form elements: Form and submit button found")
    else:
        print("❌ Form elements: Missing form or submit button")
        success = False
    
    # Check if authentication components are present and functional
    if functionality_data["turnstile_completed"]:
        print("✅ Turnstile completion: Challenge was completed successfully")
        if functionality_data["form_submitted"] and functionality_data["success_message_found"]:
            print("✅ Full authentication flow: Form submitted and success message displayed")
        else:
            print("✅ Partial authentication flow: Turnstile completed, form ready for submission")
    else:
        print("✅ Authentication setup: All components present and ready (Turnstile may require interaction)")
        # Don't fail if Turnstile requires manual interaction - this is realistic behavior
        
    # Check that page stays on same URL (no redirect)
    if functionality_data["stayed_on_page"]:
        print("✅ Page behavior: Correctly stayed on same page (no redirect)")
    else:
        print("❌ Page behavior: Unexpected redirect or navigation")
        success = False
    
    return success

# =============================================================================
# MAIN VERIFICATION
# =============================================================================

def verify_task() -> bool:
    """Verify both independent requirements AND MCP agent accuracy"""
    print("🔍 Verifying Playwright Cloudflare Turnstile Authentication Task")
    print("=" * 60)
    
    # Step 1: Independent verification
    print("\n🎭 Running independent Playwright verification...")
    page_data = verify_turnstile_page()
    functionality_data = test_turnstile_functionality()
    independent_success = verify_turnstile_requirements(page_data, functionality_data)
    
    if not independent_success:
        print("\n❌ Task requirements cannot be met - Turnstile page doesn't meet expected functionality")
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
    comparison = compare_mcp_vs_independent(mcp_data, page_data, functionality_data)
    
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
        
        # Show what MCP found vs actual
        print(f"\n   MCP Credentials Filled: {mcp_data['findings']['credentials_filled']}")
        print(f"   Actually Filled: {functionality_data['credentials_filled']}")
        print(f"   MCP Turnstile Found: {mcp_data['findings']['turnstile_found']}")
        print(f"   Actually Present: {functionality_data['turnstile_present']}")
        print(f"   MCP Turnstile Completed: {mcp_data['findings']['turnstile_completed']}")
        print(f"   Actually Completed: {functionality_data['turnstile_completed']}")
        print(f"   MCP Form Submitted: {mcp_data['findings']['form_submitted']}")
        print(f"   Actually Submitted: {functionality_data['form_submitted']}")
        print(f"   MCP Success Message: {mcp_data['findings']['success_message_found']}")
        print(f"   Actually Found: {functionality_data['success_message_found']}")
        if mcp_data['findings']['success_message_content']:
            print(f"   MCP Captured Message: '{mcp_data['findings']['success_message_content']}'")
            print(f"   Expected Message: '{SUCCESS_MESSAGE}'")
            message_match = SUCCESS_MESSAGE.lower() in mcp_data['findings']['success_message_content'].lower()
            print(f"   Message Content Match: {message_match}")
    
    else:
        print(f"\n🎉 MCP agent successfully completed Turnstile authentication with ≥{MIN_ACCURACY_THRESHOLD*100}% accuracy in all categories!")
    
    return overall_success

def main():
    """Main verification function."""
    try:
        success = verify_task()
        
        if success:
            print("\n🎉 Turnstile authentication task verification: PASSED")
            print("Both Turnstile functionality and MCP agent accuracy meet requirements")
            sys.exit(0)
        else:
            print("\n❌ Turnstile authentication task verification: FAILED")
            print("Either Turnstile functionality or MCP agent accuracy below requirements")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()