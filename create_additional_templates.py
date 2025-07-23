#!/usr/bin/env python3
"""
创建额外的GitHub模板仓库
"""

import sys, os, requests, base64, time

def load_env_file():
    """从.mcp_env文件加载环境变量"""
    try:
        with open('.mcp_env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip('"')
    except FileNotFoundError:
        print('❌ .mcp_env file not found')

class GitHubTemplateCreator:
    def __init__(self, github_token):
        self.token = github_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'MCPBench/1.0'
        })
    
    def create_repo(self, name, description, has_issues=True, has_projects=False):
        """创建仓库"""
        create_data = {
            'name': name,
            'description': description,
            'private': False,  # 模板仓库设为公开
            'auto_init': True,  # 自动创建README
            'has_issues': has_issues,
            'has_projects': has_projects,
            'has_wiki': False
        }
        
        response = self.session.post('https://api.github.com/user/repos', json=create_data)
        if response.status_code in [200, 201]:
            repo_data = response.json()
            print(f'✅ Created repository: {repo_data["html_url"]}')
            return repo_data
        else:
            print(f'❌ Failed to create {name}: {response.status_code} {response.text}')
            return None
    
    def create_file(self, owner, repo, path, content, message):
        """在仓库中创建文件"""
        file_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
        file_data = {
            'message': message,
            'content': base64.b64encode(content.encode()).decode()
        }
        
        response = self.session.put(file_url, json=file_data)
        if response.status_code in [200, 201]:
            print(f'  ✅ Created file: {path}')
            return True
        else:
            print(f'  ❌ Failed to create {path}: {response.status_code}')
            return False
    
    def create_issue(self, owner, repo, title, body, labels=None):
        """创建issue"""
        issue_url = f'https://api.github.com/repos/{owner}/{repo}/issues'
        issue_data = {
            'title': title,
            'body': body,
            'labels': labels or []
        }
        
        response = self.session.post(issue_url, json=issue_data)
        if response.status_code in [200, 201]:
            issue_data = response.json()
            print(f'  ✅ Created issue #{issue_data["number"]}: {title}')
            return issue_data
        else:
            print(f'  ❌ Failed to create issue: {response.status_code}')
            return None
    
    def create_label(self, owner, repo, name, color, description=''):
        """创建标签"""
        label_url = f'https://api.github.com/repos/{owner}/{repo}/labels'
        label_data = {
            'name': name,
            'color': color,
            'description': description
        }
        
        response = self.session.post(label_url, json=label_data)
        if response.status_code in [200, 201]:
            print(f'  ✅ Created label: {name}')
            return True
        else:
            return False

def create_issue_rich_template(creator):
    """创建Issue管理丰富模板"""
    print('\n📋 Creating issue-rich-project template...')
    repo = creator.create_repo(
        'issue-rich-project',
        'MCPBench Issue管理模板 - 包含丰富的Issues、标签和里程碑',
        has_issues=True,
        has_projects=True
    )

    if not repo:
        return False

    owner = repo['owner']['login']
    repo_name = repo['name']
    
    # 创建基础文件
    files = {
        'src/main.py': '''# Issue Rich Project - 主程序

def main():
    print("Issue Rich Project - MCPBench Template")
    return "Success"

if __name__ == "__main__":
    main()
''',
        'ISSUE_TEMPLATE.md': '''# Issue模板

## Bug报告
**描述问题**
简洁清晰地描述问题是什么。

**重现步骤**
重现问题的步骤：
1. 进入 '...'
2. 点击 '....'
3. 滚动到 '....'
4. 看到错误

**期望行为**
清晰简洁地描述您期望发生的事情。

**屏幕截图**
如果适用，请添加屏幕截图以帮助解释您的问题。

**环境信息**
- OS: [例如 iOS]
- 浏览器: [例如 chrome, safari]
- 版本: [例如 22]
''',
        '.github/ISSUE_TEMPLATE/bug_report.md': '''---
name: Bug报告
about: 创建一个bug报告来帮助我们改进
title: '[BUG] '
labels: 'bug'
assignees: ''

---

**描述bug**
清晰简洁地描述这个bug。

**重现步骤**
重现问题的步骤：
1. 进入 '...'
2. 点击 '....'
3. 滚动到 '....'
4. 看到错误

**期望行为**
清晰简洁地描述您期望发生的事情。

**屏幕截图**
如果适用，请添加屏幕截图。

**环境信息：**
- OS: [例如 iOS]
- 浏览器: [例如 chrome, safari]  
- 版本: [例如 22]
''',
        '.github/ISSUE_TEMPLATE/feature_request.md': '''---
name: 功能请求
about: 为这个项目提出一个想法
title: '[FEATURE] '
labels: 'enhancement'
assignees: ''

---

**您的功能请求是否与某个问题相关？**
清晰简洁地描述问题是什么。例如：当我[...]时，我总是感到沮丧

**描述您想要的解决方案**
清晰简洁地描述您希望发生的事情。

**描述您考虑过的替代方案**
清晰简洁地描述您考虑过的任何替代解决方案或功能。

**其他上下文**
在此处添加有关功能请求的任何其他上下文或屏幕截图。
''',
        'README.md': '''# Issue Rich Project Template

这是MCPBench的Issue管理测试模板仓库，包含：

## 📋 丰富的Issue示例
- 各种类型的bug报告
- 功能请求
- 文档改进建议
- 性能优化建议

## 🏷️ 完整的标签体系
- `bug` - 缺陷报告
- `enhancement` - 功能增强
- `documentation` - 文档相关
- `good first issue` - 适合新手
- `help wanted` - 需要帮助
- `question` - 疑问
- `priority:high` - 高优先级
- `priority:medium` - 中优先级
- `priority:low` - 低优先级

## 🎯 里程碑管理
- 版本发布计划
- 功能开发阶段

## 💡 使用方法
1. Fork这个仓库
2. 使用提供的Issue模板
3. 根据优先级和标签管理Issues
4. 跟踪里程碑进度
'''
    }
    
    # 创建文件
    for file_path, content in files.items():
        creator.create_file(owner, repo_name, file_path, content, f'Add {file_path}')
        time.sleep(0.5)
    
    # 创建扩展标签
    labels = [
        ('bug', 'd73a4a', '缺陷报告'),
        ('enhancement', 'a2eeef', '功能增强'),  
        ('documentation', '0075ca', '文档相关'),
        ('good first issue', '7057ff', '适合新手'),
        ('help wanted', '008672', '需要帮助'),
        ('question', 'd876e3', '疑问'),
        ('priority:high', 'b60205', '高优先级'),
        ('priority:medium', 'fbca04', '中优先级'),
        ('priority:low', '0e8a16', '低优先级'),
        ('type:bug', 'fc2929', 'Bug类型'),
        ('type:feature', '84b6eb', '新功能'),
        ('type:improvement', 'a2eeef', '改进'),
        ('status:in-progress', 'ededed', '进行中'),
        ('status:blocked', '000000', '被阻塞'),
    ]
    
    for name, color, desc in labels:
        creator.create_label(owner, repo_name, name, color, desc)
        time.sleep(0.2)
    
    # 创建丰富的Issues
    issues = [
        ('登录页面在移动端显示异常', '''**描述**
在移动设备上访问登录页面时，表单元素重叠，按钮无法点击。

**重现步骤**
1. 使用手机浏览器访问登录页面
2. 观察页面布局
3. 尝试点击登录按钮

**期望行为**
登录页面应该在移动端正常显示，表单可用。

**环境信息**
- 设备：iPhone 12
- 浏览器：Safari 15.0
- 屏幕分辨率：390x844''', ['bug', 'priority:high', 'type:bug']),
        
        ('添加暗黑模式支持', '''**功能描述**
希望应用能够支持暗黑模式，提供更好的夜间使用体验。

**期望功能**
- 自动检测系统主题
- 手动切换开关
- 保存用户偏好
- 所有页面都支持暗黑模式

**用户价值**
减轻用户在暗光环境下的眼部疲劳。''', ['enhancement', 'type:feature', 'priority:medium']),
        
        ('API文档缺少认证示例', '''**问题描述**
当前API文档中缺少认证相关的代码示例，开发者难以理解如何正确使用API。

**需要补充的内容**
- Token获取方式
- 请求头设置
- 错误处理示例
- 刷新token流程

**影响范围**
新接入的开发者''', ['documentation', 'priority:medium', 'good first issue']),
        
        ('数据库查询性能优化', '''**性能问题**
在用户量增长后，某些数据库查询变得很慢，影响用户体验。

**问题分析**
- 缺少合适的索引
- 复杂的JOIN操作
- 数据量过大的单表查询

**优化建议**
- 添加复合索引
- 查询结果缓存
- 分页查询优化
- 考虑数据分表''', ['type:improvement', 'priority:high', 'help wanted']),
        
        ('用户反馈功能实现', '''**功能需求**
需要一个用户反馈功能，让用户能够提交建议和问题。

**功能要点**
- 分类反馈（bug、建议、其他）
- 附件上传
- 反馈状态跟踪
- 管理员回复功能

**技术考虑**
- 需要新的数据库表
- 文件上传组件
- 邮件通知系统''', ['type:feature', 'priority:low', 'enhancement']),
        
        ('如何配置开发环境？', '''我是新加入的开发者，想了解：

**环境配置**
- 需要安装哪些依赖？
- 数据库如何初始化？
- 环境变量怎么配置？

**开发流程**
- 代码提交规范
- 测试运行方式
- 部署流程

请提供详细的setup指南。''', ['question', 'documentation', 'good first issue']),
    ]
    
    for title, body, labels_list in issues:
        creator.create_issue(owner, repo_name, title, body, labels_list)
        time.sleep(0.5)

    print(f'✅ Issue-rich template created: https://github.com/{owner}/{repo_name}')
    return True

def create_pr_workflow_template(creator):
    """创建PR工作流模板"""
    print('\n🔀 Creating pr-workflow-project template...')
    repo = creator.create_repo(
        'pr-workflow-project',
        'MCPBench PR工作流模板 - 包含分支、PR和Code Review示例',
        has_issues=True,
        has_projects=False
    )

    if not repo:
        return False

    owner = repo['owner']['login']
    repo_name = repo['name']
    
    # 创建PR工作流相关文件
    files = {
        'src/app.py': '''# PR Workflow Demo App

class Calculator:
    """简单计算器类"""
    
    def add(self, a, b):
        """加法运算"""
        return a + b
    
    def subtract(self, a, b):
        """减法运算"""
        return a - b
    
    def multiply(self, a, b):
        """乘法运算"""
        return a * b
    
    def divide(self, a, b):
        """除法运算"""
        if b == 0:
            raise ValueError("Division by zero")
        return a / b

def main():
    calc = Calculator()
    print("PR Workflow Demo")
    print(f"2 + 3 = {calc.add(2, 3)}")
    return calc

if __name__ == "__main__":
    main()
''',
        '.github/pull_request_template.md': '''## 📋 变更说明
请描述此PR的变更内容和目的。

## 🔗 相关Issue
修复 #(issue编号)

## 📝 变更类型
请删除不适用的选项：
- [ ] Bug修复（非破坏性变更，修复了一个问题）
- [ ] 新功能（非破坏性变更，添加了功能）
- [ ] 破坏性变更（修复或功能会导致现有功能无法按预期工作）
- [ ] 文档更新

## 🧪 测试
请描述您运行的测试以验证您的更改。

- [ ] 单元测试
- [ ] 集成测试
- [ ] 手动测试

## ✅ 检查清单
- [ ] 我的代码遵循此项目的样式指南
- [ ] 我已经对我的代码进行了自我审查
- [ ] 我已经对我的代码进行了评论，特别是在难以理解的地方
- [ ] 我已经对相应的文档进行了更改
- [ ] 我的更改没有生成新的警告
- [ ] 我已经添加了证明我的修复有效或我的功能工作的测试
- [ ] 新的和现有的单元测试都通过了我的更改
''',
        '.github/workflows/pr-checks.yml': '''name: PR Checks

on:
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest flake8
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
    
    - name: Lint with flake8
      run: |
        # stop the build if there are Python syntax errors or undefined names
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        # exit-zero treats all errors as warnings
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Test with pytest
      run: |
        pytest tests/ -v
        
  code-quality:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run Code Quality Checks
      run: |
        echo "Running code quality checks..."
        # 这里可以添加更多代码质量检查工具
        
  security:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run Security Scan
      run: |
        echo "Running security scan..."
        # 这里可以添加安全扫描工具
''',
        'tests/test_app.py': '''# 测试文件
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.app import Calculator
import pytest

class TestCalculator:
    def setup_method(self):
        self.calc = Calculator()
    
    def test_add(self):
        assert self.calc.add(2, 3) == 5
        assert self.calc.add(-1, 1) == 0
    
    def test_subtract(self):
        assert self.calc.subtract(5, 3) == 2
        assert self.calc.subtract(0, 5) == -5
    
    def test_multiply(self):
        assert self.calc.multiply(3, 4) == 12
        assert self.calc.multiply(-2, 3) == -6
    
    def test_divide(self):
        assert self.calc.divide(10, 2) == 5
        assert self.calc.divide(7, 2) == 3.5
    
    def test_divide_by_zero(self):
        with pytest.raises(ValueError, match="Division by zero"):
            self.calc.divide(5, 0)

if __name__ == "__main__":
    pytest.main([__file__])
''',
        'CONTRIBUTING.md': '''# 贡献指南 - PR工作流

## 🔄 开发流程

### 1. 准备工作
- Fork仓库到个人账户
- Clone到本地：`git clone https://github.com/your-username/pr-workflow-project.git`
- 添加上游仓库：`git remote add upstream https://github.com/arvinxx/pr-workflow-project.git`

### 2. 创建功能分支
```bash
git checkout -b feature/your-feature-name
# 或者
git checkout -b bugfix/fix-issue-number
```

### 3. 开发代码
- 编写代码
- 添加测试
- 更新文档

### 4. 提交代码
```bash
git add .
git commit -m "type(scope): description"
```

#### 提交信息规范
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

### 5. 推送并创建PR
```bash
git push origin feature/your-feature-name
```

然后在GitHub上创建Pull Request。

## 📋 PR检查清单

提交PR前请确保：

- [ ] 代码通过所有测试
- [ ] 添加了必要的测试用例
- [ ] 更新了相关文档
- [ ] 遵循代码规范
- [ ] PR描述清晰，关联了相关Issue

## 🔍 Code Review过程

1. **自动检查**：CI会自动运行测试和代码质量检查
2. **人工审查**：至少需要一名维护者审查
3. **反馈处理**：根据审查意见修改代码
4. **合并**：审查通过后合并到主分支

## 🚀 发布流程

- `main` 分支：生产环境
- `develop` 分支：开发环境
- `feature/*` 分支：功能开发
- `bugfix/*` 分支：bug修复
- `hotfix/*` 分支：紧急修复
''',
        'CODE_REVIEW_GUIDELINES.md': '''# Code Review指南

## 📝 Review checklist

### 功能性
- [ ] 代码是否实现了预期功能？
- [ ] 边界条件是否得到处理？
- [ ] 错误处理是否合适？

### 代码质量
- [ ] 代码是否清晰易读？
- [ ] 函数是否职责单一？
- [ ] 是否遵循了项目的编码规范？
- [ ] 是否有适当的注释？

### 性能
- [ ] 是否存在性能问题？
- [ ] 算法选择是否合理？
- [ ] 是否有内存泄漏风险？

### 测试
- [ ] 是否有足够的测试覆盖？
- [ ] 测试用例是否有效？
- [ ] 是否测试了边界条件？

### 安全性
- [ ] 是否存在安全漏洞？
- [ ] 输入验证是否充分？
- [ ] 敏感信息是否得到保护？

## 💬 Review评论指南

### 好的评论示例
- "建议使用列表推导式来简化这个循环，提高可读性"
- "这里缺少空值检查，可能导致运行时错误"
- "考虑将这个大函数拆分为几个小函数"

### 避免的评论
- "这个代码很糟糕"
- "为什么要这样做？"
- 纯主观的风格评论

## 🎯 Review原则

1. **建设性**：提供具体的改进建议
2. **尊重**：保持专业和友善的态度
3. **聚焦**：关注代码本身，而不是人
4. **教育性**：帮助他人学习和成长
'''
    }
    
    # 创建文件
    for file_path, content in files.items():
        creator.create_file(owner, repo_name, file_path, content, f'Add {file_path}')
        time.sleep(0.5)

    print(f'✅ PR workflow template created: https://github.com/{owner}/{repo_name}')
    return True

def main():
    print('🚀 Creating Additional GitHub Templates for MCPBench...')
    print('=' * 60)
    
    load_env_file()
    
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print('❌ GITHUB_TOKEN not found in environment')
        return False

    creator = GitHubTemplateCreator(token)
    
    success_count = 0
    
    # 创建Issue管理模板
    if create_issue_rich_template(creator):
        success_count += 1
    
    # 创建PR工作流模板  
    if create_pr_workflow_template(creator):
        success_count += 1
    
    print(f'\n🎉 Template creation completed!')
    print(f'Successfully created {success_count}/2 additional templates')
    
    if success_count > 0:
        print('\nNext steps:')
        print('1. Update the template mapping in github_template_manager.py')
        print('2. Test the new templates with fork mechanism')
        print('3. Verify templates work with different task categories')
    
    return success_count > 0

if __name__ == "__main__":
    main() 