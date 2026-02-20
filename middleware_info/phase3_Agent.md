# 对话模块 - 源码分析文档

## 一、模块概述

对话模块是 NL2SQL 系统的核心业务层，负责处理用户提问并返回 SQL 查询结果。整个流程采用 **ReAct 推理模式**，通过 **LangChain 1.0** 框架协调多个工具完成复杂任务。

### 核心特性
- **流式响应**：使用 SSE（Server-Sent Events）实现实时推送
- **ReAct 推理**：Reason（推理） + Acting（行动）模式
- **中间件机制**：使用 LangChain 中间件实现追踪和 UI 事件
- **工具编排**：通过 Agent 自动调度 RAG、SQL 执行等工具

---

## 二、子功能模块详细分析

### 2.1 流式对话接口（后端 API）

| 项目 | 说明 |
|------|------|
| **功能** | 接收用户问题，返回流式响应（SSE） |
| **后端接口** | `POST /api/v1/chat/stream` |
| **代码位置** | `backend/vanna/api_server.py:339-577` |
| **响应格式** | step / answer / data / chart_config / done |

#### SSE 事件类型

```python
# api_server.py:396-448
# 步骤事件
step_data = {
    'type': 'step',
    'action': '查询数据库结构',
    'tool_name': 'get_all_tables_info',
    'status': 'completed',  # preparing / running / completed
    'duration_ms': 120,
    'result': '...'
}

# 数据事件
data_event = {
    'type': 'data',
    'data': [...],
    'columns': [...],
    'sql': 'SELECT ...'
}

# 图表配置事件
chart_event = {
    'type': 'chart_config',
    'config': {...}
}

# 答案事件（流式）
answer_event = {
    'type': 'answer',
    'content': '根据查询结果...',
    'done': False
}

# 结束事件
{'type': 'done'}
```

#### 核心代码

```python
# api_server.py:339-577
@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        # 第一阶段：实时推送 Agent 执行步骤
        for event in agent.stream(
            {"messages": [{"role": "user", "content": request.question}]},
            stream_mode="values",
            config=cfg,
        ):
            # 检测工具调用
            if msg_type == 'ai' and hasattr(last_msg, 'tool_calls'):
                for tool_call in last_msg.tool_calls:
                    yield f"data: {json.dumps(step_data)}\n\n"
            
            # 检测工具执行结果
            elif msg_type == 'tool':
                yield f"data: {json.dumps(step_data)}\n\n"
        
        # 第二阶段：提取并推送查询数据
        if query_data:
            yield f"data: {json.dumps(data_event)}\n\n"
        
        # 推送图表配置
        if chart_config:
            yield f"data: {json.dumps(chart_event)}\n\n"
        
        # 流式推送答案
        for i, char in enumerate(answer):
            yield f"data: {json.dumps({'type': 'answer', 'content': char})}\n\n"
            await asyncio.sleep(0.02)
        
        # 结束标记
        yield f"data: {'type': 'done'}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

### 2.2 SSE 响应处理（前端）

| 项目 | 说明 |
|------|------|
| **功能** | 解析 SSE 流式响应，更新 UI |
| **前端组件** | `frontend/src/components/ChatPanel.tsx` |
| **代码位置** | 第 84-180 行 |
| **处理逻辑** | 区分 step/answer/data/chart_config 类型 |

#### 核心代码

```typescript
// ChatPanel.tsx:84-180
const response = await fetch(getApiUrl(API_ENDPOINTS.CHAT_STREAM), {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: query.trim() })
});

const reader = response.body?.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));

      if (data.type === 'step') {
        // 处理思考步骤
        setThinkingSteps(prev => { ... });
      } else if (data.type === 'answer') {
        // 累加答案
        setAnswer(prev => prev + data.content);
      } else if (data.type === 'chart_config') {
        // 接收图表配置
        setChartConfig(data.config);
      } else if (data.type === 'data') {
        // 接收查询数据
        setQueryData(resultData);
      }
    }
  }
}
```

---

### 2.3 Agent 工作流编排

| 项目 | 说明 |
|------|------|
| **功能** | LangGraph Agent 协调工具调用 |
| **核心文件** | `backend/vanna/src/Improve/agent/nl2sql_agent.py` |
| **框架** | LangChain 1.0 `create_agent` |
| **代码位置** | 第 37-73 行 |

#### 核心代码

```python
# nl2sql_agent.py:37-73
def create_nl2sql_agent(
    llm: ChatOpenAI, 
    enable_middleware: bool = True, 
    enable_ui_events: bool = True
):
    """创建 NL2SQL Agent"""
    
    # 定义基础工具
    tools = [
        get_all_tables_info,    # 获取所有表信息
        get_table_schema,       # RAG 检索
        check_mysql_version,    # 检查 MySQL 版本
        validate_sql_syntax,    # 验证 SQL 语法
        execute_sql,            # 执行 SQL
    ]
    
    # 中间件列表
    middleware = []
    if enable_middleware:
        middleware.extend([trace_model_call, trace_tool_call])
    if enable_ui_events:
        middleware.extend([ui_model_trace, ui_tool_trace])
    
    # 创建 Agent
    agent = create_agent(
        llm, 
        tools, 
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,
    )
    
    return agent
```

---

### 2.4 RAG 检索工具

| 项目 | 说明 |
|------|------|
| **功能** | 检索相关表结构、文档、历史 SQL |
| **核心文件** | `backend/vanna/src/Improve/tools/rag_tools.py` |
| **代码位置** | 第 14-58 行 |
| **数据源** | Milvus 向量数据库 |

#### 检索流程

```python
# rag_tools.py:14-58
@tool
def get_table_schema(question: str) -> str:
    """获取与问题相关的完整RAG信息"""
    
    vn = get_vanna_client()
    
    # 1. 获取相关表结构 (DDL) - 固定 3 个
    ddl_list = vn.get_related_ddl(question, n_results=3)
    
    # 2. 获取文档说明 (Documentation) - 固定 3 个
    doc_list = vn.get_related_documentation(question, n_results=3)
    
    # 3. 获取历史相似SQL - 固定 2 个
    similar_pairs = vn.get_similar_question_sql(question, n_results=2)
    
    return "\n".join(result_parts) if result_parts else "未找到相关信息"
```

#### Milvus 集合对应

| 集合名 | 存储内容 | 用途 |
|--------|---------|------|
| `vannaddl` | DDL 语句 | 提供表结构上下文 |
| `vannadoc` | 业务文档 | 提供业务语义说明 |
| `vannasql` | 问题-SQL 对 | 提供历史查询示例 |
| `vannaplan` | 业务分析主题 | 提供表结构过滤（通过主题相似度匹配相关表） |

---

### 2.5 数据库操作工具

| 项目 | 说明 |
|------|------|
| **功能** | 表信息查询、SQL 验证与执行 |
| **核心文件** | `backend/vanna/src/Improve/tools/database_tools.py` |

#### 工具列表

| 工具 | 代码位置 | 功能 |
|------|---------|------|
| `get_all_tables_info` | `database_tools.py:20-112` | 获取所有表及列信息 |
| `check_mysql_version` | `database_tools.py:115-152` | 检查 MySQL 版本 |
| `validate_sql_syntax` | - | 验证 SQL 语法 |
| `execute_sql` | `database_tools.py:160+` | 执行 SQL 查询 |

---

### 2.6 图表配置生成

| 项目 | 说明 |
|------|------|
| **功能** | LLM 生成图表配置，前端渲染 |
| **触发条件** | 答案中包含 `chartconfig` 代码块 |
| **前端组件** | `ChatPanel.tsx:151-154` |

---

## 三、ReAct 业务流程

### 3.1 ReAct 模式概述

ReAct = **Reasoning（推理） + Acting（行动）**

```
用户问题 → LLM 推理 → 调用工具 → 观察结果 → 继续推理 → 最终答案
```

### 3.2 详细执行流程

```
用户提问
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. check_mysql_version()                                  │
│    目的：确定数据库版本，选择合适的 SQL 语法                 │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. get_all_tables_info()                                  │
│    目的：获取所有表及列信息                                 │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. get_table_schema(question)                             │
│    目的：RAG 检索，获取 DDL/文档/历史SQL                   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. LLM 生成 SQL                                           │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. validate_sql_syntax(sql)                               │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. execute_sql(sql)                                       │
│    目的：执行 SQL，返回查询结果                            │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. 生成最终答案 + chartconfig（如需要）                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、LangChain 框架使用

### 4.1 LangChain 版本

```
langchain==1.0.3
langchain-core==1.0.3
langchain-openai==1.0.2
```

### 4.2 LangChain 核心组件

| 组件 | 代码位置 | 用途 |
|------|---------|------|
| `ChatOpenAI` | `api_server.py:14` | LLM 接口封装（通义千问） |
| `create_agent` | `nl2sql_agent.py:11` | 创建 ReAct Agent |
| `@tool` 装饰器 | `database_tools.py:11` | 定义工具函数 |
| `wrap_model_call` | `trace_middleware.py:11` | LLM 中间件包装器 |
| `wrap_tool_call` | `trace_middleware.py:11` | 工具中间件包装器 |

---

## 五、中间件机制

### 5.1 是否使用中间件？

**是的，项目使用了 LangChain 1.0 的中间件机制。**

### 5.2 中间件类型

项目实现了 **两套中间件**：

#### 1. 追踪中间件（调试用）

**文件**: `backend/vanna/src/Improve/middleware/trace_middleware.py`

| 中间件 | 作用 |
|--------|------|
| `trace_model_call` | 拦截 LLM 调用，记录输入/输出/耗时 |
| `trace_tool_call` | 拦截工具调用，记录参数/结果/耗时 |

#### 2. UI 事件中间件（前端展示）

**文件**: `backend/vanna/src/Improve/middleware/ui_events_middleware.py`

| 中间件 | 作用 |
|--------|------|
| `ui_model_trace` | 拦截 LLM 调用，提取用户问题，注入 ui_events |
| `ui_tool_trace` | 拦截工具调用，生成友好描述，注入 ui_events |

---

## 六、核心代码文件汇总

| 层级 | 文件 | 作用 |
|------|------|------|
| **前端对话 UI** | `frontend/src/components/ChatPanel.tsx` | 对话界面、SSE 解析 |
| **前端配置** | `frontend/src/config/index.ts:41` | API 端点定义 |
| **后端 API** | `backend/vanna/api_server.py:339-577` | 流式对话接口 |
| **Agent 创建** | `backend/vanna/src/Improve/agent/nl2sql_agent.py` | Agent 初始化 |
| **System Prompt** | `backend/vanna/src/Improve/config/prompts.py` | Agent 提示词 |
| **RAG 工具** | `backend/vanna/src/Improve/tools/rag_tools.py` | 向量检索 |
| **数据库工具** | `backend/vanna/src/Improve/tools/database_tools.py` | SQL 执行 |
| **追踪中间件** | `backend/vanna/src/Improve/middleware/trace_middleware.py` | 调试追踪 |
| **UI 中间件** | `backend/vanna/src/Improve/middleware/ui_events_middleware.py` | 前端事件 |

---

## 七、现有实现分析（待优化）

### 7.1 get_all_tables_info 工具

**文件**: `backend/vanna/src/Improve/tools/database_tools.py`

**代码位置**: 第 136-230 行

**功能**: 获取数据库中表的信息（支持 Plan 过滤和关键字过滤）

**优化后的特性**:
- **支持问题过滤**: 可通过 `question` 参数过滤相关表
- **Plan 过滤优先**: 通过 vannaplan 检索相似度 >= 0.75 的表
- **关键字过滤备选**: Plan 过滤无结果时，使用关键字匹配
- **交集过滤**: 过滤结果只返回数据库中实际存在的表

**当前代码逻辑**:

```python
@tool
def get_all_tables_info(question: str = "") -> str:
    """获取表信息，支持 Plan 过滤和关键字过滤"""

    # 1. 查询所有表
    tables_df = vn.run_sql(tables_query)
    all_table_names = tables_df['TABLE_NAME'].tolist()

    # 2. 如果提供了问题，进行表过滤
    if question:
        # 2.1 优先尝试 Plan 过滤
        plan_filtered = _filter_tables_by_plan(vn, db_name, question, all_table_names)
        if plan_filtered:
            tables_df = tables_df[tables_df['TABLE_NAME'].isin(plan_filtered)]
        else:
            # 2.2 Plan 无结果，使用关键字过滤
            keywords = _extract_keywords(question)
            if keywords:
                filtered_df = _filter_tables_by_keywords(tables_df, keywords)
                tables_df = filtered_df

    # 3. 返回过滤后的表信息
    for _, table_row in tables_df.iterrows():
        # ... 获取列信息
```

---

### 7.2 辅助函数

**文件**: `backend/vanna/src/Improve/tools/database_tools.py`

#### 7.2.1 _filter_tables_by_plan

**功能**: 通过 vannaplan 检索相关表并过滤

```python
def _filter_tables_by_plan(vn, db_name: str, question: str, all_tables: list) -> list:
    """
    通过 vannaplan 检索相关表名并与 all_tables 取交集
    - 从 vannaplan 集合检索相似度 >= 0.75 的 top5 记录
    - 提取 tables 字段中的表名（按逗号分割）
    - 与 all_tables 取交集，确保只返回存在的表
    """
```

#### 7.2.2 _extract_keywords

**功能**: 从问题中提取关键词

```python
def _extract_keywords(question: str) -> list:
    """
    移除停用词后返回关键词列表
    停用词: 的、是、在、有、和、与、或、了、一个、什么、怎么、如何、请、查询、获取、找出
    """
```

#### 7.2.3 _filter_tables_by_keywords

**功能**: 通过关键字匹配过滤表

```python
def _filter_tables_by_keywords(tables_df: pd.DataFrame, keywords: list) -> pd.DataFrame:
    """
    匹配表名或表注释中包含关键词的表
    如果没有匹配，返回前 10 个表
    """
```

---

### 7.3 get_table_schema 工具

**文件**: `backend/vanna/src/Improve/tools/rag_tools.py`

**代码位置**: 第 14-58 行

**功能**: 根据用户问题检索相关的 DDL、文档、历史 SQL

**当前问题**:
- **仅依赖向量检索**：只用 Embedding 向量相似度，可能遗漏语义相关但向量不相似的内容
- **n_results 固定**：DDL 和文档都是 3 个，SQL 示例是 2 个，无法根据问题复杂度调整
- **无关键词匹配**：没有结合表名、列名等关键词进行二次筛选

**当前代码逻辑**:

```python
@tool
def get_table_schema(question: str) -> str:
    # 1. 向量检索 DDL（固定 3 个）
    ddl_list = vn.get_related_ddl(question, n_results=3)
    
    # 2. 向量检索文档（固定 3 个）
    doc_list = vn.get_related_documentation(question, n_results=3)
    
    # 3. 向量检索历史 SQL（固定 2 个）
    similar_pairs = vn.get_similar_question_sql(question, n_results=2)
```

---

### 7.4 Milvus 向量检索实现（已优化）

**文件**: `backend/vanna/src/vanna/milvus/milvus_vector.py`

#### 7.4.1 get_related_ddl（已优化）

```python
def get_related_ddl(self, question: str, **kwargs) -> list:
    """
    获取与问题相关的 DDL

    Args:
        question: 用户问题
        db_name: 数据库名称（用于过滤）
        threshold: 相似度阈值，默认 0.5
        top_k: 返回数量，默认 5
    """
    # 支持 db_name 过滤、阈值 0.5、topk=5
```

#### 7.4.2 get_related_documentation（已优化）

```python
def get_related_documentation(self, question: str, **kwargs) -> list:
    """
    获取与问题相关的文档

    Args:
        question: 用户问题
        db_name: 数据库名称（用于过滤）
        top_k: 返回数量，默认 5
    """
    # 支持 db_name 过滤
```

#### 7.4.3 get_similar_question_sql（已优化）

```python
def get_similar_question_sql(self, question: str, **kwargs) -> list:
    """
    获取与问题相似的历史查询 SQL

    Args:
        question: 用户问题
        db_name: 数据库名称（用于过滤）
        top_k: 返回数量，默认 5
    """
    # 支持 db_name 过滤
```

#### 7.4.4 _get_ddl_by_keywords（新增）

```python
def _get_ddl_by_keywords(self, keywords: list, db_name: str = "", **kwargs) -> list:
    """
    通过关键词检索 DDL

    Args:
        keywords: 关键词列表
        db_name: 数据库名称（用于过滤）
        top_k: 返回数量，默认 5
    """
```

#### 7.4.5 _get_doc_by_keywords（新增）

```python
def _get_doc_by_keywords(self, keywords: list, db_name: str = "", **kwargs) -> list:
    """
    通过关键词检索文档

    Args:
        keywords: 关键词列表
        db_name: 数据库名称（用于过滤）
        top_k: 返回数量，默认 5
    """
```

---

## 八、优化方案（已完成）

### 8.1 优化目标 ✅ 已完成

1. **精准检索**：只返回与问题真正相关的表和文档 ✅
2. **减少上下文**：降低 LLM 处理压力和幻觉风险 ✅
3. **多路召回**：结合向量检索 + 关键词匹配 ✅
4. **可配置**：支持根据问题复杂度动态调整返回数量 ✅

---

### 8.2 方案一：get_all_tables_info 增强 ✅ 已实现

**状态**: 已完成实现

**实现文件**:
- `backend/vanna/src/Improve/tools/database_tools.py`
- `backend/vanna/src/vanna/milvus/milvus_vector.py`

**实现功能**:
- 支持 `question` 参数过滤相关表
- **Plan 过滤优先**: 通过 vannaplan 检索相似度 >= 0.75 的表
- **关键字过滤备选**: Plan 过滤无结果时，使用关键字匹配
- 与 all_tables 取交集，确保只返回存在的表

**核心代码**:

```python
@tool
def get_all_tables_info(question: str = "") -> str:
    # 1. 获取所有表
    tables_df = vn.run_sql(tables_query)
    all_table_names = tables_df['TABLE_NAME'].tolist()

    # 2. 如果提供了问题，进行表过滤
    if question:
        # 2.1 优先尝试 Plan 过滤
        plan_filtered = _filter_tables_by_plan(vn, db_name, question, all_table_names)
        if plan_filtered:
            tables_df = tables_df[tables_df['TABLE_NAME'].isin(plan_filtered)]
        else:
            # 2.2 Plan 无结果，使用关键字过滤
            keywords = _extract_keywords(question)
            if keywords:
                filtered_df = _filter_tables_by_keywords(tables_df, keywords)
                tables_df = filtered_df
```
    for _, table_row in tables_df.iterrows():
        # ... 现有逻辑
```

**辅助函数**:

```python
def _extract_keywords(question: str) -> List[str]:
    """从问题中提取关键词（表名、列名）"""
    import re
    
    # 简单实现：提取英文单词（表名/列名通常是英文）
    words = re.findall(r'[a-zA-Z_]+', question.lower())
    
    # 过滤常见英语词汇
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 
                  'have', 'has', 'had', 'do', 'does', 'did',
                  'what', 'which', 'who', 'whom', 'this', 'that',
                  'these', 'those', 'and', 'or', 'but', 'in', 'on',
                  'at', 'to', 'for', 'of', 'with', 'by', 'from'}
    
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    return keywords


def _filter_related_tables(tables_df: pd.DataFrame, keywords: List[str]) -> pd.DataFrame:
    """根据关键词过滤相关表"""
    
    if not keywords:
        return tables_df
    
    # 计算每张表的相关度得分
    scores = []
    for _, row in tables_df.iterrows():
        table_name = str(row['TABLE_NAME']).lower()
        table_comment = str(row['TABLE_COMMENT'] or '').lower()
        
        score = 0
        for kw in keywords:
            if kw in table_name:
                score += 10  # 表名匹配得分高
            if kw in table_comment:
                score += 5   # 注释匹配得分中等
        
        scores.append(score)
    
    tables_df = tables_df.copy()
    tables_df['score'] = scores
    
    # 返回有得分的表，或者返回前 10 张
    related = tables_df[tables_df['score'] > 0]
    if related.empty:
        return tables_df.head(10)  # 默认返回前 10 张
    
    return related.sort_values('score', ascending=False)
```

---

### 8.3 方案二：get_table_schema 多路召回 ✅ 已实现

**状态**: 已完成实现

**优化内容**:
- 结合向量检索 + 关键词匹配
- 支持 db_name 过滤
- 相似度阈值 0.5，top_k=5

**实现文件**:
- `backend/vanna/src/Improve/tools/rag_tools.py`

**核心代码**:

```python
@tool
def get_table_schema(question: str) -> str:
    """获取与问题相关的完整RAG信息（多路召回）"""

    vn = get_vanna_client()

    # 获取当前数据库名
    db_name = vn.run_sql("SELECT DATABASE()").iloc[0, 0]

    # 提取关键词
    keywords = _extract_keywords(question)

    # 1. 向量检索 DDL（阈值 0.5，topk=5，按 db_name 过滤）
    ddl_list = vn.get_related_ddl(
        question,
        db_name=db_name,
        threshold=0.5,
        top_k=5
    )

    # 2. 关键词增强
    if keywords:
        keyword_ddl_list = vn._get_ddl_by_keywords(keywords, db_name=db_name, top_k=5)
        ddl_list = _merge_and_deduplicate(ddl_list, keyword_ddl_list)

    # 3. 向量检索文档（按 db_name 过滤）
    doc_list = vn.get_related_documentation(question, db_name=db_name, top_k=5)

    # 4. 关键词增强
    if keywords:
        keyword_doc_list = vn._get_doc_by_keywords(keywords, db_name=db_name, top_k=5)
        doc_list = _merge_and_deduplicate(doc_list, keyword_doc_list)

    # 5. 历史 SQL 检索（按 db_name 过滤）
    similar_pairs = vn.get_similar_question_sql(question, db_name=db_name, top_k=3)
```

---

### 8.4 优化总结

| 方法 | 优化内容 |
|------|----------|
| `get_related_ddl` | 添加 db_name 过滤、阈值 0.5、topk=5 |
| `get_related_documentation` | 添加 db_name 过滤 |
| `get_similar_question_sql` | 添加 db_name 过滤 |
| `_get_ddl_by_keywords` | 新增，支持 db_name 过滤 |
| `_get_doc_by_keywords` | 新增，支持 db_name 过滤 |
                limit=3
            )
            results.extend([r["ddl"] for r in res])
        except:
            pass
    return list(set(results))


def _get_doc_by_keywords(vn, keywords: List[str]) -> List[str]:
    """根据关键词从 Milvus 查询相关文档"""
    results = []
    for kw in keywords:
        try:
            if not re.match(r'^[a-zA-Z0-9_]+$', kw):
                continue
            res = vn.milvus_client.query(
                collection_name="vannadoc",
                filter=f'doc like "%{kw}%"',
                output_fields=["doc"],
                limit=3
            )
            results.extend([r["doc"] for r in res])
        except:
            pass
    return list(set(results))


def _merge_and_deduplicate(list1: List, list2: List) -> List:
    """合并两个列表并去重"""
    seen = set()
    result = []
    for item in list1 + list2:
        item_str = str(item)
        if item_str not in seen:
            seen.add(item_str)
            result.append(item)
    return result
```

---

### 8.4 方案三：智能 n_results 调整（进阶）

**思路**: 根据问题复杂度动态调整返回数量

```python
def _calculate_n_results(question: str) -> dict:
    """根据问题复杂度计算返回数量"""
    
    complexity_indicators = {
        'join': 2,        # JOIN 关键词
        'group': 2,       # GROUP BY
        'order': 1,       # ORDER BY
        'subquery': 2,    # 子查询
        'multiple': 2,    # 多个
        'total': 2,       # 总计/合计
        'average': 2,     # 平均
        'count': 1,       # 计数
    }
    
    question_lower = question.lower()
    score = sum(v for k, v in complexity_indicators.items() if k in question_lower)
    
    base = 3
    extra = min(score, 4)  # 最多额外 4 个
    
    return {
        'ddl': base + extra,
        'doc': base + extra,
        'sql': 2 + extra // 2
    }
```

---

## 九、需要修改的代码文件

### 9.1 后端文件

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `database_tools.py` | 优化 `get_all_tables_info`，增加关键词过滤 | 推荐 |
| `rag_tools.py` | 优化 `get_table_schema`，增加多路召回 | 推荐 |
| `nl2sql_agent.py` | 调整工具参数，传递 question | 可选 |
| `prompts.py` | 更新 System Prompt，说明新行为 | 推荐 |

### 9.2 前端文件

**无需修改** - 优化只涉及后端逻辑，不改变 API 接口

---

## 十、工作量估算

| 优化项 | 工作内容 | 预估工作量 |
|--------|---------|-----------|
| get_all_tables_info 增强 | 关键词提取 + 过滤逻辑 | 1-2 小时 |
| get_table_schema 多路召回 | 关键词检索 + 合并去重 | 2-3 小时 |
| System Prompt 更新 | 调整提示词说明 | 0.5 小时 |
| 测试验证 | 手动测试多种问题 | 1 小时 |

**总计**: 约 4-6 小时

---

## 十一、注意事项

### 11.1 SQL 注入风险

在关键词过滤中使用字符串拼接时要注意：

```python
# ❌ 危险写法
filter_expr = f'ddl like "%{kw}%"'

# ✅ 安全写法
# 确保 kw 经过严格校验（只允许英文数字下划线）
import re
if not re.match(r'^[a-zA-Z0-9_]+$', kw):
    continue  # 跳过非法关键词
```

### 11.2 向量检索仍是主要方式

- 关键词匹配是**补充**手段，不能替代向量检索
- 向量检索能发现语义相关但字面不匹配的内容
- 两者结合效果最佳

### 11.3 性能考虑

- 关键词查询会增加额外延迟
- 可以考虑缓存关键词查询结果
- 限制关键词数量（最多 5-10 个）

---

## 十二、总结

### 子功能模块汇总

| 子功能 | 后端文件 | 前端文件 |
|--------|---------|---------|
| 流式对话接口 | `api_server.py:339-577` | - |
| SSE 响应处理 | - | `ChatPanel.tsx:84-180` |
| Agent 工作流 | `nl2sql_agent.py:37-73` | - |
| RAG 检索 | `rag_tools.py:14-58` | - |
| SQL 执行 | `database_tools.py:161+` | - |
| 图表配置 | LLM 生成 | `ChatPanel.tsx:151-154` |
| 追踪中间件 | `trace_middleware.py` | - |
| UI 中间件 | `ui_events_middleware.py` | - |

### 现有问题 ✅ 已解决

| 工具 | 问题 | 状态 |
|------|------|------|
| `get_all_tables_info` | 无条件返回所有表，信息量过大 | ✅ 已解决（支持 Plan/关键字过滤） |
| `get_table_schema` | 仅依赖向量检索，可能遗漏相关内容 | 部分解决 |

### 优化方案效果 ✅ 已实现

| 方案 | 效果 |
|------|------|
| Plan 过滤 | 通过 vannaplan 检索相似表，精准度高 |
| 关键字过滤 | Plan 无结果时的备选方案，提高召回率 |
| 多路召回 | 向量 + 关键词结合，提高召回率 |
| 动态 n_results | 根据问题复杂度调整返回数量 |

### 核心新增文件

| 文件 | 说明 |
|------|------|
| `backend/vanna/src/vanna/milvus/milvus_vector.py` | 新增 `get_related_plan_tables` 方法 |
| `backend/vanna/src/Improve/tools/database_tools.py` | 新增过滤辅助函数 |
| `backend/playground/test_get_all_tables.py` | 表过滤功能测试脚本 |
| `backend/playground/test_chat_stream.py` | 对话流程测试脚本 |
