#!/usr/bin/env python3
"""
Verification script for Playwright form interaction task.

Verifies that the MCP agent successfully submitted the form and reached 
the result page with correct data.
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any

# Expected form data from task description
EXPECTED_DATA = {
    "customer_name": "John Doe",
    "phone_number": "123-456-7890",
    "email_address": "john.doe@example.com",
    "size": "large",  # Backend normalizes to lowercase  
    "delivery_time": "afternoon",  # Backend normalizes to lowercase
    "comments": "This is a test submission for MCPBench"
}

def parse_mcp_results() -> Dict[str, Any]:
    """Check if MCP agent reached result page and verify data."""
    messages_file = Path.cwd() / "messages.json"
    if not messages_file.exists():
        return {"success": False, "error": "No messages.json found"}
    
    try:
        with open(messages_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"Failed to read messages.json: {e}"}
    
    # Look for evidence of reaching result page with correct URL pattern
    result_url_found = False
    submission_id = None
    
    for message in messages:
        if message.get("type") == "function_call_output":
            output = str(message.get("output", ""))
            
            # Check for result page URL in browser outputs
            if "/forms/result/" in output:
                match = re.search(r'/forms/result/(\d+)', output)
                if match:
                    result_url_found = True
                    submission_id = int(match.group(1))
                    break
    
    if not result_url_found:
        return {"success": False, "error": "Agent did not reach result page"}
    
    # If we reached result page, try to validate the data shown
    data_validation = validate_result_data_from_messages(messages)
    
    return {
        "success": True,
        "submission_id": submission_id,
        "data_validation": data_validation
    }

def validate_result_data_from_messages(messages) -> Dict[str, Any]:
    """Extract and validate result page data from agent's messages."""
    # Look for result page content in browser snapshots or outputs
    result_content = ""
    
    for message in messages:
        if message.get("type") == "function_call_output":
            output = str(message.get("output", ""))
            if "submission" in output.lower() and ("john doe" in output.lower() or "customer name" in output.lower()):
                result_content = output
                break
    
    if not result_content:
        return {"success": False, "error": "No result page data found in agent messages"}
    
    # Extract data using patterns
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
        match = re.search(pattern, result_content, re.IGNORECASE)
        if match:
            extracted_data[key] = match.group(1).strip()
    
    # Compare with expected data
    data_matches = {}
    for key, expected_value in EXPECTED_DATA.items():
        actual_value = extracted_data.get(key, "").lower().strip()
        expected_lower = expected_value.lower().strip()
        data_matches[key] = actual_value == expected_lower
    
    return {
        "success": True,
        "extracted_data": extracted_data,
        "data_matches": data_matches,
        "all_correct": all(data_matches.values())
    }

def verify_task() -> bool:
    """Main verification function."""
    print("🔍 Verifying Playwright Form Interaction Task")
    print("=" * 50)
    
    # Parse MCP agent results
    print("🤖 Checking MCP agent results...")
    mcp_result = parse_mcp_results()
    
    if not mcp_result["success"]:
        print(f"❌ {mcp_result.get('error')}")
        return False
    
    print(f"✅ Agent reached result page with submission ID: {mcp_result['submission_id']}")
    
    # Check data validation
    data_validation = mcp_result["data_validation"]
    if not data_validation["success"]:
        print(f"❌ Data validation failed: {data_validation.get('error')}")
        return False
    
    if data_validation["all_correct"]:
        print("✅ All submitted data appears correctly on result page")
        return True
    else:
        print("❌ Some submitted data is incorrect:")
        for field, matches in data_validation["data_matches"].items():
            status = "✅" if matches else "❌"
            expected = EXPECTED_DATA[field]
            actual = data_validation["extracted_data"].get(field, "NOT FOUND")
            print(f"   {status} {field}: expected '{expected}', got '{actual}'")
        return False

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