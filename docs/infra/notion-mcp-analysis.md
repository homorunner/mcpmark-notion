# Notion MCP Server 实现分析

## 📋 概述

Notion MCP Server 是 MCPBench 项目中的参考实现，展示了如何集成一个完整的 MCP 服务。该实现结合了 Notion API、Playwright 浏览器自动化和异步任务执行。

## 🏗️ 组件架构

```
┌─────────────────────────────────────────────────────────────┐
│                Notion MCP Service                            │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │NotionTaskManager│    │NotionStateManager│               │
│  │                 │    │                  │               │
│  │• Task Discovery │    │• Template Mgmt   │               │
│  │• MCP Integration│    │• Playwright Auto │               │
│  │• Async Execution│    │• Resource Cleanup│               │
│  └─────────────────┘    └─────────────────┘                │
│                                                             │
│            ┌─────────────────┐                             │
│            │NotionLoginHelper│                             │
│            │                 │                             │
│            │• Browser Login  │                             │
│            │• Session Persist│                             │
│            │• Multi-browser  │                             │
│            └─────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 核心组件详解

### 1. NotionTaskManager - 任务执行引擎

**文件位置**: `src/mcp_services/notion/notion_task_manager.py`

#### 关键功能模块

##### 🔍 任务发现 (Task Discovery)
```python
def discover_all_tasks(self) -> List[NotionTask]:
    """发现所有可用的任务文件"""
    # 扫描 tasks/ 目录
    # 按类别和任务ID组织
    # 返回结构化任务列表
```

##### 🤖 MCP 服务器集成
```python
async def _create_mcp_server(self) -> MCPServerStdio:
    return MCPServerStdio(
        params={
            "command": "npx",
            "args": ["-y", "@notionhq/notion-mcp-server"],
            "env": {
                "OPENAPI_MCP_HEADERS": (
                    '{"Authorization": "Bearer ' + eval_key + '", '
                    '"Notion-Version": "2022-06-28"}'
                )
            },
        },
        client_session_timeout_seconds=120,
        cache_tools_list=True,
    )
```

**集成特点**:
- 使用 `@notionhq/notion-mcp-server` npm 包
- 通过环境变量传递 API 密钥
- 支持工具缓存优化性能
- 设置合理的超时时间

##### ⚡ 异步任务执行
```python
async def _run_single_task_async(self, agent: Agent, task_content: str):
    # 1. 准备对话上下文
    conversation = [{"content": task_content, "role": "user"}]
    
    # 2. 流式执行任务
    result = Runner.run_streamed(agent, max_turns=20, input=conversation)
    
    # 3. 实时处理事件流
    async for event in result.stream_events():
        # 处理不同类型的事件 (token deltas, tool calls, etc.)
        
    # 4. 收集执行结果和统计信息
    return result.to_input_list(), token_usage, turn_count
```

**执行特性**:
- 实时事件流处理
- Token 使用统计
- 工具调用监控
- 自动重试机制

##### 🔄 重试机制
```python
# 配置参数
self.max_retries: int = 3
self.retry_backoff: float = 5.0

# 重试逻辑处理网络错误和临时性故障
```

### 2. NotionStateManager - 环境状态管理

**文件位置**: `src/mcp_services/notion/notion_state_manager.py`

#### 核心职责

##### 🔄 模板管理
- **模板复制**: 复制源模板到评估环境
- **页面重命名**: 为每个任务创建唯一标识
- **层次结构**: 维护页面的父子关系

##### 🎭 Playwright 自动化
```python
def _duplicate_template_for_task(self, template_url: str, category: str, task_name: str):
    # 1. 打开模板页面
    page.goto(template_url)
    
    # 2. 触发复制操作
    page.click(PAGE_MENU_BUTTON_SELECTOR)
    page.click(DUPLICATE_WITH_CONTENT_SELECTOR)
    
    # 3. 移动到指定位置
    self._move_current_page_to_env(page)
    
    # 4. 重命名页面
    self._rename_page_for_task(page, category, task_name)
```

**自动化特点**:
- 精确的 CSS 选择器定位
- 智能等待和超时处理
- 错误恢复和重试
- 多浏览器支持 (Firefox/Chromium)

##### 🧹 资源清理
```python
def clean_up(self, template_id: str = None, **kwargs) -> bool:
    """清理评估后的资源"""
    # 归档或删除临时页面
    # 释放浏览器资源
    # 清理临时文件
```

### 3. NotionLoginHelper - 认证管理

**文件位置**: `src/mcp_services/notion/notion_login_helper.py`

#### 主要功能

##### 🔐 浏览器登录自动化
```python
def login_and_save_state(self, *, url: str = None, **kwargs) -> bool:
    # 1. 启动浏览器
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=self.headless)
        
        # 2. 加载已有会话或创建新会话
        context = browser.new_context()
        
        # 3. 导航到登录页面
        page = context.new_page()
        page.goto(url or "https://www.notion.so")
        
        # 4. 等待用户完成登录
        # 5. 保存认证状态
```

##### 💾 会话持久化
- 保存浏览器状态到本地文件
- 支持会话复用，避免重复登录
- 跨浏览器的状态兼容性

## 🔧 配置和依赖

### 环境变量配置
```bash
# .mcp_env
NOTION_SOURCE_API_KEY=secret_...    # 源模板访问密钥
NOTION_EVAL_API_KEY=secret_...      # 评估环境密钥
```

### 关键依赖
- `notion-client`: Notion 官方 Python SDK
- `playwright`: 浏览器自动化
- `agents`: MCP 代理框架
- `openai`: LLM 模型集成

## 📊 性能特征

### 执行统计
- **Token 使用监控**: 详细的输入/输出 token 统计
- **对话轮数追踪**: 多轮对话的完整记录
- **工具调用日志**: MCP 工具使用情况

### 优化策略
- **工具缓存**: 避免重复加载 MCP 工具列表
- **异步执行**: 非阻塞的任务处理
- **连接复用**: MCP 服务器连接复用
- **智能重试**: 指数退避的重试策略

## 🚀 扩展要点

### 对 GitHub/PostgreSQL 的启示

1. **MCP 服务器选择**:
   - GitHub: 可使用 `@github/mcp-server` 或自定义实现
   - PostgreSQL: 需要实现或寻找 PostgreSQL MCP 服务器

2. **状态管理差异**:
   - GitHub: Repository 分叉、Branch 创建、PR 管理
   - PostgreSQL: 数据库schema、测试数据、连接池管理

3. **认证方式**:
   - GitHub: Token-based 认证，无需浏览器
   - PostgreSQL: 数据库连接认证

4. **资源清理**:
   - GitHub: 删除临时 repository/branch
   - PostgreSQL: 清理测试数据、关闭连接

## 🔍 代码质量特点

- ✅ **类型注解完整**: 全面的 Python 类型提示
- ✅ **异常处理健全**: 完善的错误捕获和处理
- ✅ **日志记录详细**: 分级的日志输出
- ✅ **可测试性强**: 清晰的接口分离
- ✅ **文档注释规范**: 详细的 docstring 说明 