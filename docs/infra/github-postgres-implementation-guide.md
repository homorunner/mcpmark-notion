# GitHub & PostgreSQL MCP Server 实现指南

## 🎯 实施概述

基于 Notion MCP Server 的参考实现，本指南提供 GitHub 和 PostgreSQL MCP Server 集成的具体实施方案。

## 🐙 GitHub MCP Server 实现

### 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                GitHub MCP Service                            │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │GitHubTaskManager│    │GitHubStateManager│               │
│  │                 │    │                  │               │
│  │• Repository Mgmt│    │• Fork & Branch   │               │
│  │• MCP Integration│    │• PR Management   │               │
│  │• API Calls      │    │• Cleanup Actions │               │
│  └─────────────────┘    └─────────────────┘                │
│                                                             │
│            ┌─────────────────┐                             │
│            │GitHubLoginHelper│                             │
│            │                 │                             │
│            │• Token Auth     │                             │
│            │• OAuth Flow     │                             │
│            │• Permission Mgmt│                             │
│            └─────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

### 🛠️ 组件实现规范

#### 1. GitHubTaskManager 实现要点

```python
# src/mcp_services/github/github_task_manager.py

from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from agents.mcp.server import MCPServerStdio
from src.base.task_manager import BaseTaskManager, BaseTask

@dataclass
class GitHubTask(BaseTask):
    """GitHub 特定的任务数据结构"""
    repository_url: Optional[str] = None
    fork_url: Optional[str] = None
    branch_name: Optional[str] = None
    pr_number: Optional[int] = None

class GitHubTaskManager(BaseTaskManager):
    def __init__(self, tasks_root: Path = None, model_name: str = None, 
                 api_key: str = None, base_url: str = None, 
                 github_token: str = None, timeout: int = 600):
        super().__init__(tasks_root, service="github")
        
        # GitHub 特定配置
        self.github_token = github_token
        self.timeout = timeout
        
        # 其他配置...
    
    async def _create_mcp_server(self) -> MCPServerStdio:
        """创建 GitHub MCP 服务器连接"""
        return MCPServerStdio(
            params={
                "command": "npx",
                "args": ["-y", "@github/mcp-server"],  # 假设的包名
                "env": {
                    "GITHUB_TOKEN": self.github_token,
                    "GITHUB_API_VERSION": "2022-11-28"
                },
            },
            client_session_timeout_seconds=120,
            cache_tools_list=True,
        )
    
    def discover_all_tasks(self) -> List[GitHubTask]:
        """发现所有 GitHub 相关任务"""
        # 实现任务发现逻辑
        pass
    
    def filter_tasks(self, task_filter: str) -> List[GitHubTask]:
        """基于条件过滤任务"""
        # 实现任务过滤逻辑
        pass
```

#### 2. GitHubStateManager 实现要点

```python
# src/mcp_services/github/github_state_manager.py

from typing import Optional, Tuple
import requests
from src.base.state_manager import BaseStateManager
from src.base.task_manager import BaseTask

class GitHubStateManager(BaseStateManager):
    def __init__(self, github_token: str, base_repo_owner: str = "mcpbench", 
                 test_org: str = "mcpbench-eval"):
        self.github_token = github_token
        self.base_repo_owner = base_repo_owner
        self.test_org = test_org
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        })
    
    def initialize(self, **kwargs):
        """初始化 GitHub 环境"""
        # 验证 token 有效性
        # 确认组织权限
        # 设置默认配置
        pass
    
    def set_up(self, task: BaseTask) -> bool:
        """为任务设置 GitHub 环境"""
        try:
            # 1. 确定源仓库
            source_repo = self._determine_source_repo(task.category)
            
            # 2. 创建 fork
            fork_url = self._create_fork(source_repo, task.name)
            task.repository_url = fork_url
            
            # 3. 创建任务分支
            branch_name = f"task-{task.category}-{task.task_id}"
            self._create_branch(fork_url, branch_name)
            task.branch_name = branch_name
            
            return True
        except Exception as e:
            logger.error(f"GitHub setup failed for {task.name}: {e}")
            return False
    
    def clean_up(self, task_data: dict = None, **kwargs) -> bool:
        """清理 GitHub 资源"""
        try:
            if task_data and 'repository_url' in task_data:
                # 删除 fork 或归档仓库
                self._cleanup_repository(task_data['repository_url'])
            return True
        except Exception as e:
            logger.error(f"GitHub cleanup failed: {e}")
            return False
    
    def _create_fork(self, source_repo: str, task_name: str) -> str:
        """创建仓库分叉"""
        # GitHub API 调用实现分叉
        pass
    
    def _create_branch(self, repo_url: str, branch_name: str):
        """创建新分支"""
        # GitHub API 调用创建分支
        pass
    
    def _cleanup_repository(self, repo_url: str):
        """清理仓库资源"""
        # 删除或归档仓库
        pass
```

#### 3. GitHubLoginHelper 实现要点

```python
# src/mcp_services/github/github_login_helper.py

from typing import Optional
from pathlib import Path
import requests
from src.base.login_helper import BaseLoginHelper

class GitHubLoginHelper(BaseLoginHelper):
    def __init__(self, token: Optional[str] = None, 
                 state_path: Optional[Path] = None):
        self.token = token
        self.state_path = state_path or Path.home() / ".mcpbench" / "github_auth.json"
    
    def login_and_save_state(self, **kwargs) -> bool:
        """GitHub Token 认证验证"""
        try:
            # 验证 token 有效性
            response = requests.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if response.status_code == 200:
                user_info = response.json()
                # 保存认证状态
                self._save_auth_state(user_info)
                return True
            
            return False
        except Exception as e:
            logger.error(f"GitHub authentication failed: {e}")
            return False
    
    def _save_auth_state(self, user_info: dict):
        """保存认证状态"""
        # 保存用户信息和权限范围
        pass
```

### 🔧 GitHub 服务工厂

```python
# 在 src/factory.py 中添加

class GitHubServiceFactory(ServiceFactory):
    """GitHub 服务工厂"""
    
    def create_task_manager(self, config: ServiceConfig, **kwargs) -> BaseTaskManager:
        from src.mcp_services.github.github_task_manager import GitHubTaskManager
        
        return GitHubTaskManager(
            tasks_root=kwargs.get("tasks_root"),
            model_name=kwargs.get("model_name"),
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url"),
            github_token=config.config["github_token"],
            timeout=kwargs.get("timeout", 600),
        )
    
    def create_state_manager(self, config: ServiceConfig, **kwargs) -> BaseStateManager:
        from src.mcp_services.github.github_state_manager import GitHubStateManager
        
        return GitHubStateManager(
            github_token=config.config["github_token"],
            base_repo_owner=config.config.get("base_repo_owner", "mcpbench"),
            test_org=config.config.get("test_org", "mcpbench-eval"),
        )
    
    def create_login_helper(self, config: ServiceConfig, **kwargs) -> BaseLoginHelper:
        from src.mcp_services.github.github_login_helper import GitHubLoginHelper
        
        return GitHubLoginHelper(
            token=config.config["github_token"],
            state_path=kwargs.get("state_path"),
        )
```

---

## 🐘 PostgreSQL MCP Server 实现

### 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│               PostgreSQL MCP Service                        │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │PostgresTaskMgr  │    │PostgresStateMgr │               │
│  │                 │    │                  │               │
│  │• Query Execution│    │• Schema Setup    │               │
│  │• MCP Integration│    │• Test Data Mgmt  │               │
│  │• Connection Mgmt│    │• Database Cleanup│               │
│  └─────────────────┘    └─────────────────┘                │
│                                                             │
│            ┌─────────────────┐                             │
│            │PostgresLoginHlpr│                             │
│            │                 │                             │
│            │• Connection Test│                             │
│            │• Credential Mgmt│                             │
│            │• SSL Config     │                             │
│            └─────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

### 🛠️ 组件实现规范

#### 1. PostgresTaskManager 实现要点

```python
# src/mcp_services/postgres/postgres_task_manager.py

import asyncio
import asyncpg
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from agents.mcp.server import MCPServerStdio
from src.base.task_manager import BaseTaskManager, BaseTask

@dataclass
class PostgresTask(BaseTask):
    """PostgreSQL 特定的任务数据结构"""
    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    test_tables: Optional[List[str]] = None

class PostgresTaskManager(BaseTaskManager):
    def __init__(self, tasks_root: Path = None, model_name: str = None, 
                 api_key: str = None, base_url: str = None,
                 db_host: str = "localhost", db_port: int = 5432,
                 db_user: str = None, db_password: str = None,
                 db_name: str = "mcpbench", timeout: int = 600):
        super().__init__(tasks_root, service="postgres")
        
        # PostgreSQL 连接配置
        self.db_config = {
            "host": db_host,
            "port": db_port,
            "user": db_user,
            "password": db_password,
            "database": db_name
        }
        self.timeout = timeout
    
    async def _create_mcp_server(self) -> MCPServerStdio:
        """创建 PostgreSQL MCP 服务器连接"""
        # 构建数据库连接 URL
        db_url = f"postgresql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
        
        return MCPServerStdio(
            params={
                "command": "python",
                "args": ["-m", "mcp_postgres_server"],  # 假设的 PostgreSQL MCP 服务器
                "env": {
                    "DATABASE_URL": db_url,
                    "POSTGRES_SSL_MODE": "prefer"
                },
            },
            client_session_timeout_seconds=120,
            cache_tools_list=True,
        )
    
    async def _setup_connection_pool(self):
        """设置异步连接池"""
        self.pool = await asyncpg.create_pool(**self.db_config, min_size=1, max_size=10)
    
    def discover_all_tasks(self) -> List[PostgresTask]:
        """发现所有 PostgreSQL 相关任务"""
        # 实现任务发现逻辑
        pass
    
    def filter_tasks(self, task_filter: str) -> List[PostgresTask]:
        """基于条件过滤任务"""
        # 实现任务过滤逻辑
        pass
```

#### 2. PostgresStateManager 实现要点

```python
# src/mcp_services/postgres/postgres_state_manager.py

import asyncio
import asyncpg
from typing import Optional, Dict, List
from pathlib import Path
from src.base.state_manager import BaseStateManager
from src.base.task_manager import BaseTask

class PostgresStateManager(BaseStateManager):
    def __init__(self, db_host: str = "localhost", db_port: int = 5432,
                 db_user: str = None, db_password: str = None,
                 template_db: str = "mcpbench_template"):
        self.db_config = {
            "host": db_host,
            "port": db_port,
            "user": db_user,
            "password": db_password
        }
        self.template_db = template_db
        self.pool = None
    
    async def initialize(self, **kwargs):
        """初始化 PostgreSQL 环境"""
        # 创建连接池
        self.pool = await asyncpg.create_pool(**self.db_config)
        
        # 验证模板数据库存在
        await self._ensure_template_database()
    
    def set_up(self, task: BaseTask) -> bool:
        """为任务设置 PostgreSQL 环境"""
        try:
            # 异步运行设置
            return asyncio.run(self._async_setup(task))
        except Exception as e:
            logger.error(f"PostgreSQL setup failed for {task.name}: {e}")
            return False
    
    async def _async_setup(self, task: BaseTask) -> bool:
        """异步设置任务环境"""
        # 1. 创建任务专用数据库
        task_db_name = f"mcpbench_task_{task.category}_{task.task_id}"
        await self._create_task_database(task_db_name)
        task.database_name = task_db_name
        
        # 2. 复制模板 schema
        await self._copy_template_schema(task_db_name, task.category)
        
        # 3. 插入测试数据
        await self._setup_test_data(task_db_name, task)
        
        return True
    
    def clean_up(self, task_data: dict = None, **kwargs) -> bool:
        """清理 PostgreSQL 资源"""
        try:
            if task_data and 'database_name' in task_data:
                asyncio.run(self._drop_task_database(task_data['database_name']))
            return True
        except Exception as e:
            logger.error(f"PostgreSQL cleanup failed: {e}")
            return False
    
    async def _create_task_database(self, db_name: str):
        """创建任务专用数据库"""
        # 连接到 postgres 系统数据库创建新数据库
        pass
    
    async def _copy_template_schema(self, task_db_name: str, category: str):
        """复制模板 schema 到任务数据库"""
        # 根据任务类别复制相应的表结构和数据
        pass
    
    async def _setup_test_data(self, task_db_name: str, task: BaseTask):
        """设置测试数据"""
        # 插入任务特定的测试数据
        pass
    
    async def _drop_task_database(self, db_name: str):
        """删除任务数据库"""
        # 安全删除任务数据库
        pass
```

#### 3. PostgresLoginHelper 实现要点

```python
# src/mcp_services/postgres/postgres_login_helper.py

import asyncpg
from typing import Optional
from pathlib import Path
from src.base.login_helper import BaseLoginHelper

class PostgresLoginHelper(BaseLoginHelper):
    def __init__(self, db_host: str = "localhost", db_port: int = 5432,
                 db_user: str = None, db_password: str = None,
                 state_path: Optional[Path] = None):
        self.db_config = {
            "host": db_host,
            "port": db_port,
            "user": db_user,
            "password": db_password,
            "database": "postgres"  # 连接到系统数据库进行验证
        }
        self.state_path = state_path or Path.home() / ".mcpbench" / "postgres_auth.json"
    
    def login_and_save_state(self, **kwargs) -> bool:
        """PostgreSQL 连接验证"""
        try:
            # 测试数据库连接
            import asyncio
            return asyncio.run(self._test_connection())
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """异步测试数据库连接"""
        try:
            conn = await asyncpg.connect(**self.db_config)
            
            # 执行简单查询验证连接
            result = await conn.fetchval("SELECT version()")
            logger.info(f"PostgreSQL version: {result}")
            
            # 检查权限
            await self._check_permissions(conn)
            
            await conn.close()
            
            # 保存连接状态
            self._save_connection_state()
            
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def _check_permissions(self, conn):
        """检查数据库权限"""
        # 验证用户是否有创建数据库的权限
        pass
    
    def _save_connection_state(self):
        """保存连接状态信息"""
        # 保存连接配置和权限信息
        pass
```

### 🔧 PostgreSQL 服务工厂

```python
# 在 src/factory.py 中添加

class PostgresServiceFactory(ServiceFactory):
    """PostgreSQL 服务工厂"""
    
    def create_task_manager(self, config: ServiceConfig, **kwargs) -> BaseTaskManager:
        from src.mcp_services.postgres.postgres_task_manager import PostgresTaskManager
        
        return PostgresTaskManager(
            tasks_root=kwargs.get("tasks_root"),
            model_name=kwargs.get("model_name"),
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url"),
            db_host=config.config["db_host"],
            db_port=int(config.config["db_port"]),
            db_user=config.config["db_user"],
            db_password=config.config["db_password"],
            db_name=config.config["db_name"],
            timeout=kwargs.get("timeout", 600),
        )
    
    def create_state_manager(self, config: ServiceConfig, **kwargs) -> BaseStateManager:
        from src.mcp_services.postgres.postgres_state_manager import PostgresStateManager
        
        return PostgresStateManager(
            db_host=config.config["db_host"],
            db_port=int(config.config["db_port"]),
            db_user=config.config["db_user"],
            db_password=config.config["db_password"],
            template_db=config.config.get("template_db", "mcpbench_template"),
        )
    
    def create_login_helper(self, config: ServiceConfig, **kwargs) -> BaseLoginHelper:
        from src.mcp_services.postgres.postgres_login_helper import PostgresLoginHelper
        
        return PostgresLoginHelper(
            db_host=config.config["db_host"],
            db_port=int(config.config["db_port"]),
            db_user=config.config["db_user"],
            db_password=config.config["db_password"],
            state_path=kwargs.get("state_path"),
        )
```

## 🔧 服务注册和配置

### 环境变量配置更新

在 `.mcp_env` 文件中添加：

```bash
# GitHub 配置
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_BASE_REPO_OWNER=mcpbench
GITHUB_TEST_ORG=mcpbench-eval

# PostgreSQL 配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mcpbench_admin
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=mcpbench
POSTGRES_TEMPLATE_DB=mcpbench_template
```

### 工厂注册更新

在 `src/factory.py` 的 `MCPServiceFactory` 中注册新服务：

```python
class MCPServiceFactory:
    _factories = {
        "notion": NotionServiceFactory(),
        "github": GitHubServiceFactory(),
        "postgres": PostgresServiceFactory(),
    }
    
    _service_configs = {
        "notion": ServiceConfig(
            service_name="notion",
            additional_vars={
                "source_api_key": "NOTION_SOURCE_API_KEY",
                "eval_api_key": "NOTION_EVAL_API_KEY",
            }
        ),
        "github": ServiceConfig(
            service_name="github", 
            additional_vars={
                "github_token": "GITHUB_TOKEN",
                "base_repo_owner": "GITHUB_BASE_REPO_OWNER",
                "test_org": "GITHUB_TEST_ORG",
            }
        ),
        "postgres": ServiceConfig(
            service_name="postgres",
            additional_vars={
                "db_host": "POSTGRES_HOST",
                "db_port": "POSTGRES_PORT", 
                "db_user": "POSTGRES_USER",
                "db_password": "POSTGRES_PASSWORD",
                "db_name": "POSTGRES_DB",
                "template_db": "POSTGRES_TEMPLATE_DB",
            }
        ),
    }
```

## 🚀 实施步骤总结

### GitHub MCP Server 实施顺序

1. **🏗️ 创建基础结构**
   - 创建 `src/mcp_services/github/` 目录
   - 实现 `__init__.py` 导出模块

2. **🔐 实现认证模块** 
   - 实现 `GitHubLoginHelper`
   - 测试 GitHub token 验证

3. **🔧 实现状态管理**
   - 实现 `GitHubStateManager`
   - 测试仓库分叉和分支创建

4. **⚡ 实现任务管理**
   - 实现 `GitHubTaskManager`
   - 集成 GitHub MCP 服务器

5. **🏭 注册服务工厂**
   - 创建 `GitHubServiceFactory`
   - 更新主工厂注册

### PostgreSQL MCP Server 实施顺序

1. **🏗️ 创建基础结构**
   - 创建 `src/mcp_services/postgres/` 目录
   - 安装 `asyncpg` 依赖

2. **🔐 实现连接管理**
   - 实现 `PostgresLoginHelper`
   - 测试数据库连接和权限

3. **🗄️ 实现状态管理**
   - 实现 `PostgresStateManager`
   - 测试数据库和 schema 创建

4. **⚡ 实现任务管理**
   - 实现 `PostgresTaskManager`  
   - 集成 PostgreSQL MCP 服务器

5. **🏭 注册服务工厂**
   - 创建 `PostgresServiceFactory`
   - 更新主工厂注册

## 🔍 测试和验证

### 单元测试建议

- ✅ 每个组件的独立功能测试
- ✅ MCP 服务器连接测试
- ✅ 状态管理的设置和清理测试
- ✅ 错误处理和重试机制测试
- ✅ 配置加载和验证测试

### 集成测试建议

- ✅ 端到端任务执行流程
- ✅ 多服务并行执行测试
- ✅ 资源清理完整性验证
- ✅ 性能和稳定性测试 