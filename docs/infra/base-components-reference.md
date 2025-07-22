# 基础组件接口参考

## 📋 概述

MCPBench 框架定义了三个核心的抽象基类，为所有 MCP 服务提供统一的接口规范。这些基类位于 `src/base/` 目录下，确保了不同服务实现的一致性和互操作性。

## 🏗️ 基础架构关系

```
┌─────────────────────────────────────────────────────────────┐
│                    Abstract Base Classes                    │
│                                                             │
│  ┌──────────────┐ ┌───────────────┐ ┌────────────────┐     │
│  │BaseTask      │ │BaseState      │ │BaseLogin       │     │
│  │Manager       │ │Manager        │ │Helper          │     │
│  │              │ │               │ │                │     │
│  │• Task Discovery   │• Environment Setup │• Authentication │     │
│  │• Execution   │ │• Resource Mgmt│ │• Session Mgmt  │     │
│  │• Filtering   │ │• Cleanup      │ │• State Persist │     │
│  └──────────────┘ └───────────────┘ └────────────────┘     │
│                          ⬇                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │           Service-Specific Implementations              ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   ││
│  │  │   Notion    │ │   GitHub    │ │   PostgreSQL    │   ││
│  │  │ Components  │ │ Components  │ │   Components    │   ││
│  │  └─────────────┘ └─────────────┘ └─────────────────┘   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 🎯 BaseTaskManager 抽象类

**位置**: `src/base/task_manager.py`

### 接口定义

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path

class BaseTaskManager(ABC):
    """任务管理器抽象基类"""
    
    def __init__(self, tasks_root: Path = None, service: str = "notion"):
        self.tasks_root = Path(tasks_root) if tasks_root else None
        self.service = service

    @abstractmethod
    def discover_all_tasks(self) -> List[BaseTask]:
        """发现所有可用的任务"""
        pass

    @abstractmethod
    def get_categories(self) -> List[str]:
        """获取所有任务类别列表"""
        pass

    @abstractmethod
    def filter_tasks(self, task_filter: str) -> List[BaseTask]:
        """根据过滤条件筛选任务"""
        pass

    @abstractmethod
    def run_tasks(self, tasks: List[BaseTask], **kwargs) -> List[BaseTaskResult]:
        """执行任务列表"""
        pass
```

### 核心职责

1. **📋 任务发现**: 扫描和识别可执行的任务
2. **🔍 任务过滤**: 支持灵活的任务筛选机制
3. **⚡ 任务执行**: 协调 MCP 服务器和 AI 代理执行任务
4. **📊 结果收集**: 收集和格式化执行结果

### 实现要点

#### 任务发现模式
```python
def discover_all_tasks(self) -> List[BaseTask]:
    """标准任务发现实现模式"""
    tasks = []
    if not self.tasks_root.exists():
        return tasks
    
    # 按服务过滤目录
    service_dirs = [d for d in self.tasks_root.iterdir() 
                   if d.is_dir() and d.name == self.service]
    
    for service_dir in service_dirs:
        # 扫描类别目录
        for category_dir in service_dir.iterdir():
            if category_dir.is_dir():
                tasks.extend(self._discover_category_tasks(category_dir))
    
    return sorted(tasks, key=lambda t: (t.category, t.task_id))
```

#### MCP 服务器集成模式
```python
async def _create_mcp_server(self) -> MCPServerStdio:
    """MCP 服务器创建的标准模式"""
    return MCPServerStdio(
        params={
            "command": "npx",  # 或其他启动命令
            "args": ["-y", "@service/mcp-server"],
            "env": {
                # 服务特定的环境变量
            },
        },
        client_session_timeout_seconds=120,
        cache_tools_list=True,
    )
```

### 扩展指导

**必须实现的方法**:
- ✅ `discover_all_tasks()`: 任务发现逻辑
- ✅ `get_categories()`: 类别枚举
- ✅ `filter_tasks()`: 过滤逻辑
- ✅ `run_tasks()`: 执行协调

**可选扩展的功能**:
- 🔄 重试机制配置
- 📊 性能监控和统计
- 🔧 自定义 MCP 服务器参数
- 📝 详细的执行日志

---

## 🏛️ BaseStateManager 抽象类

**位置**: `src/base/state_manager.py`

### 接口定义

```python
from abc import ABC, abstractmethod
from .task_manager import BaseTask

class BaseStateManager(ABC):
    """状态管理器抽象基类"""
    
    def __init__(self):
        pass

    @abstractmethod
    def initialize(self, **kwargs):
        """初始化状态管理器"""
        pass

    @abstractmethod
    def clean_up(self, **kwargs):
        """清理资源"""
        pass

    @abstractmethod
    def set_up(self, task: BaseTask) -> bool:
        """为特定任务设置环境状态"""
        pass
```

### 核心职责

1. **🏗️ 环境准备**: 为任务执行准备必要的环境
2. **🔄 资源管理**: 管理临时资源的生命周期
3. **🧹 资源清理**: 任务完成后的清理工作
4. **⚖️ 状态隔离**: 确保不同任务间的状态独立

### 实现模式

#### 设置阶段模式
```python
def set_up(self, task: BaseTask) -> bool:
    """标准设置流程"""
    try:
        # 1. 验证前置条件
        if not self._validate_preconditions(task):
            return False
        
        # 2. 准备资源
        resources = self._prepare_resources(task)
        
        # 3. 配置环境
        self._configure_environment(task, resources)
        
        # 4. 验证设置成功
        return self._verify_setup(task)
        
    except Exception as e:
        logger.error(f"Setup failed for {task.name}: {e}")
        return False
```

#### 清理阶段模式
```python
def clean_up(self, **kwargs) -> bool:
    """标准清理流程"""
    try:
        # 1. 收集需要清理的资源
        resources = self._identify_cleanup_resources(kwargs)
        
        # 2. 按优先级清理
        for resource in sorted(resources, key=lambda r: r.priority):
            self._cleanup_resource(resource)
        
        # 3. 验证清理完成
        return self._verify_cleanup()
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return False
```

### 服务特定实现示例

#### Notion 状态管理
- 🔄 页面模板复制
- 📝 页面重命名和移动
- 🎭 Playwright 浏览器自动化

#### GitHub 状态管理  
- 🍴 仓库分叉 (Fork)
- 🌿 分支创建和管理
- 📬 Pull Request 生命周期

#### PostgreSQL 状态管理
- 🗄️ 测试数据库创建
- 📋 Schema 复制和配置
- 🔌 连接池管理

---

## 🔐 BaseLoginHelper 抽象类

**位置**: `src/base/login_helper.py`

### 接口定义

```python
from abc import ABC, abstractmethod

class BaseLoginHelper(ABC):
    """登录助手抽象基类"""
    
    @abstractmethod
    def login_and_save_state(self, **kwargs) -> bool:
        """执行登录并保存认证状态"""
        pass
```

### 核心职责

1. **🔐 身份认证**: 处理服务特定的认证流程
2. **💾 状态持久化**: 保存和恢复认证状态
3. **🔄 会话管理**: 管理认证会话的生命周期
4. **🛡️ 安全存储**: 安全地存储敏感的认证信息

### 实现模式

#### 通用认证流程
```python
def login_and_save_state(self, **kwargs) -> bool:
    """标准认证流程"""
    try:
        # 1. 检查现有认证状态
        if self._check_existing_auth():
            return True
        
        # 2. 执行认证流程
        auth_result = self._perform_authentication(**kwargs)
        
        if auth_result:
            # 3. 保存认证状态
            self._save_authentication_state(auth_result)
            
            # 4. 验证认证有效性
            return self._verify_authentication()
        
        return False
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return False
```

#### 状态持久化模式
```python
def _save_authentication_state(self, auth_data: dict):
    """安全存储认证状态"""
    # 1. 加密敏感信息
    encrypted_data = self._encrypt_sensitive_data(auth_data)
    
    # 2. 保存到安全位置
    auth_file = self.state_path or self._get_default_auth_path()
    
    # 3. 设置适当的文件权限
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    auth_file.write_text(json.dumps(encrypted_data))
    auth_file.chmod(0o600)  # 仅用户可读写
```

### 服务特定实现方式

#### Notion 认证方式
- 🎭 **Playwright 浏览器自动化**: 模拟用户登录流程
- 🍪 **Cookie 会话保存**: 持久化浏览器会话状态
- 🔑 **API 密钥验证**: 验证 Notion API 密钥有效性

#### GitHub 认证方式
- 🎫 **Personal Access Token**: 基于 token 的 API 认证
- 🔐 **OAuth 应用流程**: 支持 OAuth 认证流程
- ✅ **权限范围验证**: 验证 token 权限范围

#### PostgreSQL 认证方式
- 🔗 **连接字符串验证**: 测试数据库连接有效性
- 🏆 **权限检查**: 验证用户数据库操作权限
- 🔧 **SSL 配置**: 支持 SSL 连接配置

---

## 🎯 BaseTask 数据模型

**位置**: `src/base/task_manager.py`

### 基础数据结构

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class BaseTask:
    """任务数据模型基类"""
    task_instruction_path: Path
    task_verification_path: Path
    service: str
    category: str
    task_id: int

    @property
    def name(self) -> str:
        """任务完整名称"""
        return f"{self.category}/task_{self.task_id}"

    def get_task_instruction(self) -> str:
        """读取任务指令内容"""
        if self.task_instruction_path.exists():
            return self.task_instruction_path.read_text(encoding="utf-8")
        return ""
```

### 扩展数据模型

每个服务可以扩展基础任务模型：

#### Notion 任务扩展
```python
@dataclass
class NotionTask(BaseTask):
    original_template_url: Optional[str] = None
    duplicated_template_url: Optional[str] = None
    duplicated_template_id: Optional[str] = None
```

#### GitHub 任务扩展
```python  
@dataclass
class GitHubTask(BaseTask):
    repository_url: Optional[str] = None
    fork_url: Optional[str] = None
    branch_name: Optional[str] = None
    pr_number: Optional[int] = None
```

#### PostgreSQL 任务扩展
```python
@dataclass
class PostgresTask(BaseTask):
    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    test_tables: Optional[List[str]] = None
```

---

## 📊 BaseTaskResult 结果模型

### 基础结果结构

```python
@dataclass
class BaseTaskResult:
    """任务执行结果基类"""
    success: bool = False
    execution_time: float = 0.0
    service: str = "notion"
    category: str = "online_resume"
    task_id: int = 1
    error_message: Optional[str] = None
    conversation: Optional[dict] = None

    @property
    def status(self) -> str:
        """执行状态描述"""
        return "PASS" if self.success else "FAIL"
```

### 结果扩展模式

服务特定的结果信息：

```python
@dataclass
class DetailedTaskResult(BaseTaskResult):
    # 性能指标
    token_usage: Optional[Dict[str, int]] = None
    turn_count: Optional[int] = None
    
    # 服务特定信息
    mcp_tool_calls: Optional[List[str]] = None
    resource_cleanup_status: bool = True
    
    # 调试信息  
    execution_log: Optional[List[str]] = None
    intermediate_states: Optional[List[dict]] = None
```

---

## 🔧 实现最佳实践

### 1. 错误处理策略

```python
class ServiceManagerBase:
    def __init__(self):
        self.max_retries = 3
        self.retry_backoff = 5.0
    
    def _execute_with_retry(self, operation, *args, **kwargs):
        """通用重试装饰器"""
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except RetryableException as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.retry_backoff * (attempt + 1)
                time.sleep(wait_time)
            except NonRetryableException:
                raise
```

### 2. 配置验证模式

```python
def validate_configuration(self, config: dict) -> bool:
    """配置验证通用模式"""
    required_keys = self.get_required_config_keys()
    
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ConfigurationError(f"Missing required config keys: {missing_keys}")
    
    # 执行服务特定的配置验证
    return self._validate_service_specific_config(config)
```

### 3. 日志记录标准

```python
import logging
from src.logger import get_logger

class ServiceComponent:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def _log_operation_start(self, operation: str, **context):
        self.logger.info(f"Starting {operation}", extra=context)
    
    def _log_operation_success(self, operation: str, duration: float, **context):
        self.logger.info(f"Completed {operation} in {duration:.2f}s", extra=context)
    
    def _log_operation_error(self, operation: str, error: Exception, **context):
        self.logger.error(f"Failed {operation}: {error}", extra=context, exc_info=True)
```

### 4. 资源管理模式

```python
class ResourceManager:
    def __init__(self):
        self._active_resources = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup_all_resources()
    
    def register_resource(self, resource, cleanup_func):
        """注册需要清理的资源"""
        self._active_resources.append((resource, cleanup_func))
    
    def _cleanup_all_resources(self):
        """清理所有注册的资源"""
        for resource, cleanup_func in reversed(self._active_resources):
            try:
                cleanup_func(resource)
            except Exception as e:
                self.logger.error(f"Resource cleanup failed: {e}")
```

## 🎯 集成检查清单

在实现新的 MCP 服务时，请确保：

### ✅ 接口完整性
- [ ] 实现所有抽象方法
- [ ] 遵循方法签名规范  
- [ ] 正确处理返回值类型

### ✅ 错误处理
- [ ] 实现重试机制
- [ ] 提供详细错误信息
- [ ] 优雅降级处理

### ✅ 资源管理
- [ ] 正确的资源创建和清理
- [ ] 避免资源泄漏
- [ ] 超时和限制机制

### ✅ 配置管理
- [ ] 环境变量验证
- [ ] 敏感信息安全存储
- [ ] 配置文档完整

### ✅ 测试覆盖
- [ ] 单元测试完整性
- [ ] 集成测试场景
- [ ] 错误场景测试
- [ ] 性能基准测试

### ✅ 文档质量  
- [ ] API 文档完整
- [ ] 使用示例清晰
- [ ] 故障排除指南
- [ ] 配置参考文档 