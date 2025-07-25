#!/usr/bin/env python3
"""
GitHub State Manager for MCPBench
=================================

This module handles GitHub repository state management for consistent task evaluation.
Manages test repositories, branches, and cleanup after evaluation.
"""

import requests
from typing import Optional, Dict, Any

from src.base.state_manager import BaseStateManager, InitialStateInfo
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
        # Name of the evaluation organisation / user where temporary test repositories are created
        eval_org: str = "MCPLeague-Eval",
        # Prefix for evaluation repositories that will be created during tasks
        eval_repo_prefix: str = "eval-",
        # Organisation / user that hosts the immutable template (initial-state) repositories
        source_org: str = "MCPLeague-Source",
    ):
        """
        Initialize GitHub state manager.
        
        Args:
            github_token: GitHub Personal Access Token used for *all* API calls.
            eval_org: Organisation / user used to host **ephemeral evaluation repositories**.
            eval_repo_prefix: Prefix for names of the evaluation repositories that will be created.
            source_org: Organisation / user that contains **read-only template repositories** (initial state).
        """
        super().__init__(service_name="github")
        
        # List to track resources (repositories, issues, PRs) created during a task for cleanup
        self.created_resources: list[dict[str, Any]] = []

        self.github_token = github_token

        # Store evaluation context (consistent naming)
        self.eval_org = eval_org  # evaluation organisation / user
        self.eval_repo_prefix = eval_repo_prefix
        self.source_org = source_org
        
        # Set up HTTP session for GitHub API
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MCPBench/1.0"
        })
        
        # Validate GitHub configuration during initialization
        try:
            response = self.session.get("https://api.github.com/user")
            if response.status_code != 200:
                raise ValueError(f"Invalid GitHub token: {response.status_code} {response.text}")
            
            user_info = response.json()
            logger.info(f"GitHub authenticated as: {user_info['login']}")
            
            # Check if evaluation organisation exists (optional)
            if self.eval_org:
                org_response = self.session.get(f"https://api.github.com/orgs/{self.eval_org}")
                if org_response.status_code == 200:
                    logger.info(f"Using evaluation organisation: {self.eval_org}")
                else:
                    logger.warning(f"Evaluation organisation {self.eval_org} not accessible, using user account")
                    # Fall back to user account
                    self.eval_org = user_info['login']
            
            logger.info("GitHub state manager initialized successfully")
            
        except Exception as e:
            raise RuntimeError(f"GitHub initialization failed: {e}")
        
        # Initial state mapping - categories to initial state repositories
        self.initial_state_mapping = {
            "basic_repo_operations": None,  # Basic operations don't need initial state, create empty repo
            "file_operations": "empty-repo",  # Use arvinxx/empty-repo as base initial state
            "issue_management": "empty-repo",  # Currently all use empty-repo, can be extended later
            "pull_request_workflow": "empty-repo", 
            "branch_management": "empty-repo",
            "complex_workflows": "empty-repo"
        }

    # =========================================================================
    # Core Template Methods (Required by BaseStateManager)
    # =========================================================================

    def _create_initial_state(self, task) -> Optional[InitialStateInfo]:
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
                repo_name = f"{self.eval_repo_prefix}{task.category}-{task.task_id}"
                repo_url = self._create_or_get_test_repo(repo_name, task.category)
                
                if hasattr(task, 'repository_url'):
                    task.repository_url = repo_url
                
                # Store for cleanup
                self.created_resources.append({
                    'type': 'repository',
                    'name': repo_name,
                    'owner': self.eval_org
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
                        # By default, delete test repositories instead of archiving them
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

    # =========================================================================
    # Task Requirements Analysis
    # =========================================================================
    
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

    # =========================================================================
    # Repository Creation and Setup Operations
    # =========================================================================
    
    def _create_or_get_test_repo(self, repo_name: str, category: str) -> str:
        """Create or get a test repository for the task."""
        # Check if repository already exists
        repo_url = f"https://api.github.com/repos/{self.eval_org}/{repo_name}"
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
        
        # Select correct endpoint based on whether we are using evaluation org
        create_url = self._repo_create_endpoint()
        
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

    # ---------------------------------------------------------------------
    # Helper utilities (organisation vs user)
    # ---------------------------------------------------------------------

    def _get_authenticated_user(self) -> str:
        """Return cached authenticated username or fetch once from GitHub."""
        if hasattr(self, "_auth_user") and self._auth_user:
            return self._auth_user

        response = self.session.get("https://api.github.com/user")
        if response.status_code == 200:
            self._auth_user = response.json()["login"]
            return self._auth_user
        return None

    def _using_test_org(self) -> bool:
        """Whether we're operating in a separate evaluation organisation."""
        auth_user = self._get_authenticated_user()
        return bool(self.eval_org and auth_user and self.eval_org != auth_user)

    def _repo_create_endpoint(self) -> str:
        """Return correct REST endpoint for creating repositories (org or user)."""
        if self._using_test_org():
            return f"https://api.github.com/orgs/{self.eval_org}/repos"
        return "https://api.github.com/user/repos"

    # =========================================================================
    # GitHub API Utility Methods
    # =========================================================================
    
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

    # =========================================================================
    # Resource Tracking and Cleanup Management
    # =========================================================================
    
    def track_created_repository(self, repo_name: str, owner: str = None):
        """Track repositories created during task execution (e.g., via MCP tools)"""
        if not owner:
            owner = self._get_authenticated_user()
        
        self.created_resources.append({
            'type': 'repository',
            'name': repo_name,
            'owner': owner,
            'created_by': 'mcp_task'  # Marked as created by MCP task
        })
        logger.info(f"Tracking repository for cleanup: {owner}/{repo_name}")

    def get_test_repositories(self) -> list:
        """Return a list of all tracked test repositories"""
        return [r for r in self.created_resources if r['type'] == 'repository']
    
    # =========================================================================
    # Legacy Task Setup Methods (can be deprecated)
    # =========================================================================

    def set_up(self, task) -> bool:
        """Create initial state for GitHub task."""
        try:
            repo_url = self.create_initial_state_for_task(str(task.task_id), task.category)
            if not repo_url:
                return None
            
            # Extract repo info for tracking
            owner, repo_name = self.extract_repo_info_from_url(repo_url)
            
            return InitialStateInfo(
                state_id=f"{owner}/{repo_name}",
                state_url=repo_url,
                metadata={
                    'owner': owner,
                    'repo_name': repo_name,
                    'category': task.category,
                    'task_id': task.task_id
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create GitHub initial state for {task.name}: {e}")
            return None
    
    def _store_initial_state_info(self, task, state_info: InitialStateInfo) -> None:
        """Store initial state information in task object."""
        if hasattr(task, 'repository_url'):
            task.repository_url = state_info.state_url
        
        # Track the repository for cleanup
        self.track_resource('repository', state_info.state_id, state_info.metadata)
    
    def _cleanup_task_initial_state(self, task) -> bool:
        """Clean up initial state for a specific GitHub task."""
        if hasattr(task, 'repository_url') and task.repository_url:
            try:
                owner, repo_name = self.extract_repo_info_from_url(task.repository_url)
                # Default to deletion (can be configurable later if needed)
                self._delete_repository(owner, repo_name)
                logger.info(f"Deleted repository: {owner}/{repo_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to cleanup repository for {task.name}: {e}")
                return False
        return True
    
    def _cleanup_single_resource(self, resource: Dict[str, Any]) -> bool:
        """Clean up a single GitHub resource."""
        if resource['type'] == 'repository':
            try:
                repo_id = resource['id']  # format: "owner/repo_name"
                owner, repo_name = repo_id.split('/', 1)
                
                # Default to deletion for simplicity
                self._delete_repository(owner, repo_name)
                logger.info(f"Deleted repository: {owner}/{repo_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to cleanup repository {resource['id']}: {e}")
                return False
        
        logger.warning(f"Unknown resource type for cleanup: {resource['type']}")
        return False
    
    # =========================================================================
    # Initial State Selection and Repository Creation
    # =========================================================================
    
    def select_initial_state_for_task(self, task_category: str) -> Optional[str]:
        """Select appropriate initial state repository for task category."""
        return self.initial_state_mapping.get(task_category)
    
    def create_initial_state_for_task(self, task_id: str, task_category: str) -> Optional[str]:
        """Create initial state for task - unified entry point."""
        initial_state_name = self.select_initial_state_for_task(task_category)
        
        try:
            if initial_state_name and self._can_fork_initial_state(initial_state_name):
                # If initial state exists and can be forked, use fork mechanism
                return self.fork_initial_state(initial_state_name, task_id, task_category)
            else:
                # Otherwise create basic test repository
                logger.info(f"Creating new test repository for {task_category} task (initial state not forkable)")
                return self.create_test_repo_with_content(task_id, task_category)
                
        except Exception as e:
            logger.error(f"Failed to create initial state for task {task_id}: {e}")
            # Fallback: create basic repository
            try:
                logger.info("Falling back to creating basic test repository...")
                return self.create_test_repo_with_content(task_id, task_category)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return None
    
    def fork_initial_state(self, initial_state_name: str, task_id: str, task_category: str) -> str:
        """Fork initial state repository to user account and rename."""
        try:
            # 1. Fork initial state repository
            fork_url = f"https://api.github.com/repos/{self.source_org}/{initial_state_name}/forks"

            # Fork to organisation if needed
            fork_payload: dict[str, Any]
            if self._using_test_org():
                fork_payload = {"organization": self.eval_org}
            else:
                fork_payload = {}

            response = self.session.post(fork_url, json=fork_payload)
            
            if response.status_code not in [200, 202]:
                raise Exception(f"Failed to fork initial state {initial_state_name}: {response.status_code} {response.text}")
            
            fork_data = response.json()
            original_name = fork_data['name']
            owner = fork_data['owner']['login']
            
            logger.info(f"Forked initial state {initial_state_name} to {owner}/{original_name}")
            
            # Note: Resource tracking is handled by the base class template methods
            
            # 2. Generate test repository name
            new_name = self._generate_test_repo_name(task_id, task_category)
            
            # 3. Rename to test repository name
            if new_name != original_name:
                rename_success = self._rename_repository(owner, original_name, new_name)
                if rename_success:
                    logger.info(f"Renamed repository to {owner}/{new_name}")
                    # Update tracked resource
                    for resource in self.tracked_resources:
                        if resource['id'] == f"{owner}/{original_name}":
                            resource['id'] = f"{owner}/{new_name}"
                            resource['metadata']['name'] = new_name
                    return f"https://github.com/{owner}/{new_name}"
                else:
                    logger.warning(f"Failed to rename repository, using original name: {owner}/{original_name}")
            
            return fork_data['html_url']
            
        except Exception as e:
            logger.error(f"Failed to fork initial state {initial_state_name}: {e}")
            raise
    
    def create_test_repo_with_content(self, task_id: str, task_category: str) -> str:
        """Create test repository with initial content, replacing empty initial state fork."""
        try:
            repo_name = self._generate_test_repo_name(task_id, task_category)
            
            # Customize repository content based on task category
            create_data = {
                "name": repo_name,
                "description": f"MCPBench test repository for {task_category} task {task_id}",
                "private": False,  # Set test repos as public
                "auto_init": True,  # Auto-create README
                "has_issues": True,
                "has_projects": False,
                "has_wiki": False
            }
            
            # Add different initial content for different task types
            if task_category in ['issue_management', 'pull_request_workflow']:
                create_data["has_issues"] = True
                create_data["has_projects"] = True
            
            # Choose the correct endpoint (org vs user)
            create_url = self._repo_create_endpoint()
            response = self.session.post(create_url, json=create_data)
            
            if response.status_code in [200, 201]:
                repo_data = response.json()
                repo_url = repo_data['html_url']
                owner = repo_data['owner']['login']
                
                logger.info(f"Created test repository: {repo_url}")

                # Track the repository so that `clean_up` can remove it later
                self.created_resources.append({
                    'type': 'repository',
                    'name': repo_name,
                    'owner': owner
                })
                # Also track via the base class mechanism for consistency
                self.track_resource('repository', f"{owner}/{repo_name}", {
                    'created_by': 'create_test_repo_with_content',
                    'task_category': task_category,
                    'task_id': task_id
                })
                
                # Add initial content for specific task types
                if task_category != 'basic_repo_operations':
                    self._setup_initial_content(owner, repo_name, task_category)
                
                return repo_url
            else:
                raise Exception(f"Failed to create repository: {response.status_code} {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to create test repository with content: {e}")
            raise
    
    # =========================================================================
    # Initial State Validation and Forking Operations
    # =========================================================================
    
    def _can_fork_initial_state(self, initial_state_name: str) -> bool:
        """Check if initial state repository can be forked (i.e., has Git content)."""
        try:
            # Check initial state repository commits
            commits_url = f"https://api.github.com/repos/{self.source_org}/{initial_state_name}/commits"
            response = self.session.get(commits_url)
            
            if response.status_code == 200:
                commits = response.json()
                return len(commits) > 0  # Can only fork if has commits
            elif response.status_code == 409:
                # 409 indicates empty repository
                logger.info(f"Initial state {initial_state_name} is empty and cannot be forked")
                return False
            else:
                logger.warning(f"Cannot check commits for initial state {initial_state_name}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to check if initial state {initial_state_name} can be forked: {e}")
            return False
    
    # =========================================================================
    # Repository Naming and Content Setup Utilities
    # =========================================================================
    
    def _generate_test_repo_name(self, task_id: str, task_category: str) -> str:
        """Generate test repository name."""
        from datetime import datetime
        # Use an ISO-like timestamp (UTC) for easier readability, e.g. 20250725T153024Z
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        return f"mcpleague-test-{timestamp}-{task_category}-task-{task_id}".replace("_", "-")
    
    def _rename_repository(self, owner: str, old_name: str, new_name: str) -> bool:
        """Rename repository."""
        try:
            rename_url = f"https://api.github.com/repos/{owner}/{old_name}"
            rename_data = {"name": new_name}
            
            response = self.session.patch(rename_url, json=rename_data)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to rename repository {owner}/{old_name} to {new_name}: {e}")
            return False
    
    def extract_repo_info_from_url(self, repo_url: str) -> tuple[str, str]:
        """Extract owner and repo name from GitHub URL."""
        try:
            from urllib.parse import urlparse
            # Support https://github.com/owner/repo format
            if "github.com" in repo_url:
                path = urlparse(repo_url).path.strip('/')
                parts = path.split('/')
                if len(parts) >= 2:
                    return parts[0], parts[1]
            
            raise ValueError(f"Invalid GitHub URL format: {repo_url}")
            
        except Exception as e:
            logger.error(f"Failed to extract repo info from URL {repo_url}: {e}")
            raise
    
    def _setup_initial_content(self, owner: str, repo_name: str, task_category: str):
        """Set up initial content for test repository."""
        try:
            base_url = f"https://api.github.com/repos/{owner}/{repo_name}"
            
            # Add basic files based on task category
            if task_category == 'file_operations':
                # Add example file
                self._create_file(base_url, "src/example.py", "# Example Python file\nprint('Hello MCPBench!')\n")
                
            elif task_category == 'issue_management':
                # Create sample issues
                self._create_sample_issue(base_url, "Sample Bug Report", "This is a sample issue for testing", ["bug"])
                self._create_sample_issue(base_url, "Feature Request", "This is a feature request for testing", ["enhancement"])
                
            elif task_category == 'pull_request_workflow':
                # Create branch and PR base structure
                self._create_file(base_url, "CONTRIBUTING.md", "# Contributing Guide\n\nThank you for contributing!\n")
                
            elif task_category == 'branch_management':
                # Add basic files for branch operations
                self._create_file(base_url, "docs/README.md", "# Documentation\n\nProject documentation goes here.\n")
                
            logger.info(f"Set up initial content for {task_category} task in {owner}/{repo_name}")
            
        except Exception as e:
            logger.warning(f"Failed to setup initial content for {task_category}: {e}")
            # Don't raise exception, initial content setup failure shouldn't affect whole flow
    
    def _create_file(self, base_url: str, file_path: str, content: str):
        """Create file in repository."""
        import base64
        
        file_url = f"{base_url}/contents/{file_path}"
        file_data = {
            "message": f"Add {file_path} for MCPBench testing",
            "content": base64.b64encode(content.encode()).decode()
        }
        
        response = self.session.patch(file_url, json=file_data)
        if response.status_code in [200, 201]:
            logger.debug(f"Created file {file_path}")
        else:
            logger.warning(f"Failed to create file {file_path}: {response.status_code}")
    
    def _create_sample_issue(self, base_url: str, title: str, body: str, labels: list):
        """Create sample issue."""
        issue_url = f"{base_url}/issues"
        issue_data = {
            "title": title,
            "body": body,
            "labels": labels
        }
        
        response = self.session.post(issue_url, json=issue_data)
        if response.status_code in [200, 201]:
            logger.debug(f"Created sample issue: {title}")
        else:
            logger.warning(f"Failed to create sample issue: {response.status_code}") 