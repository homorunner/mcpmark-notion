# GitHub MCP Server 环境管理与复现机制设计

## 🔍 **当前问题分析**

### 问题1：环境隔离不足
- **现状**：测试完成后只归档（archive）仓库，不删除
- **问题**：测试仓库累积，污染GitHub账户，影响后续测试
- **根因**：缺乏有效的环境清理机制

### 问题2：缺少环境复现逻辑
- **现状**：简单任务可以从空仓库开始，但复杂任务需要预置数据
- **需求**：像Notion的模板机制一样，为复杂场景预置issues、PRs、commits等
- **挑战**：GitHub没有模板"复制"概念，需要设计等价机制

## 🚀 **改进方案设计**

### 方案1：模板仓库 + Fork机制 (推荐)

#### 核心思路
```
预置模板仓库 → Fork到用户账户 → 任务执行 → 删除Fork仓库
```

#### 实现细节
- **模板组织**：`mcpbench-templates` (存放各种模板仓库)
- **测试仓库命名**：`mcpbench-test-{timestamp}-{task-category}-{task-id}`
- **生命周期**：
  - **初始化**：验证模板仓库可用性
  - **任务执行**：Fork模板到用户账户，重命名为测试仓库
  - **清理**：直接删除Fork出来的测试仓库

#### 优势
✅ 真实的GitHub环境（包含issues、PRs、commits等）
✅ 完全环境隔离  
✅ 类似Notion的模板复制机制
✅ 不需要特殊权限
✅ 支持复杂场景的预置数据

#### 挑战
⚠️ 需要维护模板仓库
⚠️ Fork操作有API限制

### 方案2：仓库标签管理 (备选)

#### 核心思路
```
测试开始 → 标记所有测试仓库 → 测试结束 → 批量删除带标记的仓库
```

#### 实现细节
- **仓库命名**：`mcpbench-test-{timestamp}-{task-id}`
- **描述标记**：统一的测试标识符
- **清理机制**：根据命名规则批量删除

## 🏗️ **GitHub环境复现机制设计**

### 核心设计：模板仓库 + Fork/Clone 机制

#### 设计思路
```
预置模板仓库 → Fork到测试环境 → 任务执行 → 删除Fork
```

### 模板仓库体系

#### 1. 基础模板仓库
```
mcpbench-templates/
├── empty-repo/           # 空仓库模板
├── basic-project/        # 基础项目模板
├── complex-workflow/     # 复杂工作流模板
└── issue-management/     # Issue管理模板
```

#### 2. 模板内容设计

**基础项目模板** (`basic-project`)
```
Repository Structure:
├── README.md
├── src/
│   ├── main.py
│   └── utils.py
├── tests/
│   └── test_main.py
├── .github/
│   └── workflows/
│       └── ci.yml
└── docs/
    └── api.md

Pre-created Resources:
- 5个不同类型的Issues (bug, feature, documentation, etc.)
- 3个不同状态的Pull Requests (open, merged, closed)
- 10个历史Commits
- 2个Releases/Tags
- 多个Labels (bug, enhancement, documentation, etc.)
- 2个Milestones (active and closed)
```

**复杂工作流模板** (`complex-workflow`)
```
Advanced Resources:
- Branch protection rules
- Multiple contributor commits
- Review requests and approvals
- CI/CD workflow runs (success/failure)
- Dependency updates
- Security advisories
- Project boards with cards
```

### 环境复现流程

#### 阶段1：模板选择与Fork
```python
def setup_environment(task: GitHubTask) -> str:
    # 1. 根据任务类别选择模板
    template_repo = select_template_by_category(task.category)
    
    # 2. Fork模板到测试环境
    test_repo = fork_template_to_test_env(template_repo, task.task_id)
    
    # 3. 个性化设置（如需要）
    customize_for_task(test_repo, task)
    
    return test_repo
```

#### 阶段2：任务执行环境
- **独立空间**：每个任务使用独立的Fork
- **真实数据**：包含实际的GitHub对象（issues、PRs等）
- **可操作性**：Agent可以直接操作所有GitHub功能

#### 阶段3：清理机制
```python
def cleanup_environment(test_repo: str):
    # 直接删除Fork的测试仓库
    delete_repository(test_repo)
```

## 🛠️ **具体实现方案**

### Phase 1: 环境隔离改进

#### 1.1 模板仓库管理
```python
class GitHubTemplateManager:
    def __init__(self, github_token: str, template_org: str = "mcpbench-templates"):
        self.github_token = github_token
        self.template_org = template_org
        self.session = requests.Session()
        # ... setup session headers
        
    def fork_template(self, template_name: str, task: GitHubTask) -> str:
        """Fork模板仓库到用户账户"""
        # 1. Fork模板仓库
        fork_url = f"https://api.github.com/repos/{self.template_org}/{template_name}/forks"
        response = self.session.post(fork_url, json={})
        
        if response.status_code not in [200, 202]:
            raise Exception(f"Failed to fork template: {response.text}")
        
        fork_data = response.json()
        original_name = fork_data['name']
        
        # 2. 重命名为测试仓库名称
        new_name = self._generate_test_repo_name(task)
        rename_url = f"https://api.github.com/repos/{fork_data['owner']['login']}/{original_name}"
        rename_data = {"name": new_name}
        
        rename_response = self.session.patch(rename_url, json=rename_data)
        if rename_response.status_code == 200:
            return rename_response.json()['html_url']
        else:
            # 如果重命名失败，仍返回原Fork
            return fork_data['html_url']
            
    def _generate_test_repo_name(self, task: GitHubTask) -> str:
        """生成测试仓库名称"""
        timestamp = int(time.time())
        return f"mcpbench-test-{timestamp}-{task.category}-{task.task_id}"
```

#### 1.2 测试仓库清理机制
```python
class GitHubTestRepoManager:
    def track_test_repo(self, repo_name: str, owner: str):
        """追踪测试仓库"""
        self.test_repos.append({
            'name': repo_name,
            'owner': owner,
            'created_at': time.time(),
            'source': 'template_fork'
        })
        
    def cleanup_all_test_repos(self):
        """批量清理所有测试仓库"""
        for repo in self.test_repos:
            try:
                self._delete_repository(repo['owner'], repo['name'])
                logger.info(f"Deleted test repo: {repo['owner']}/{repo['name']}")
            except Exception as e:
                logger.error(f"Failed to delete {repo['owner']}/{repo['name']}: {e}")
        
        self.test_repos.clear()
        
    def force_cleanup_by_pattern(self, pattern: str = "mcpbench-test-"):
        """根据命名模式强制清理测试仓库"""
        user = self._get_authenticated_user()
        repos = self._get_user_repos(user)
        
        for repo in repos:
            if pattern in repo['name']:
                try:
                    self._delete_repository(repo['owner']['login'], repo['name'])
                    logger.info(f"Force cleaned: {repo['full_name']}")
                except Exception as e:
                    logger.error(f"Failed to clean {repo['full_name']}: {e}")
```

### Phase 2: 模板仓库体系

#### 2.1 模板仓库创建
```bash
# 创建模板仓库 (一次性设置)
./scripts/setup-github-templates.sh
```

#### 2.2 模板内容生成
```python
class GitHubTemplateGenerator:
    def create_basic_project_template(self):
        """创建基础项目模板"""
        repo = self.create_repo("mcpbench-template-basic")
        
        # 添加文件结构
        self.add_file(repo, "README.md", basic_readme_content)
        self.add_file(repo, "src/main.py", sample_code)
        
        # 创建Issues
        self.create_issue(repo, "Bug: Login fails", "bug")
        self.create_issue(repo, "Feature: Add dark mode", "enhancement")
        
        # 创建PRs
        self.create_pull_request(repo, "Fix login bug", "bugfix-branch")
        
        # 设置标签和里程碑
        self.create_labels(repo, ["bug", "enhancement", "documentation"])
        self.create_milestone(repo, "v1.0 Release")
```

#### 2.3 环境复现引擎
```python
class GitHubEnvironmentReplicator:
    def replicate_environment(self, task: GitHubTask) -> str:
        """复现任务环境"""
        # 1. 选择模板
        template = self.select_template(task.category)
        
        # 2. Fork到测试空间
        test_repo = self.fork_template(template, task)
        
        # 3. 任务特定定制
        if task.requires_customization():
            self.customize_environment(test_repo, task)
            
        return test_repo
    
    def select_template(self, category: str) -> str:
        template_mapping = {
            "basic_repo_operations": "mcpbench-template-empty",
            "issue_management": "mcpbench-template-issues",
            "pull_request_workflow": "mcpbench-template-prs",
            "branch_management": "mcpbench-template-branches",
            "complex_workflows": "mcpbench-template-complex"
        }
        return template_mapping.get(category, "mcpbench-template-basic")
```

## 📊 **对比分析：Notion vs GitHub**

| 维度 | Notion机制 | GitHub机制 |
|------|------------|------------|
| **模板存储** | 模板工作区 | 模板仓库组织 |
| **环境复制** | Page复制API | Fork/Clone |
| **资源隔离** | 独立Page ID | 独立Repository |
| **清理机制** | Archive Page | Delete Repository |
| **预置数据** | Block结构 | Issues/PRs/Commits |
| **权限管理** | Workspace权限 | Repository权限 |

## 🔄 **完整生命周期流程**

### 初始化阶段
```python
# 1. 验证模板仓库可用性
template_manager = GitHubTemplateManager(github_token)
templates = await template_manager.validate_template_repos()

# 2. 初始化测试仓库管理器
test_repo_manager = GitHubTestRepoManager(github_token)
```

### 任务执行阶段
```python
for task in tasks:
    # 1. 环境复现 - Fork模板仓库
    test_repo_url = template_manager.fork_template(
        template_name=select_template_for_task(task), 
        task=task
    )
    
    # 2. 追踪测试仓库
    test_repo_manager.track_test_repo_from_url(test_repo_url)
    
    # 3. 任务执行
    result = await execute_task(task, test_repo_url)
    
    # 4. 即时清理（可选）
    if cleanup_immediately:
        test_repo_manager.delete_repo_from_url(test_repo_url)
```

### 清理阶段
```python
# 批量清理所有测试仓库
test_repo_manager.cleanup_all_test_repos()

# 或者根据命名模式强制清理
test_repo_manager.force_cleanup_by_pattern("mcpbench-test-")
```

## 🎯 **实施优先级**

### 高优先级 (立即实施)
1. **修复当前清理问题** - 改为真正删除测试仓库
2. **基础模板仓库** - 创建空仓库和基础项目模板
3. **Fork机制实现** - 实现模板仓库Fork和重命名

### 中优先级 (短期实施)
1. **复杂模板** - Issue管理、PR工作流模板
2. **环境定制** - 根据任务需求个性化环境
3. **并行支持** - 支持多个测试同时运行

### 低优先级 (长期优化)
1. **模板版本管理** - 模板的版本控制
2. **性能优化** - Fork和删除的性能优化
3. **监控告警** - 环境状态监控

## 🔧 **配置示例**

### 环境配置
```yaml
github_environment:
  # 环境隔离策略
  isolation_strategy: "template_fork"  # "template_fork" | "tagged_repos"
  
  # 模板仓库设置
  template_repos:
    base_org: "arvinxx"  # 使用arvinxx组织
    repos:
      empty: "empty-repo"  # 基础空仓库模板
      basic: "empty-repo"  # 暂时都使用empty-repo，后续可扩展
      issues: "empty-repo"
      prs: "empty-repo"
      complex: "empty-repo"
  
  # 测试仓库命名
  test_repo_naming:
    prefix: "mcpbench-test"
    include_timestamp: true
    include_category: true
    include_task_id: true
      
  # 清理配置
  cleanup:
    immediate_cleanup: true
    cleanup_policy: "delete_immediately"  # "delete_immediately" | "archive_only"
    retention_hours: 0  # 0表示立即删除
    max_test_repos: 50  # 安全限制
    force_cleanup_pattern: "mcpbench-test-"  # 强制清理的仓库名称模式
```

## 🚨 **风险与限制**

### GitHub API限制
- **Fork操作**：每个仓库的Fork有数量限制
- **仓库重命名**：需要admin权限
- **仓库删除**：需要admin权限
- **Rate limiting**：API调用频率限制

### 解决方案
1. **API配额管理**：监控和限制API使用
2. **权限验证**：测试前验证必要权限（包括仓库删除权限）
3. **降级方案**：Fork失败时创建空仓库，重命名失败时保持原名
4. **清理保障**：支持按命名模式强制清理，防止测试仓库累积

### 安全考虑
- **权限最小化**：只授予必要的GitHub权限
- **资源限制**：设置测试仓库数量上限
- **清理保障**：多层清理机制防止资源泄露

---

> **总结**：通过模板仓库Fork机制实现环境复现和隔离，类似Notion的模板复制逻辑，为每个任务提供独立的、预置了丰富数据的GitHub环境，任务完成后直接删除Fork出来的测试仓库，实现完整的环境生命周期管理。 