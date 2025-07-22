#!/usr/bin/env python3
"""
GitHub模板仓库创建脚本 - 为MCPBench创建完整的测试模板
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
            # 标签可能已存在，不报错
            return False

def create_basic_project_template(creator):
    """创建基础项目模板"""
    print('\n📁 Creating basic-project template...')
    repo = creator.create_repo(
        'basic-project',
        'MCPBench基础项目模板 - 包含基本的项目结构和文件',
        has_issues=True,
        has_projects=False
    )

    if not repo:
        return False

    owner = repo['owner']['login']
    repo_name = repo['name']
    
    # 创建项目结构
    files = {
        'src/main.py': '''# MCPBench示例项目 - 主程序

def main():
    print("Hello, MCPBench!")
    return "Success"

if __name__ == "__main__":
    main()
''',
        'src/utils.py': '''# 实用工具函数

def calculate_sum(a, b):
    """计算两个数的和"""
    return a + b

def format_message(message, prefix="[INFO]"):
    """格式化消息"""
    return f"{prefix} {message}"
''',
        'tests/test_main.py': '''# 主程序测试
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.main import main
from src.utils import calculate_sum, format_message

def test_main():
    result = main()
    assert result == "Success"

def test_calculate_sum():
    assert calculate_sum(2, 3) == 5

def test_format_message():
    result = format_message("test")
    assert result == "[INFO] test"

if __name__ == "__main__":
    test_main()
    test_calculate_sum()
    test_format_message()
    print("All tests passed!")
''',
        '.github/workflows/ci.yml': '''name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.9'
    
    - name: Run tests
      run: |
        cd tests
        python test_main.py
''',
        'docs/api.md': '''# API文档

## 主要函数

### main()
- **描述**: 主程序入口点
- **返回值**: "Success" 字符串
- **示例**: 
  ```python
  from src.main import main
  result = main()
  print(result)  # 输出: Success
  ```

### calculate_sum(a, b)
- **描述**: 计算两个数的和
- **参数**: 
  - `a`: 第一个数字
  - `b`: 第二个数字
- **返回值**: 数字和
''',
        'CONTRIBUTING.md': '''# 贡献指南

感谢您对MCPBench示例项目的贡献！

## 开发流程

1. Fork仓库
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -am "Add new feature"`
4. 推送分支: `git push origin feature/new-feature`
5. 创建Pull Request

## 代码规范

- 使用Python 3.9+
- 遵循PEP 8编码规范
- 为新功能添加测试
- 更新相关文档
''',
        'requirements.txt': '''# MCPBench 基础项目依赖

# 开发依赖
pytest>=7.0.0
flake8>=4.0.0
black>=22.0.0

# 示例依赖
requests>=2.28.0
''',
        '.gitignore': '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
''',
    }
    
    # 创建文件
    for file_path, content in files.items():
        creator.create_file(owner, repo_name, file_path, content, f'Add {file_path}')
        time.sleep(0.5)  # API限制保护
    
    print('\n🎯 Adding sample issues and labels...')
    
    # 创建标签
    labels = [
        ('bug', 'd73a4a', '缺陷报告'),
        ('enhancement', 'a2eeef', '功能增强'),  
        ('documentation', '0075ca', '文档相关'),
        ('good first issue', '7057ff', '适合新手'),
        ('help wanted', '008672', '需要帮助'),
        ('question', 'd876e3', '疑问')
    ]
    
    for name, color, desc in labels:
        creator.create_label(owner, repo_name, name, color, desc)
        time.sleep(0.2)
    
    # 创建示例issues  
    issues = [
        ('修复计算函数的精度问题', '''在使用 `calculate_sum` 函数时，发现浮点数计算存在精度问题。

**重现步骤：**
1. 调用 `calculate_sum(0.1, 0.2)`
2. 期望结果：`0.3`
3. 实际结果：`0.30000000000000004`

**建议解决方案：**
使用 `decimal` 模块进行精确计算。''', ['bug']),
        
        ('添加更多的实用工具函数', '''建议在 `utils.py` 中添加更多常用的工具函数，比如：

- `format_date()` - 日期格式化
- `validate_email()` - 邮箱验证  
- `generate_uuid()` - 生成UUID
- `safe_json_load()` - 安全的JSON解析''', ['enhancement']),
        
        ('改进API文档的示例代码', '''当前的API文档中的示例代码比较简单，建议：

1. 添加更完整的使用示例
2. 包含错误处理的代码
3. 添加性能注意事项''', ['documentation', 'enhancement']),
    ]
    
    for title, body, labels_list in issues:
        creator.create_issue(owner, repo_name, title, body, labels_list)
        time.sleep(0.5)

    print(f'✅ Basic project template created: https://github.com/{owner}/{repo_name}')
    return True

def main():
    print('🚀 Creating GitHub Template Repositories for MCPBench...')
    print('=' * 60)
    
    load_env_file()
    
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print('❌ GITHUB_TOKEN not found in environment')
        return False

    creator = GitHubTemplateCreator(token)
    
    # 创建基础项目模板
    success = create_basic_project_template(creator)
    
    if success:
        print('\n🎉 Template creation completed successfully!')
        print('\nNext steps:')
        print('1. Check the created repository')
        print('2. You can now test the template fork mechanism')
        print('3. Create additional templates as needed')
    else:
        print('\n❌ Template creation failed')
        
    return success

if __name__ == "__main__":
    main() 