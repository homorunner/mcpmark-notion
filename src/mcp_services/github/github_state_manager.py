#!/usr/bin/env python3
"""
GitHub State Manager for MCPBench
=================================

This module handles GitHub repository state management for consistent task evaluation.
Manages test repositories, branches, and cleanup after evaluation.
"""

import os
import requests
from typing import Optional, Dict, Any
from pathlib import Path

from src.base.state_manager import BaseStateManager
from src.base.task_manager import BaseTask
from src.logger import get_logger

logger = get_logger(__name__)


class GitHubStateManager(BaseStateManager):
    """
    Manages GitHub repository state for task evaluation.
    """

    def __init__(
        self,
        github_token: str,
        base_repo_owner: str = "mcpbench",
        test_org: str = "mcpbench-eval",
        test_repo_prefix: str = "test-",
    ):
        """
        Initialize GitHub state manager.
        
        Args:
            github_token: GitHub Personal Access Token
            base_repo_owner: Owner of base template repositories
            test_org: Organization for test repositories
            test_repo_prefix: Prefix for test repository names
        """
        super().__init__()
        
        self.github_token = github_token
        self.base_repo_owner = base_repo_owner
        self.test_org = test_org
        self.test_repo_prefix = test_repo_prefix
        
        # Set up HTTP session with GitHub API headers
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MCPBench/1.0"
        })
        
        # Store created resources for cleanup
        self.created_resources = []

    def initialize(self, **kwargs):
        """Initialize GitHub environment and validate credentials."""
        try:
            # Validate GitHub token and get user info
            response = self.session.get("https://api.github.com/user")
            if response.status_code != 200:
                raise ValueError(f"Invalid GitHub token: {response.status_code} {response.text}")
            
            user_info = response.json()
            logger.info(f"GitHub authenticated as: {user_info['login']}")
            
            # Check if test organization exists (optional)
            if self.test_org:
                org_response = self.session.get(f"https://api.github.com/orgs/{self.test_org}")
                if org_response.status_code == 200:
                    logger.info(f"Using test organization: {self.test_org}")
                else:
                    logger.warning(f"Test organization {self.test_org} not accessible, using user account")
                    # Fall back to user account
                    self.test_org = user_info['login']
            
            return True
            
        except Exception as e:
            logger.error(f"GitHub initialization failed: {e}")
            return False

    def set_up(self, task: BaseTask) -> bool:
        """
        Set up GitHub environment for a specific task.
        
        This may involve:
        1. Creating/forking test repositories
        2. Setting up branches
        3. Creating issues or PRs if needed
        """
        try:
            logger.info(f"Setting up GitHub state for task: {task.name}")
            
            # For basic file operations, we might create a test repository
            if self._task_needs_repo(task):
                repo_name = f"{self.test_repo_prefix}{task.category}-{task.task_id}"
                repo_url = self._create_or_get_test_repo(repo_name, task.category)
                
                if hasattr(task, 'repository_url'):
                    task.repository_url = repo_url
                
                # Store for cleanup
                self.created_resources.append({
                    'type': 'repository',
                    'name': repo_name,
                    'owner': self.test_org
                })
                
                logger.info(f"Created/configured test repository: {repo_url}")
            
            # Set up branch if needed
            if self._task_needs_branch(task):
                branch_name = f"task-{task.category}-{task.task_id}"
                if hasattr(task, 'repository_url') and hasattr(task, 'branch_name'):
                    self._create_branch(task.repository_url, branch_name)
                    task.branch_name = branch_name
                    logger.info(f"Created branch: {branch_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"GitHub setup failed for {task.name}: {e}")
            return False

    def clean_up(self, task=None, **kwargs) -> bool:
        """Clean up GitHub resources created during task execution."""
        try:
            cleanup_success = True
            
            for resource in self.created_resources:
                try:
                    if resource['type'] == 'repository':
                        # 默认删除测试仓库，而不是归档
                        if kwargs.get('archive_only', False):
                            self._archive_repository(resource['owner'], resource['name'])
                            logger.info(f"Archived repository: {resource['owner']}/{resource['name']}")
                        else:
                            self._delete_repository(resource['owner'], resource['name'])
                            logger.info(f"Deleted repository: {resource['owner']}/{resource['name']}")
                        
                except Exception as e:
                    logger.error(f"Failed to cleanup {resource}: {e}")
                    cleanup_success = False
            
            # Clear the resources list
            self.created_resources.clear()
            
            return cleanup_success
            
        except Exception as e:
            logger.error(f"GitHub cleanup failed: {e}")
            return False

    def _task_needs_repo(self, task: BaseTask) -> bool:
        """Determine if a task needs a test repository."""
        # For basic repo operations (like creating repos), we don't need pre-setup
        # The task itself will create the repository
        if task.category == 'basic_repo_operations':
            return False
        
        # Other categories that might need repos
        repo_categories = ['file_operations', 'branch_management', 'issue_management', 'pull_request_workflow']
        return task.category in repo_categories

    def _task_needs_branch(self, task: BaseTask) -> bool:
        """Determine if a task needs a separate branch."""
        branch_categories = ['branch_management', 'pull_requests']
        return task.category in branch_categories

    def _create_or_get_test_repo(self, repo_name: str, category: str) -> str:
        """Create or get a test repository for the task."""
        # Check if repository already exists
        repo_url = f"https://api.github.com/repos/{self.test_org}/{repo_name}"
        response = self.session.get(repo_url)
        
        if response.status_code == 200:
            logger.info(f"Repository {repo_name} already exists")
            return response.json()['html_url']
        
        # Create new repository
        create_data = {
            "name": repo_name,
            "description": f"Test repository for MCPBench {category} tasks",
            "private": True,  # Keep test repos private
            "auto_init": True,  # Initialize with README
            "has_issues": True,
            "has_projects": True,
            "has_wiki": False,
        }
        
        # If using organization, create in org; otherwise create in user account
        if self.test_org and self.test_org != self._get_authenticated_user():
            create_url = f"https://api.github.com/orgs/{self.test_org}/repos"
        else:
            create_url = "https://api.github.com/user/repos"
        
        response = self.session.post(create_url, json=create_data)
        
        if response.status_code in [200, 201]:
            repo_data = response.json()
            logger.info(f"Created repository: {repo_data['html_url']}")
            return repo_data['html_url']
        else:
            raise Exception(f"Failed to create repository: {response.status_code} {response.text}")

    def _create_branch(self, repo_url: str, branch_name: str):
        """Create a new branch in the repository."""
        # Extract owner and repo name from URL
        parts = repo_url.replace('https://github.com/', '').split('/')
        owner, repo = parts[0], parts[1]
        
        # Get the current main branch SHA
        main_ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/main"
        response = self.session.get(main_ref_url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get main branch ref: {response.text}")
        
        main_sha = response.json()['object']['sha']
        
        # Create new branch
        create_branch_data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": main_sha
        }
        
        create_ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
        response = self.session.post(create_ref_url, json=create_branch_data)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create branch: {response.text}")

    def _archive_repository(self, owner: str, repo_name: str):
        """Archive a repository instead of deleting it."""
        archive_url = f"https://api.github.com/repos/{owner}/{repo_name}"
        archive_data = {"archived": True}
        
        response = self.session.patch(archive_url, json=archive_data)
        if response.status_code not in [200, 201]:
            logger.warning(f"Failed to archive repository {owner}/{repo_name}: {response.text}")

    def _delete_repository(self, owner: str, repo_name: str):
        """Delete a repository (use with caution)."""
        delete_url = f"https://api.github.com/repos/{owner}/{repo_name}"
        response = self.session.delete(delete_url)
        
        if response.status_code not in [200, 204]:
            logger.warning(f"Failed to delete repository {owner}/{repo_name}: {response.text}")
            raise Exception(f"Failed to delete repository {owner}/{repo_name}: {response.status_code} {response.text}")
        else:
            logger.info(f"Successfully deleted repository {owner}/{repo_name}")

    def _get_authenticated_user(self) -> str:
        """Get the username of the authenticated user."""
        response = self.session.get("https://api.github.com/user")
        if response.status_code == 200:
            return response.json()['login']
        return None

    # Utility methods for common GitHub operations during task setup
    def create_issue(self, repo_owner: str, repo_name: str, title: str, body: str = "") -> Optional[int]:
        """Create an issue in the specified repository."""
        issue_data = {
            "title": title,
            "body": body
        }
        
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
        response = self.session.post(url, json=issue_data)
        
        if response.status_code in [200, 201]:
            issue = response.json()
            self.created_resources.append({
                'type': 'issue',
                'repo': f"{repo_owner}/{repo_name}",
                'number': issue['number']
            })
            return issue['number']
        
        logger.error(f"Failed to create issue: {response.text}")
        return None

    def create_pull_request(self, repo_owner: str, repo_name: str, title: str, head: str, base: str = "main", body: str = "") -> Optional[int]:
        """Create a pull request in the specified repository."""
        pr_data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body
        }
        
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
        response = self.session.post(url, json=pr_data)
        
        if response.status_code in [200, 201]:
            pr = response.json()
            self.created_resources.append({
                'type': 'pull_request',
                'repo': f"{repo_owner}/{repo_name}",
                'number': pr['number']
            })
            return pr['number']
        
        logger.error(f"Failed to create pull request: {response.text}")
        return None 

    def track_created_repository(self, repo_name: str, owner: str = None):
        """追踪任务执行过程中创建的仓库（例如通过MCP工具）"""
        if not owner:
            owner = self._get_authenticated_user()
        
        self.created_resources.append({
            'type': 'repository',
            'name': repo_name,
            'owner': owner,
            'created_by': 'mcp_task'  # 标记为MCP任务创建
        })
        logger.info(f"Tracking repository for cleanup: {owner}/{repo_name}")

    def get_test_repositories(self) -> list:
        """获取所有被追踪的测试仓库列表"""
        return [r for r in self.created_resources if r['type'] == 'repository']

    def force_cleanup_test_repos(self, pattern: str = "mcpbench-test-") -> bool:
        """强制清理所有匹配模式的测试仓库"""
        user = self._get_authenticated_user()
        if not user:
            logger.error("Cannot get authenticated user for cleanup")
            return False
        
        success = True
        # Get user's repositories
        repos_url = f"https://api.github.com/user/repos?per_page=100"
        response = self.session.get(repos_url)
        
        if response.status_code != 200:
            logger.error(f"Failed to get user repositories: {response.text}")
            return False
        
        repos = response.json()
        
        for repo in repos:
            if pattern in repo['name']:
                try:
                    self._delete_repository(repo['owner']['login'], repo['name'])
                    logger.info(f"Force deleted test repository: {repo['full_name']}")
                except Exception as e:
                    logger.error(f"Failed to force delete {repo['full_name']}: {e}")
                    success = False
        
        return success 