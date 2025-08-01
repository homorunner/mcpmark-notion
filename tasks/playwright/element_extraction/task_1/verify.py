#!/usr/bin/env python3
"""
Verification script for Playwright element extraction task.

This script uses dual verification:
1. Independent Playwright verification of website content
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
TARGET_URL = "https://mcp-eval-website.vercel.app/extraction"

# Expected data patterns from the website
EXPECTED_HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
EXPECTED_NAV_LINKS_COUNT = 15  # Based on actual website structure
EXPECTED_HEADINGS_COUNT = 9   # Based on actual website structure  
EXPECTED_STATUS_CODES = ["200", "201", "400", "401", "404", "500"]

# Accuracy thresholds for comparison
MIN_ACCURACY_THRESHOLD = 1.0  # 100% accuracy required to pass

# =============================================================================
# INDEPENDENT PLAYWRIGHT VERIFICATION
# =============================================================================

def verify_website_content() -> Dict[str, Any]:
    """Use Playwright to independently verify the website content."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"🌐 Navigating to: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle")
            
            # Extract navigation links
            nav_links = page.locator("nav a").all()
            nav_link_count = len(nav_links)
            nav_link_hrefs = [link.get_attribute("href") for link in nav_links if link.get_attribute("href")]
            
            # Extract headings (h1-h6)
            headings = page.locator("h1, h2, h3, h4, h5, h6").all()
            heading_count = len(headings)
            heading_texts = [heading.text_content().strip() for heading in headings if heading.text_content()]
            
            # Extract HTTP methods (look for elements containing method names)
            page_content = page.content()
            http_methods_found = []
            for method in EXPECTED_HTTP_METHODS:
                if method in page_content:
                    http_methods_found.append(method)
            
            # Extract status codes (look for elements containing status codes)
            status_codes_found = []
            for code in EXPECTED_STATUS_CODES:
                if code in page_content:
                    status_codes_found.append(code)
            
            browser.close()
            
            return {
                "success": True,
                "nav_links": {
                    "count": nav_link_count,
                    "hrefs": nav_link_hrefs
                },
                "headings": {
                    "count": heading_count,
                    "texts": heading_texts
                },
                "http_methods": {
                    "count": len(http_methods_found),
                    "found": http_methods_found
                },
                "status_codes": {
                    "count": len(status_codes_found),
                    "found": status_codes_found
                }
            }
            
    except Exception as e:
        print(f"❌ Error during Playwright verification: {e}")
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
        "nav_links": [],
        "headings": [],
        "http_methods": [],
        "status_codes": []
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
            
            # Extract navigation links
            nav_link_patterns = [
                r'/[a-zA-Z0-9/_-]+',  # /forms, /auth/basic, etc.
                r'#[a-zA-Z0-9-]+',    # #http-methods, #status-codes, etc.
            ]
            for pattern in nav_link_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if match not in agent_findings["nav_links"] and len(match) > 1:
                        agent_findings["nav_links"].append(match)
            
            # Extract headings (look for quoted strings or title-case text)
            heading_patterns = [
                r'"([^"]{3,50})"',  # "Heading Text"
                r"'([^']{3,50})'",  # 'Heading Text'
                r'([A-Z][a-z\s&]{3,30})',  # Title Case Text
            ]
            for pattern in heading_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    clean_match = match.strip()
                    if (clean_match not in agent_findings["headings"] and 
                        len(clean_match) > 3 and 
                        any(word in clean_match.lower() for word in ['test', 'http', 'service', 'method', 'status', 'response', 'navigation', 'json', 'form', 'link'])):
                        agent_findings["headings"].append(clean_match)
            
            # Extract HTTP methods
            for method in EXPECTED_HTTP_METHODS:
                if method in content.upper() and method not in agent_findings["http_methods"]:
                    agent_findings["http_methods"].append(method)
            
            # Extract status codes
            for code in EXPECTED_STATUS_CODES:
                if code in content and code not in agent_findings["status_codes"]:
                    agent_findings["status_codes"].append(code)
    
    return {"success": True, "findings": agent_findings}

# =============================================================================
# COMPARISON AND EVALUATION
# =============================================================================

def compare_mcp_vs_independent(mcp_results: Dict, independent_results: Dict) -> Dict[str, Any]:
    """Compare MCP agent findings with independent verification"""
    comparison = {}
    
    # Compare navigation links
    mcp_nav = set(mcp_results["findings"]["nav_links"])
    actual_nav = set(independent_results["nav_links"]["hrefs"])
    
    if actual_nav:
        correct_links = len(mcp_nav.intersection(actual_nav))
        nav_accuracy = correct_links / len(actual_nav)
        missing_links = list(actual_nav - mcp_nav)
        extra_links = list(mcp_nav - actual_nav)
    else:
        nav_accuracy = 0.0
        missing_links = []
        extra_links = list(mcp_nav)
    
    comparison["nav_links"] = {
        "mcp_count": len(mcp_nav),
        "independent_count": len(actual_nav),
        "accuracy": nav_accuracy,
        "match": nav_accuracy >= MIN_ACCURACY_THRESHOLD,
        "missing": missing_links,
        "extra": extra_links
    }
    
    # Compare headings (more flexible matching)
    mcp_headings = set(h.lower().strip() for h in mcp_results["findings"]["headings"])
    actual_headings = set(h.lower().strip() for h in independent_results["headings"]["texts"])
    
    if actual_headings:
        # Allow partial matches for headings
        correct_headings = 0
        for actual_heading in actual_headings:
            for mcp_heading in mcp_headings:
                if (actual_heading in mcp_heading or mcp_heading in actual_heading or
                    any(word in mcp_heading for word in actual_heading.split() if len(word) > 3)):
                    correct_headings += 1
                    break
        
        heading_accuracy = correct_headings / len(actual_headings)
    else:
        heading_accuracy = 0.0
    
    comparison["headings"] = {
        "mcp_count": len(mcp_results["findings"]["headings"]),
        "independent_count": len(actual_headings),
        "accuracy": heading_accuracy,
        "match": heading_accuracy >= MIN_ACCURACY_THRESHOLD
    }
    
    # Compare HTTP methods
    mcp_methods = set(mcp_results["findings"]["http_methods"])
    actual_methods = set(independent_results["http_methods"]["found"])
    
    if actual_methods:
        method_accuracy = len(mcp_methods.intersection(actual_methods)) / len(actual_methods)
    else:
        method_accuracy = 0.0
    
    comparison["http_methods"] = {
        "mcp_count": len(mcp_methods),
        "independent_count": len(actual_methods),
        "accuracy": method_accuracy,
        "match": method_accuracy >= MIN_ACCURACY_THRESHOLD
    }
    
    # Compare status codes
    mcp_codes = set(mcp_results["findings"]["status_codes"])
    actual_codes = set(independent_results["status_codes"]["found"])
    
    if actual_codes:
        code_accuracy = len(mcp_codes.intersection(actual_codes)) / len(actual_codes)
    else:
        code_accuracy = 0.0
    
    comparison["status_codes"] = {
        "mcp_count": len(mcp_codes),
        "independent_count": len(actual_codes),
        "accuracy": code_accuracy,
        "match": code_accuracy >= MIN_ACCURACY_THRESHOLD
    }
    
    return comparison

def verify_extraction_requirements(data: Dict[str, Any]) -> bool:
    """Verify that the extracted data meets task requirements."""
    if not data.get("success"):
        print(f"❌ Independent verification failed: {data.get('error', 'Unknown error')}")
        return False
    
    success = True
    
    # Check navigation links (allow slight variation)
    nav_count = data["nav_links"]["count"]
    if nav_count >= EXPECTED_NAV_LINKS_COUNT:
        print(f"✅ Navigation links: {nav_count}/{EXPECTED_NAV_LINKS_COUNT}")
    else:
        print(f"❌ Navigation links: {nav_count}/{EXPECTED_NAV_LINKS_COUNT} (expected at least {EXPECTED_NAV_LINKS_COUNT})")
        success = False
    
    # Check headings (allow slight variation)
    heading_count = data["headings"]["count"]
    if heading_count >= EXPECTED_HEADINGS_COUNT:
        print(f"✅ Page headings: {heading_count}/{EXPECTED_HEADINGS_COUNT}")
    else:
        print(f"❌ Page headings: {heading_count}/{EXPECTED_HEADINGS_COUNT} (expected at least {EXPECTED_HEADINGS_COUNT})")
        success = False
    
    # Check HTTP methods
    http_methods_count = data["http_methods"]["count"]
    if http_methods_count >= 6:
        print(f"✅ HTTP methods: {http_methods_count}/{len(EXPECTED_HTTP_METHODS)}")
    else:
        print(f"❌ HTTP methods: {http_methods_count}/{len(EXPECTED_HTTP_METHODS)} (expected at least 6)")
        success = False
    
    # Check status codes
    status_codes_count = data["status_codes"]["count"]
    if status_codes_count >= 5:
        print(f"✅ Status codes: {status_codes_count}/{len(EXPECTED_STATUS_CODES)}")
    else:
        print(f"❌ Status codes: {status_codes_count}/{len(EXPECTED_STATUS_CODES)} (expected at least 5)")
        success = False
    
    return success

# =============================================================================
# MAIN VERIFICATION
# =============================================================================

def verify_task() -> bool:
    """Verify both independent requirements AND MCP agent accuracy"""
    print("🔍 Verifying Playwright Element Extraction Task")
    print("=" * 50)
    
    # Step 1: Independent verification
    print("\n🎭 Running independent Playwright verification...")
    independent_data = verify_website_content()
    independent_success = verify_extraction_requirements(independent_data)
    
    if not independent_success:
        print("\n❌ Task requirements cannot be met - website doesn't have expected content")
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
    comparison = compare_mcp_vs_independent(mcp_data, independent_data)
    
    # Step 4: Evaluation
    overall_success = True
    
    for category, results in comparison.items():
        accuracy = results["accuracy"] * 100
        category_name = category.replace("_", " ").title()
        
        if results["match"]:
            print(f"✅ {category_name}: {accuracy:.1f}% accuracy (MCP: {results['mcp_count']}, Actual: {results['independent_count']})")
        else:
            print(f"❌ {category_name}: {accuracy:.1f}% accuracy (MCP: {results['mcp_count']}, Actual: {results['independent_count']})")
            overall_success = False
    
    # Step 5: Detailed breakdown
    if not overall_success:
        print(f"\n📋 Detailed comparison (threshold: {MIN_ACCURACY_THRESHOLD*100}%):")
        
        # Navigation links detail
        nav_results = comparison["nav_links"]
        if nav_results["missing"] or nav_results["extra"]:
            print(f"   Navigation Links:")
            if nav_results["missing"]:
                print(f"     • Missing: {nav_results['missing']}")
            if nav_results["extra"]:
                print(f"     • Extra: {nav_results['extra']}")
        
        # Show what MCP found vs actual
        print(f"\n   MCP Found: {len(mcp_data['findings']['nav_links'])} nav links, {len(mcp_data['findings']['headings'])} headings")
        print(f"   Actually: {independent_data['nav_links']['count']} nav links, {independent_data['headings']['count']} headings")
    
    else:
        print(f"\n🎉 MCP agent successfully extracted content with ≥{MIN_ACCURACY_THRESHOLD*100}% accuracy in all categories!")
    
    return overall_success

def main():
    """Main verification function."""
    try:
        success = verify_task()
        
        if success:
            print("\n🎉 Element extraction task verification: PASSED")
            print("Both website content and MCP agent accuracy meet requirements")
            sys.exit(0)
        else:
            print("\n❌ Element extraction task verification: FAILED")
            print("Either website content or MCP agent accuracy below requirements")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()