"""
GitHub模板管理器 - 实现模板仓库Fork和环境复现机制
"""

import logging
import requests
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitHubTemplateManager:
    """GitHub模板仓库管理器 - 类似Notion的模板复制机制"""
    
    def __init__(self, github_token: str, template_org: str = "arvinxx"):
        self.github_token = github_token
        self.template_org = template_org
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MCPBench/1.0"
        })
        
        # 模板映射 - 根据任务类别选择模板
        self.template_mapping = {
            "basic_repo_operations": None,  # 基础操作不需要模板，直接创建空仓库
            "file_operations": "empty-repo",  # 使用arvinxx/empty-repo作为基础模板
            "issue_management": "empty-repo",  # 暂时都使用empty-repo，后续可以创建更丰富的模板
            "pull_request_workflow": "empty-repo", 
            "branch_management": "empty-repo",
            "complex_workflows": "empty-repo"
        }
    
    def select_template_for_task(self, task_category: str) -> Optional[str]:
        """根据任务类别选择合适的模板仓库"""
        return self.template_mapping.get(task_category)
    
    def fork_template(self, template_name: str, task_id: str, task_category: str) -> str:
        """Fork模板仓库到用户账户并重命名"""
        try:
            # 1. Fork模板仓库
            fork_url = f"https://api.github.com/repos/{self.template_org}/{template_name}/forks"
            response = self.session.post(fork_url, json={})
            
            if response.status_code not in [200, 202]:
                raise Exception(f"Failed to fork template {template_name}: {response.status_code} {response.text}")
            
            fork_data = response.json()
            original_name = fork_data['name']
            owner = fork_data['owner']['login']
            
            logger.info(f"Forked template {template_name} to {owner}/{original_name}")
            
            # 2. 生成测试仓库名称
            new_name = self._generate_test_repo_name(task_id, task_category)
            
            # 3. 重命名为测试仓库名称
            if new_name != original_name:
                rename_success = self._rename_repository(owner, original_name, new_name)
                if rename_success:
                    logger.info(f"Renamed repository to {owner}/{new_name}")
                    return f"https://github.com/{owner}/{new_name}"
                else:
                    logger.warning(f"Failed to rename repository, using original name: {owner}/{original_name}")
            
            return fork_data['html_url']
            
        except Exception as e:
            logger.error(f"Failed to fork template {template_name}: {e}")
            raise
    
    def _rename_repository(self, owner: str, old_name: str, new_name: str) -> bool:
        """重命名仓库"""
        try:
            rename_url = f"https://api.github.com/repos/{owner}/{old_name}"
            rename_data = {"name": new_name}
            
            response = self.session.patch(rename_url, json=rename_data)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to rename repository {owner}/{old_name} to {new_name}: {e}")
            return False
    
    def _generate_test_repo_name(self, task_id: str, task_category: str) -> str:
        """生成测试仓库名称"""
        timestamp = int(time.time())
        # 格式: mcpbench-test-{timestamp}-{category}-{task_id}
        return f"mcpbench-test-{timestamp}-{task_category}-{task_id}".replace("_", "-")
    
    def create_empty_repo(self, task_id: str, task_category: str) -> str:
        """为不需要模板的任务创建空仓库"""
        try:
            repo_name = self._generate_test_repo_name(task_id, task_category)
            
            create_data = {
                "name": repo_name,
                "description": f"MCPBench test repository for {task_category} task {task_id}",
                "private": False,  # 测试仓库设为公开
                "auto_init": True,  # 自动创建README
                "has_issues": True,
                "has_projects": False,
                "has_wiki": False
            }
            
            create_url = "https://api.github.com/user/repos"
            response = self.session.post(create_url, json=create_data)
            
            if response.status_code in [200, 201]:
                repo_data = response.json()
                logger.info(f"Created empty repository: {repo_data['html_url']}")
                return repo_data['html_url']
            else:
                raise Exception(f"Failed to create repository: {response.status_code} {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to create empty repository: {e}")
            raise
    
    def setup_environment_for_task(self, task_id: str, task_category: str) -> Optional[str]:
        """为任务设置环境 - 统一入口"""
        template_name = self.select_template_for_task(task_category)
        
        try:
            if template_name and self._can_fork_template(template_name):
                # 如果模板存在且可以Fork，使用模板Fork
                return self.fork_template(template_name, task_id, task_category)
            else:
                # 否则创建基础测试仓库
                logger.info(f"Creating new test repository for {task_category} task (template not forkable)")
                return self.create_test_repo_with_content(task_id, task_category)
                
        except Exception as e:
            logger.error(f"Failed to setup environment for task {task_id}: {e}")
            # 降级方案：创建基础仓库
            try:
                logger.info("Falling back to creating basic test repository...")
                return self.create_test_repo_with_content(task_id, task_category)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return None
    
    def validate_template_repos(self) -> Dict[str, bool]:
        """验证模板仓库是否可用"""
        results = {}
        
        for category, template_name in self.template_mapping.items():
            if template_name is None:
                results[category] = True  # 不需要模板的任务
                continue
                
            try:
                # 检查模板仓库是否存在
                check_url = f"https://api.github.com/repos/{self.template_org}/{template_name}"
                response = self.session.get(check_url)
                results[category] = response.status_code == 200
                
                if response.status_code != 200:
                    logger.warning(f"Template repository {self.template_org}/{template_name} not accessible: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Failed to validate template {template_name}: {e}")
                results[category] = False
        
        return results
    
    def extract_repo_info_from_url(self, repo_url: str) -> tuple[str, str]:
        """从GitHub URL提取owner和repo名称"""
        try:
            # 支持 https://github.com/owner/repo 格式
            if "github.com" in repo_url:
                path = urlparse(repo_url).path.strip('/')
                parts = path.split('/')
                if len(parts) >= 2:
                    return parts[0], parts[1]
            
            raise ValueError(f"Invalid GitHub URL format: {repo_url}")
            
        except Exception as e:
            logger.error(f"Failed to extract repo info from URL {repo_url}: {e}")
            raise 

    def _can_fork_template(self, template_name: str) -> bool:
        """检查模板仓库是否可以被Fork（即是否有Git内容）"""
        try:
            # 检查模板仓库的commits
            commits_url = f"https://api.github.com/repos/{self.template_org}/{template_name}/commits"
            response = self.session.get(commits_url)
            
            if response.status_code == 200:
                commits = response.json()
                return len(commits) > 0  # 有commit才能Fork
            elif response.status_code == 409:
                # 409 表示空仓库
                logger.info(f"Template {template_name} is empty and cannot be forked")
                return False
            else:
                logger.warning(f"Cannot check commits for template {template_name}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to check if template {template_name} can be forked: {e}")
            return False

    def create_test_repo_with_content(self, task_id: str, task_category: str) -> str:
        """创建带基础内容的测试仓库，用于替代空模板Fork"""
        try:
            repo_name = self._generate_test_repo_name(task_id, task_category)
            
            # 根据任务类别定制仓库内容
            create_data = {
                "name": repo_name,
                "description": f"MCPBench test repository for {task_category} task {task_id}",
                "private": False,  # 测试仓库设为公开
                "auto_init": True,  # 自动创建README
                "has_issues": True,
                "has_projects": False,
                "has_wiki": False
            }
            
            # 为不同任务类型添加不同的初始内容
            if task_category in ['issue_management', 'pull_request_workflow']:
                create_data["has_issues"] = True
                create_data["has_projects"] = True
            
            create_url = "https://api.github.com/user/repos"
            response = self.session.post(create_url, json=create_data)
            
            if response.status_code in [200, 201]:
                repo_data = response.json()
                repo_url = repo_data['html_url']
                logger.info(f"Created test repository: {repo_url}")
                
                # 为特定任务类型添加初始内容
                if task_category != 'basic_repo_operations':
                    self._setup_initial_content(repo_data['owner']['login'], repo_name, task_category)
                
                return repo_url
            else:
                raise Exception(f"Failed to create repository: {response.status_code} {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to create test repository with content: {e}")
            raise

    def _setup_initial_content(self, owner: str, repo_name: str, task_category: str):
        """为测试仓库设置初始内容"""
        try:
            base_url = f"https://api.github.com/repos/{owner}/{repo_name}"
            
            # 添加一些基础文件
            if task_category == 'file_operations':
                # 添加一个示例文件
                self._create_file(base_url, "src/example.py", "# Example Python file\nprint('Hello MCPBench!')\n")
                
            elif task_category == 'issue_management':
                # 创建一些示例issues
                self._create_sample_issue(base_url, "Sample Bug Report", "This is a sample issue for testing", ["bug"])
                self._create_sample_issue(base_url, "Feature Request", "This is a feature request for testing", ["enhancement"])
                
            elif task_category == 'pull_request_workflow':
                # 创建一个分支和PR的基础结构
                self._create_file(base_url, "CONTRIBUTING.md", "# Contributing Guide\n\nThank you for contributing!\n")
                
            elif task_category == 'branch_management':
                # 添加一些基础文件用于分支操作
                self._create_file(base_url, "docs/README.md", "# Documentation\n\nProject documentation goes here.\n")
                
            logger.info(f"Set up initial content for {task_category} task in {owner}/{repo_name}")
            
        except Exception as e:
            logger.warning(f"Failed to setup initial content for {task_category}: {e}")
            # 不抛出异常，初始内容设置失败不应该影响整个流程

    def _create_file(self, base_url: str, file_path: str, content: str):
        """在仓库中创建文件"""
        import base64
        
        file_url = f"{base_url}/contents/{file_path}"
        file_data = {
            "message": f"Add {file_path} for MCPBench testing",
            "content": base64.b64encode(content.encode()).decode()
        }
        
        response = self.session.put(file_url, json=file_data)
        if response.status_code in [200, 201]:
            logger.debug(f"Created file {file_path}")
        else:
            logger.warning(f"Failed to create file {file_path}: {response.status_code}")

    def _create_sample_issue(self, base_url: str, title: str, body: str, labels: list):
        """创建示例issue"""
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