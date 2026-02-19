# NL2SQL 系统源码分析 - 完整版

本文档整合了数据源管理模块、训练数据管理模块和对话模块的完整源码分析。

---

# 第一部分：数据源管理模块

## 一、模块概述

数据源管理模块是 NL2SQL 系统的第一层，负责管理数据库连接和表结构。该模块主要围绕 MySQL 数据库展开，包含以下核心功能：

- 数据库连接测试
- 数据库连接与表结构获取
- 表结构树形展示
- 数据源配置持久化

---

## 二、子功能模块详细分析

### 2.1 数据库连接测试

| 项目 | 说明 |
|------|------|
| **功能** | 在正式连接数据库之前，先测试连接配置是否正确 |
| **后端接口** | `POST /api/v1/database/test` |
| **后端代码** | `api_server.py:721-757` |
| **前端组件** | `DataSourcePanel.tsx:74-94` |

**核心逻辑**:
```python
connection = pymysql.connect(
    host=request.host,
    port=int(request.port),
    user=request.username,
    password=request.password,
    database=request.database if request.database else None,
    connect_timeout=5
)
connection.close()
```

---

### 2.2 数据库连接与表结构获取

| 项目 | 说明 |
|------|------|
| **功能** | 连接数据库并获取表结构信息 |
| **后端接口** | `POST /api/v1/database/connect` |
| **后端代码** | `api_server.py:759-861` |
| **前端组件** | `DataSourcePanel.tsx:96-147` |

**返回数据结构**:
```python
table_info = {
    "name": table_name,
    "type": "table",
    "children": [
        {"name": col[0], "type": "column", "dataType": col[1], ...}
    ]
}
```

---

### 2.3 表结构树形展示

以树形结构展示数据库→表→列的层级关系。

**前端组件**: `DataSourcePanel.tsx`

**关键函数**:
- `convertToTableNodes` - 转换为树形节点
- `renderTreeNode` - 递归渲染树形节点
- `toggleNode` - 处理展开/折叠

---

### 2.4 数据源配置持久化

使用 localStorage 保存数据源配置。

**存储键**: `dataSources`

---

## 三、增加数据源列表功能

### 需要修改的前端代码

| 文件 | 修改内容 |
|------|---------|
| `frontend/src/services/api.ts` | 新增数据源列表 API |
| `frontend/src/components/DataSourcePanel.tsx` | 改造为支持多数据源列表 |

### 工作量估算

| 模块 | 工作内容 | 预估工作量 |
|------|---------|-----------|
| 后端 | 无需修改 | 0 小时 |
| 前端 | API 封装 + 组件改造 | 2-3 小时 |

---

# 第二部分：训练数据管理模块

## 一、模块概述

训练数据管理模块是 NL2SQL 系统的第二层，负责管理 RAG 所需的训练数据。这些数据存储在 **Milvus 向量数据库** 中：

| 集合名 | 存储内容 | 用途 |
|--------|---------|------|
| `vannasql` | 问题-SQL 对 | 提供历史查询示例 |
| `vannaddl` | DDL 语句 | 提供表结构上下文 |
| `vannadoc` | 业务文档 | 提供业务语义说明 |

---

## 二、子功能模块详细分析

### 2.1 添加训练数据

| 项目 | 说明 |
|------|------|
| **功能** | 向系统添加 SQL 示例、DDL、表文档 |
| **后端接口** | `POST /api/v1/training/add` |
| **后端代码** | `api_server.py:579-622` |
| **前端组件** | `TrainingDataPanel.tsx:88-129` |

**数据类型**: `sql`、`ddl`、`documentation`

---

### 2.2 获取训练数据列表

| 项目 | 说明 |
|------|------|
| **功能** | 获取已添加的所有训练数据 |
| **后端接口** | `GET /api/v1/training/get` |
| **后端代码** | `api_server.py:624-688` |
| **支持功能** | 分页、类型过滤 |

**Milvus 查询实现** (`milvus_vector.py:210-255`):
```python
sql_data = self.milvus_client.query(collection_name="vannasql", ...)
ddl_data = self.milvus_client.query(collection_name="vannaddl", ...)
doc_data = self.milvus_client.query(collection_name="vannadoc", ...)
df = pd.concat([df_sql, df_ddl, df_doc])
```

---

### 2.3 删除训练数据

| 项目 | 说明 |
|------|------|
| **功能** | 删除指定的训练数据 |
| **后端接口** | `DELETE /api/v1/training/delete` |
| **后端代码** | `api_server.py:690-719` |

---

## 三、增加新集合或调整字段

### 需要修改的后端代码

| 文件 | 修改内容 |
|------|---------|
| `milvus_vector.py` | 集合创建方法、字段定义 |
| `vanna_client.py` | add/remove 方法 |
| `api_server.py` | 请求模型、处理逻辑 |

### 工作量估算

| 模块 | 工作内容 | 预估工作量 |
|------|---------|-----------|
| Milvus 集合 | 新增集合创建方法 | 1-2 小时 |
| Vanna 客户端 | 新增 add/remove 方法 | 1-2 小时 |
| API 接口 | 添加新数据类型处理 | 0.5-1 小时 |
| 前端 | 类型、模板、UI 调整 | 1-2 小时 |

---

# 第三部分：对话模块

## 一、模块概述

对话模块是 NL2SQL 系统的核心业务层，采用 **ReAct 推理模式**，通过 **LangChain 1.0** 框架协调多个工具完成复杂任务。

### 核心特性
- **流式响应**：使用 SSE 实现实时推送
- **ReAct 推理**：Reason + Acting 模式
- **中间件机制**：追踪和 UI 事件

---

## 二、子功能模块详细分析

### 2.1 流式对话接口

| 项目 | 说明 |
|------|------|
| **后端接口** | `POST /api/v1/chat/stream` |
| **代码位置** | `api_server.py:339-577` |
| **响应格式** | step / answer / data / chart_config / done |

---

### 2.2 Agent 工作流编排

| 项目 | 说明 |
|------|------|
| **框架** | LangChain 1.0 `create_agent` |
| **代码位置** | `nl2sql_agent.py:37-73` |

```python
def create_nl2sql_agent(llm, enable_middleware=True, enable_ui_events=True):
    tools = [
        get_all_tables_info,
        get_table_schema,
        check_mysql_version,
        validate_sql_syntax,
        execute_sql,
    ]
    middleware = [trace_model_call, trace_tool_call, ui_model_trace, ui_tool_trace]
    agent = create_agent(llm, tools, system_prompt=SYSTEM_PROMPT, middleware=middleware)
    return agent
```

---

### 2.3 RAG 检索工具

| 工具 | 位置 | 功能 |
|------|------|------|
| `get_table_schema` | `rag_tools.py:14-58` | RAG 检索（DDL+文档+历史SQL） |

**当前问题**:
- 无条件返回所有表（get_all_tables_info）
- 仅依赖向量检索（get_table_schema）
- n_results 固定

---

### 2.4 数据库操作工具

| 工具 | 位置 | 功能 |
|------|------|------|
| `get_all_tables_info` | `database_tools.py:20-112` | 获取所有表及列信息 |
| `execute_sql` | `database_tools.py:160+` | 执行 SQL 查询 |

---

### 2.5 中间件机制

**两套中间件**:

| 中间件 | 文件 | 作用 |
|--------|------|------|
| `trace_model_call` | `trace_middleware.py` | LLM 调用追踪 |
| `trace_tool_call` | `trace_middleware.py` | 工具调用追踪 |
| `ui_model_trace` | `ui_events_middleware.py` | UI 事件注入 |
| `ui_tool_trace` | `ui_events_middleware.py` | 工具事件生成 |

---

## 三、ReAct 业务流程

```
用户提问
    │
    ▼
┌─────────────────────────────────────────────┐
│ 1. check_mysql_version()                  │
│    确定数据库版本，选择合适的 SQL 语法      │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 2. get_all_tables_info()                 │
│    获取所有表及列信息                      │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 3. get_table_schema(question)             │
│    RAG 检索：DDL/文档/历史SQL            │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 4. LLM 生成 SQL                          │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 5. validate_sql_syntax(sql)              │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 6. execute_sql(sql)                      │
│    执行 SQL，返回查询结果                  │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 7. 生成最终答案 + chartconfig            │
└─────────────────────────────────────────────┘
```

---

## 四、优化方案

### 4.1 get_all_tables_info 增强

**问题**: 无条件返回所有表，信息量过大

**方案**: 增加关键词过滤

```python
@tool
def get_all_tables_info(question: str = "") -> str:
    # 1. 获取所有表
    all_tables = vn.run_sql(tables_query)
    
    # 2. 如果提供了问题，进行关键词过滤
    if question:
        keywords = _extract_keywords(question)
        related_tables = _filter_related_tables(all_tables, keywords)
        tables_df = related_tables if not related_tables.empty else all_tables.head(10)
    else:
        tables_df = all_tables
    
    # 3. 获取列信息
    ...
```

---

### 4.2 get_table_schema 多路召回

**问题**: 仅依赖向量检索

**方案**: 向量检索 + 关键词匹配

```python
@tool
def get_table_schema(question: str) -> str:
    # 1. 向量检索
    ddl_list = vn.get_related_ddl(question, n_results=5)
    
    # 2. 关键词增强
    keywords = _extract_keywords(question)
    if keywords:
        keyword_ddl_list = _get_ddl_by_keywords(vn, keywords)
        ddl_list = _merge_and_deduplicate(ddl_list, keyword_ddl_list)
    
    # 3. 同样处理文档
    doc_list = vn.get_related_documentation(question, n_results=5)
    ...
```

---

### 4.3 智能 n_results 调整

根据问题复杂度动态调整返回数量。

```python
def _calculate_n_results(question: str) -> dict:
    complexity_indicators = {
        'join': 2, 'group': 2, 'order': 1, 
        'subquery': 2, 'multiple': 2, 'total': 2
    }
    score = sum(v for k, v in complexity_indicators.items() if k in question.lower())
    base, extra = 3, min(score, 4)
    return {'ddl': base + extra, 'doc': base + extra, 'sql': 2 + extra // 2}
```

---

## 五、需要修改的代码文件

### 后端文件

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `database_tools.py` | 优化 `get_all_tables_info`，增加关键词过滤 | 推荐 |
| `rag_tools.py` | 优化 `get_table_schema`，增加多路召回 | 推荐 |
| `prompts.py` | 更新 System Prompt | 推荐 |

### 前端文件

**无需修改**

---

## 六、工作量估算

| 优化项 | 工作内容 | 预估工作量 |
|--------|---------|-----------|
| get_all_tables_info 增强 | 关键词提取 + 过滤逻辑 | 1-2 小时 |
| get_table_schema 多路召回 | 关键词检索 + 合并去重 | 2-3 小时 |
| System Prompt 更新 | 调整提示词说明 | 0.5 小时 |
| 测试验证 | 手动测试多种问题 | 1 小时 |

**总计**: 约 4-6 小时

---

# 总结：模块关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          NL2SQL 系统架构                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    │
│  │  第一层         │    │  第二层         │    │  第三层         │    │
│  │  数据源管理     │ ──▶ │  训练数据管理   │ ──▶ │  对话模块        │    │
│  │                 │    │                 │    │                 │    │
│  │ • MySQL 连接    │    │ • vannasql     │    │ • Agent 工作流  │    │
│  │ • 表结构获取    │    │ • vannaddl     │    │ • RAG 检索      │    │
│  │ • 树形展示      │    │ • vannadoc     │    │ • SQL 执行      │    │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     LangChain 1.0 框架                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │   │
│  │  │ ChatOpenAI  │  │ create_agent│  │ @tool       │            │   │
│  │  │ (通义千问)  │  │ (ReAct)     │  │ (工具定义)  │            │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     基础设施层                                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │   │
│  │  │ Milvus   │  │ MySQL    │  │ Jina     │  │ LLM      │    │   │
│  │  │ 向量存储  │  │ 数据存储  │  │ Embedding│  │ (通义)   │    │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 附录：核心文件路径汇总

### 后端

| 模块 | 文件 | 作用 |
|------|------|------|
| API | `api_server.py` | REST 接口 |
| Agent | `nl2sql_agent.py` | Agent 创建 |
| RAG | `rag_tools.py` | 向量检索 |
| DB | `database_tools.py` | SQL 执行 |
| 中间件 | `trace_middleware.py` | 调试追踪 |
| 中间件 | `ui_events_middleware.py` | UI 事件 |
| 向量 | `milvus_vector.py` | Milvus 操作 |
| 客户端 | `vanna_client.py` | Vanna 封装 |

### 前端

| 模块 | 文件 | 作用 |
|------|------|------|
| 对话 | `ChatPanel.tsx` | 对话界面 |
| 数据源 | `DataSourcePanel.tsx` | 数据源面板 |
| 训练 | `TrainingDataPanel.tsx` | 训练数据管理 |
| API | `services/api.ts` | API 封装 |
