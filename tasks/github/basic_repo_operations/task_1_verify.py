#!/usr/bin/env python3
"""
Verification script for GitHub Task 1: Repository Creation
"""

import os
import requests
import sys
from typing import Optional

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
    
    # Check repository properties
    checks = [
        ("Repository name", repo_data.get("name") == repo_name, f"Expected: {repo_name}, Got: {repo_data.get('name')}"),
        ("Repository description", "MCPBench测试仓库" in (repo_data.get("description") or ""), f"Description: {repo_data.get('description')}"),
        ("Repository is public", not repo_data.get("private", True), f"Private: {repo_data.get('private')}"),
        ("Has Issues enabled", repo_data.get("has_issues", False), f"Has issues: {repo_data.get('has_issues')}"),
    ]
    
    all_passed = True
    for check_name, condition, detail in checks:
        if condition:
            print(f"✅ {check_name}: PASS")
        else:
            print(f"❌ {check_name}: FAIL - {detail}")
            all_passed = False
    
    # Check for README.md file
    readme_response = requests.get(f"https://api.github.com/repos/{owner}/{repo_name}/readme", headers=headers)
    if readme_response.status_code == 200:
        print("✅ README.md file exists: PASS")
    else:
        print("❌ README.md file missing: FAIL")
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
    repo_name = "mcpbench-test-repo"
    success = verify_repository_exists(token, owner, repo_name)
    
    if success:
        print("\n🎉 Task 1 verification: PASS")
        print(f"Repository {owner}/{repo_name} created successfully with correct configuration")
        sys.exit(0)
    else:
        print("\n❌ Task 1 verification: FAIL")
        print("Repository was not created correctly or is missing required configuration")
        sys.exit(1)

if __name__ == "__main__":
    main() 