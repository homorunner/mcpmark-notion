# MCPBench 代码结构文档

## 项目概览

MCPBench 是一个评测框架，用于评测不同 LLM 在 Agent 框架下通过调用 MCP (Model Context Protocol) tools 完成任务的能力。项目采用模块化设计，支持多种 MCP 服务（Notion、GitHub、PostgreSQL）。

## 核心架构

### 入口文件
- **`pipeline.py`**: 主入口点，解析命令行参数，调用评测流程
- **`src/agent.py`**: 统一的 Agent 实现，负责 LLM 和 MCP server 管理

### 核心组件

#### 1. 评测引擎 (`src/evaluator.py`)
- **`MCPEvaluator`**: 主评测类，协调整个评测流程
- 四阶段评测流程：环境初始化 → 任务执行 → 任务评测 → 环境清理
- 支持任务恢复和重试机制

#### 2. Agent 管理 (`src/agent.py`)
- **`MCPAgent`**: 统一 Agent 实现
- 功能：模型提供商管理、MCP server 创建、LLM 推理执行、Token 统计
- 支持流式响应和错误重试

#### 3. 工厂模式 (`src/factory.py`)
- **`MCPServiceFactory`**: 主工厂类，创建服务特定组件
- **`ServiceConfig`**: 服务配置容器，管理 API 密钥和环境变量
- 支持的服务：Notion、GitHub、PostgreSQL（开发中）

#### 4. 模型配置 (`src/model_config.py`)
- **`ModelConfig`**: 模型配置管理
- 支持多种模型提供商：OpenAI、DeepSeek、Anthropic、Google、Moonshot、Grok
- 自动检测 API 密钥和基础 URL

## 基础抽象层 (`src/base/`)

### 任务管理 (`task_manager.py`)
- **`BaseTaskManager`**: 任务管理抽象基类，使用模板方法模式
- **`BaseTask`**: 任务数据结构
- 核心功能：任务发现、过滤、验证、指令格式化

### 状态管理 (`state_manager.py`)
- **`BaseStateManager`**: 状态管理抽象基类
- **`InitialStateInfo`**: 初始状态信息数据结构
- 核心功能：初始状态创建、资源跟踪、清理

### 登录助手 (`login_helper.py`)
- **`BaseLoginHelper`**: 登录助手抽象基类
- 提供服务登录和状态管理

## MCP 服务实现 (`src/mcp_services/`)

### Notion 服务 (`src/mcp_services/notion/`)
```
notion/
├── __init__.py
├── notion_login_helper.py     # Notion 登录管理
├── notion_state_manager.py    # Notion 状态管理
└── notion_task_manager.py     # Notion 任务管理
```

### GitHub 服务 (`src/mcp_services/github/`)
```
github/
├── __init__.py
├── github_login_helper.py     # GitHub 登录管理
├── github_state_manager.py    # GitHub 状态管理
└── github_task_manager.py     # GitHub 任务管理
```

### PostgreSQL 服务 (`src/mcp_services/postgres/`)
```
postgres/
└── __init__.py               # 占位符，待实现
```

## 支持模块

### 结果报告 (`src/results_reporter.py`)
- **`ResultsReporter`**: 结果报告生成
- **`EvaluationReport`**: 评测报告数据结构
- **`TaskResult`**: 任务结果数据结构

### 日志系统 (`src/logger.py`)
- 统一日志配置和管理
- 支持不同级别的日志输出

## 数据流

```
用户命令 → pipeline.py → MCPEvaluator → 工厂创建组件 → Agent执行 → 结果报告
    ↓           ↓              ↓              ↓           ↓           ↓
 解析参数   初始化评测器   创建管理器    MCP Server   LLM推理    保存结果
```

## 设计模式

1. **模板方法模式**: `BaseTaskManager` 和 `BaseStateManager` 定义通用流程
2. **工厂模式**: `MCPServiceFactory` 创建服务特定组件
3. **策略模式**: 不同的 MCP 服务提供不同的实现策略
4. **依赖注入**: 通过工厂注入服务特定实现

## 扩展性设计

- **服务独立**: 每个 MCP 服务有独立的实现模块
- **接口统一**: 通过抽象基类统一接口
- **配置分离**: 环境变量和配置文件分离
- **模块化**: 核心功能模块化，便于测试和维护