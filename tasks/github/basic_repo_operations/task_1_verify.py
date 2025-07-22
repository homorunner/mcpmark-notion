#!/usr/bin/env python3
"""
Verification script for GitHub Task 1: Repository Creation
"""

import os
import requests
import sys
from typing import Optional

# =============================================================================
# CONFIGURATION - Key fields that may need to be modified
# =============================================================================

# Repository configuration
REPO_NAME = "mcpbench-test-repo"
EXPECTED_DESCRIPTION_KEYWORD = "MCPBench测试仓库"

# Repository property checks configuration
REPO_CHECKS = [
    ("Repository is public", lambda repo: not repo.get("private", True), "private"),
    ("Has Issues enabled", lambda repo: repo.get("has_issues", False), "has_issues"),
]

# Required files to check
REQUIRED_FILES = ["README.md"]

# =============================================================================
# IMPLEMENTATION
# =============================================================================

def get_github_token() -> Optional[str]:
    """Get GitHub token from environment variables."""
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".mcp_env")
    return os.getenv("GITHUB_TOKEN")

def verify_repository_exists(token: str, owner: str, repo_name: str) -> bool:
    """Verify that the repository exists and has correct configuration."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    # Get repository information
    response = requests.get(f"https://api.github.com/repos/{owner}/{repo_name}", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Repository {owner}/{repo_name} not found")
        return False
    
    repo_data = response.json()
    
    # Check basic repository properties
    basic_checks = [
        ("Repository name", repo_data.get("name") == repo_name, f"Expected: {repo_name}, Got: {repo_data.get('name')}"),
        ("Repository description", EXPECTED_DESCRIPTION_KEYWORD in (repo_data.get("description") or ""), f"Description: {repo_data.get('description')}"),
    ]
    
    all_passed = True
    
    # Run basic checks
    for check_name, condition, detail in basic_checks:
        if condition:
            print(f"✅ {check_name}: PASS")
        else:
            print(f"❌ {check_name}: FAIL - {detail}")
            all_passed = False
    
    # Run configurable repository checks
    for check_name, check_func, field_name in REPO_CHECKS:
        condition = check_func(repo_data)
        if condition:
            print(f"✅ {check_name}: PASS")
        else:
            print(f"❌ {check_name}: FAIL - {field_name}: {repo_data.get(field_name)}")
            all_passed = False
    
    # Check for required files
    for file_name in REQUIRED_FILES:
        file_response = requests.get(f"https://api.github.com/repos/{owner}/{repo_name}/contents/{file_name}", headers=headers)
        if file_response.status_code == 200:
            print(f"✅ {file_name} file exists: PASS")
        else:
            print(f"❌ {file_name} file missing: FAIL")
            all_passed = False
    
    return all_passed

def get_authenticated_user(token: str) -> Optional[str]:
    """Get the authenticated user's username."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get("https://api.github.com/user", headers=headers)
    if response.status_code == 200:
        return response.json().get("login")
    return None

def main():
    """Main verification function."""
    print("🔍 Verifying GitHub Task 1: Repository Creation")
    print("=" * 50)
    
    # Get GitHub token
    token = get_github_token()
    if not token:
        print("❌ GitHub token not found in .mcp_env file")
        sys.exit(1)
    
    # Get authenticated user
    owner = get_authenticated_user(token)
    if not owner:
        print("❌ Failed to get authenticated user information")
        sys.exit(1)
    
    print(f"🔍 Checking repository for user: {owner}")
    
    # Verify repository
    success = verify_repository_exists(token, owner, REPO_NAME)
    
    if success:
        print("\n🎉 Task 1 verification: PASS")
        print(f"Repository {owner}/{REPO_NAME} created successfully with correct configuration")
        sys.exit(0)
    else:
        print("\n❌ Task 1 verification: FAIL")
        print("Repository was not created correctly or is missing required configuration")
        sys.exit(1)

if __name__ == "__main__":
    main() 