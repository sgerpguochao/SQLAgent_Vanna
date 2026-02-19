# NL2SQL 数据分析系统 - 详细架构说明

## 一、系统整体架构

### 1.1 项目顶层目录结构

```
SQLAgent_Vanna_1/
├── backend/               # 后端服务
│   ├── vanna/           # NL2SQL 核心服务
│   ├── playground/        # 测试脚本
│   └── data/             # 初始数据
├── frontend/              # 前端应用 (React)
├── local_embedding/       # Jina Embedding 服务
├── milvus-deployment/     # Milvus 部署配置
└── middleware_info/       # 部署文档
```

---

## 二、业务功能模块（按业务划分）

### 2.1 对话服务模块 - 核心业务

| 业务功能 | 代码位置 | 说明 |
|---------|----------|------|
| 对话 API 入口 | `backend/vanna/api_server.py` | `/api/v1/chat` 接口 |
| Agent 核心 | `backend/vanna/react_agent.py` | LangGraph Agent 定义 |
| NL2SQL Agent | `backend/vanna/src/Improve/agent/nl2sql_agent.py` | 具体业务逻辑 |

**核心文件说明：**

- `api_server.py`：FastAPI 服务入口，定义所有 REST API 接口
- `react_agent.py`：LangGraph Agent 工作流定义
- `nl2sql_agent.py`：NL2SQL 领域的 Agent 核心逻辑

### 2.2 数据查询模块

| 业务功能 | 代码位置 | 说明 |
|---------|----------|------|
| SQL 执行工具 | `backend/vanna/src/Improve/tools/database_tools.py` | `execute_sql` 工具 |
| SQL 查询接口 | `backend/vanna/api_server.py` | `/api/query` 接口 |

**核心功能：**
- 执行用户输入的 SQL 查询
- 支持多条 SQL 顺序执行
- SQL 语法检查和错误处理
- 查询结果缓存和格式转换

### 2.3 RAG 检索模块

| 业务功能 | 代码位置 | 说明 |
|---------|----------|------|
| RAG 工具 | `backend/vanna/src/Improve/tools/rag_tools.py` | `get_table_schema`, `get_ddl`, `get_documents` |
| 向量客户端 | `backend/vanna/src/Improve/clients/vanna_client.py` | Milvus 连接封装 |
| Embedding 提供商 | `backend/vanna/src/Improve/clients/embedding_providers.py` | Jina Embedding 集成 |

**RAG 检索流程：**
1. 用户提问 → 转换为向量
2. 在 Milvus 中检索相似 SQL 示例
3. 检索相关表结构 (DDL)
4. 检索业务文档
5. 将检索结果作为上下文提供给 LLM

### 2.4 训练数据管理模块

| 业务功能 | 代码位置 | 说明 |
|---------|----------|------|
| 训练数据 API | `backend/vanna/api_server.py` | `/api/v1/training/*` 接口 |
| 训练数据处理 | `backend/vanna/src/Improve/agent/post_training.py` | 训练决策逻辑 |

**功能说明：**
- 添加 SQL 查询示例（问题 + SQL 语句）
- 添加 DDL 表结构定义
- 添加表文档说明
- 自动学习用户确认的查询

### 2.5 数据可视化模块

| 业务功能 | 代码位置 | 说明 |
|---------|----------|------|
| 图表生成 | 后端返回 `chartconfig` JSON | LLM 自动生成 |
| 图表展示 | `frontend/src/components/ResultsPanel.tsx` | Chart.js 渲染 |
| 数据表格 | `frontend/src/components/QueryResultDisplay.tsx` | 结果展示 |

**可视化流程：**
1. LLM 生成 SQL 并执行
2. LLM 分析结果，生成 `chartconfig` JSON 配置
3. 前端接收配置，使用 Chart.js 渲染图表

### 2.6 数据源管理模块

| 业务功能 | 代码位置 | 说明 |
|---------|----------|------|
| 数据库连接 | `backend/vanna/api_server.py` | `/api/v1/database/*` 接口 |
| 表结构获取 | `backend/vanna/src/Improve/tools/rag_tools.py` | `get_table_schema` |

---

## 三、前后端入口文件

### 3.1 前端入口

| 文件 | 说明 |
|------|------|
| `frontend/src/App.tsx` | 应用主入口 |
| `frontend/src/NewApp.tsx` | 新版应用入口 |
| `frontend/src/main.tsx` | React 渲染入口 |

### 3.2 后端入口

| 文件 | 说明 |
|------|------|
| `backend/vanna/api_server.py` | FastAPI 主程序，端口 8100 |

---

## 四、外部服务集成

| 服务 | 集成代码位置 | 端口 | 说明 |
|------|-------------|------|------|
| **Jina Embedding** | `local_embedding/app_jina_embedding_v4.py` | 8898 | 文本向量化 |
| **Milvus** | `backend/vanna/src/vanna/milvus/milvus_vector.py` | 19530 | 向量存储与检索 |
| **MySQL** | `backend/vanna/src/Improve/tools/database_tools.py` | 3306 | 业务数据存储 |
| **LLM (通义)** | `backend/vanna/src/Improve/clients/vanna_client.py` | - | SQL 生成与回答 |

---

## 五、核心调用链路

```
用户提问
    │
    ▼
┌────────────────────────────────────────┐
│  前端: ChatPanel.tsx                 │
│  → /api/v1/chat/stream (SSE)       │
└──────────────┬───────────────────────┘
               │ SSE 流式响应
               ▼
┌────────────────────────────────────────┐
│  api_server.py: chat_stream()         │
│  - 接收问题                          │
│  - 返回流式响应 (step/answer/data)    │
└──────────────┬───────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│  react_agent.py: Agent (LangGraph)     │
│  - 工作流编排                         │
│  - ReAct 推理模式                    │
└──────────────┬───────────────────────┘
               │
     ┌─────────┴─────────┐
     │                    │
     ▼                    ▼
┌──────────┐      ┌──────────────┐
│ RAG 工具  │      │ LLM (通义)   │
│          │      │              │
│ - get_table_schema │  │ - 生成 SQL   │
│ - get_ddl    │      │ - 生成回答   │
│ - get_documents │    │ - 生成图表配置│
└────┬─────┘      └──────────────┘
     │
     ▼
┌────────────────────────────────────────┐
│  database_tools.py: execute_sql       │
│  - 连接 MySQL                         │
│  - 执行 SQL 查询                      │
│  - 返回结果                          │
└────────────────────────────────────────┘
```

---

## 六、前端业务组件对照

| 业务功能 | 前端组件文件 | 说明 |
|---------|-------------|------|
| 智能对话 | `frontend/src/components/ChatPanel.tsx` | AI 对话界面，流式输出 |
| SQL 编写 | `frontend/src/components/QueryPanel.tsx` | SQL 编辑器 |
| 结果展示 | `frontend/src/components/ResultsPanel.tsx` | 数据表格和图表 |
| 训练数据 | `frontend/src/components/TrainingDataPanel.tsx` | 训练数据管理 |
| 数据源 | `frontend/src/components/DataSourcePanel.tsx` | 数据源管理 |
| 数据库连接 | `frontend/src/components/DatabaseConnectionPanel.tsx` | 数据库连接配置 |

---

## 七、技术栈总结

| 层级 | 技术选型 |
|------|----------|
| 前端框架 | React + TypeScript + Vite |
| UI 组件 | shadcn/ui + Tailwind CSS |
| 图表库 | Chart.js + Recharts |
| 后端框架 | FastAPI + LangChain 1.0 |
| Agent 框架 | LangGraph |
| 向量数据库 | Milvus |
| 嵌入模型 | Jina Embeddings v4 |
| LLM | 通义千问 (DashScope) |
| 关系型数据库 | MySQL 8.0 |

---

## 八、系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           用户层 (User Layer)                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  前端页面 (React + TypeScript + Vite)                       │   │
│  │  - ChatPanel (对话界面)                                     │   │
│  │  - QueryPanel (SQL编辑器)                                    │   │
│  │  - ResultsPanel (结果展示)                                   │   │
│  │  - TrainingDataPanel (训练数据管理)                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┬───────┘
                                                                 │
                                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           API 网关层 (API Gateway Layer)                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  backend/vanna/api_server.py                                 │   │
│  │  - FastAPI 服务入口 (Port 8100)                             │   │
│  │  - /api/v1/chat (对话接口)                                 │   │
│  │  - /api/v1/chat/stream (流式对话)                        │   │
│  │  - /api/query (SQL查询)                                    │   │
│  │  - /api/v1/training/* (训练数据管理)                       │   │
│  │  - /api/v1/database/* (数据库连接)                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┬───────┘
                                                                 │
                                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Agent 核心层 (Agent Core Layer)                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  backend/vanna/react_agent.py                                │   │
│  │  - LangGraph Agent 定义                                    │   │
│  │  - ReAct 推理模式                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  backend/vanna/src/Improve/agent/nl2sql_agent.py            │   │
│  │  - NL2SQL Agent 核心逻辑                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┬───────┘
                                                                 │
                    │                              │                              │
                    ▼                              ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              工具层 (Tools Layer)                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │ database_tools.py │  │   rag_tools.py    │  │ post_training.py │              │
│  │                  │  │                  │  │                  │              │
│  │ - execute_sql   │  │ - get_table_schema│  │ - 训练决策      │              │
│  │ - query_sql     │  │ - get_ddl        │  │ - 添加训练数据  │              │
│  └──────────────────┘  │ - get_documents  │  └──────────────────┘              │
│                           └──────────────────┘                                      │
└────────────────────────────────────────────────────────────────────┬───────────────┘
                                                                     │
                    │                              │                              │
                    ▼                              ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                           基础设施层 (Infrastructure Layer)                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────┐ │
│  │   Jina          │  │    Milvus        │  │     MySQL       │  │  LLM     │ │
│  │   Embedding     │  │   向量数据库     │  │    数据库       │  │  (通义)  │ │
│  │                  │  │                  │  │                  │  │           │ │
│  │ (文本向量化)    │  │ (向量存储/检索)  │  │  (业务数据)    │  │           │ │
│  │ Port: 8898     │  │  Port: 19530    │  │  Port: 3306    │  │           │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 九、业务模块总结表

| 业务模块 | 前端组件 | 后端文件 | 外部依赖 |
|---------|----------|----------|----------|
| **智能对话** | `ChatPanel.tsx` | `api_server.py`, `react_agent.py` | LLM (通义) |
| **SQL 执行** | `QueryPanel.tsx` | `database_tools.py` | MySQL |
| **RAG 检索** | - | `rag_tools.py`, `vanna_client.py` | Milvus, Jina |
| **结果展示** | `ResultsPanel.tsx`, `QueryResultDisplay.tsx` | 返回 chartconfig JSON | Chart.js |
| **训练数据** | `TrainingDataPanel.tsx` | `post_training.py` | Milvus |
| **数据源** | `DataSourcePanel.tsx`, `DatabaseConnectionPanel.tsx` | database 接口 | MySQL |

---

## 十、核心设计思路

### 10.1 Agent 设计模式

系统采用 **LangGraph** 框架实现 Agent，遵循 **ReAct (Reasoning + Acting)** 模式：

1. **Reasoning**：理解用户问题，分析需要哪些信息
2. **Acting**：调用工具获取信息（表结构、文档、SQL 示例）
3. **Observation**：观察工具返回结果
4. **Reasoning again**：基于获取的信息继续推理
5. **Final Answer**：生成最终回答

### 10.2 RAG 增强

系统使用 RAG 技术提升 SQL 生成准确率：

- **SQL 示例检索**：从 Milvus 检索相似问题的 SQL
- **表结构检索**：获取相关表的 DDL
- **文档检索**：获取业务背景知识

### 10.3 可视化自动生成

LLM 根据查询结果自动生成图表配置（chartconfig JSON），前端直接渲染，无需额外配置。
