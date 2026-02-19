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
                    # 推送步骤状态
                    yield f"data: {json.dumps(step_data)}\n\n"
            
            # 检测工具执行结果
            elif msg_type == 'tool':
                # 推送完成状态
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
        setThinkingSteps(prev => {
          if (data.update) {
            // 更新最后一个步骤
            const newSteps = [...prev];
            newSteps[newSteps.length - 1] = {
              action: data.action,
              status: data.status,
              duration_ms: data.duration_ms,
              tool_name: data.tool_name,
              result: data.result,
            };
            return newSteps;
          } else {
            // 添加新步骤
            return [...prev, { ... }];
          }
        });
      } else if (data.type === 'answer') {
        // 累加答案
        setAnswer(prev => prev + data.content);
      } else if (data.type === 'chart_config') {
        // 接收图表配置
        setChartConfig(data.config);
      } else if (data.type === 'data') {
        // 接收查询数据
        const resultData = {
          success: true,
          data: data.data,
          columns: data.columns,
          returned_rows: data.data.length,
          sql: data.sql,
        };
        setQueryData(resultData);
        if (onQueryResult) onQueryResult(resultData);
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
    """创建 NL2SQL Agent（挂载 TraceMiddleware 和 UI 事件中间件）"""
    
    # 定义基础工具
    tools = [
        get_all_tables_info,    # 获取所有表信息
        get_table_schema,       # RAG 检索
        check_mysql_version,    # 检查 MySQL 版本
        validate_sql_syntax,    # 验证 SQL 语法
        execute_sql,            # 执行 SQL
    ]
    
    # 中间件列表（按顺序执行）
    middleware = []
    if enable_middleware:
        middleware.extend([trace_model_call, trace_tool_call])
    if enable_ui_events:
        # UI 事件中间件应该在 trace 之后
        middleware.extend([ui_model_trace, ui_tool_trace])
    
    # 使用 LangChain 1.0 的 create_agent API
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
    """获取与问题相关的完整RAG信息（DDL、文档说明、历史SQL）"""
    
    vn = get_vanna_client()
    
    # 1. 获取相关表结构 (DDL)
    ddl_list = vn.get_related_ddl(question, n_results=3)
    
    # 2. 获取文档说明 (Documentation)
    doc_list = vn.get_related_documentation(question, n_results=3)
    
    # 3. 获取历史相似SQL (Question-SQL pairs)
    similar_pairs = vn.get_similar_question_sql(question, n_results=2)
    
    # 组合结果
    result = f"""相关表结构 (DDL):
{ddl_list}

业务文档说明:
{doc_list}

历史相似查询:
{similar_pairs}"""
    
    return result
```

#### Milvus 集合对应

| 集合名 | 存储内容 | 用途 |
|--------|---------|------|
| `vannaddl` | DDL 语句 | 提供表结构上下文 |
| `vannadoc` | 业务文档 | 提供业务语义说明 |
| `vannasql` | 问题-SQL 对 | 提供历史查询示例 |

---

### 2.5 数据库操作工具

| 项目 | 说明 |
|------|------|
| **功能** | 表信息查询、SQL 验证与执行 |
| **核心文件** | `backend/vanna/src/Improve/tools/database_tools.py` |

#### 工具列表

| 工具 | 代码位置 | 功能 |
|------|---------|------|
| `get_all_tables_info` | `database_tools.py:20-159` | 获取所有表及列信息 |
| `check_mysql_version` | - | 检查 MySQL 版本 |
| `validate_sql_syntax` | - | 验证 SQL 语法 |
| `execute_sql` | `database_tools.py:161+` | 执行 SQL 查询 |

#### execute_sql 核心逻辑

```python
# database_tools.py:161-240
@tool
def execute_sql(sql: str) -> str:
    """执行 SQL 查询并返回结果"""
    
    # 1. 使用互斥锁强制串行执行（防止并发破坏 MySQL 连接）
    with _sql_execution_lock:
        vn = get_vanna_client()
        
        # 2. SQL 语法检查
        # - 检查 SET 语句
        # - 检查危险操作（DROP DELETE）
        
        # 3. 执行 SQL
        result_df = vn.run_sql(sql)
        
        # 4. 保存结果到全局缓存（供前端获取）
        set_last_query_result(result_df)
        
        # 5. 返回结果摘要
        return f"查询成功，返回 {len(result_df)} 行数据"
```

---

### 2.6 图表配置生成

| 项目 | 说明 |
|------|------|
| **功能** | LLM 生成图表配置，前端渲染 |
| **触发条件** | 答案中包含 `chartconfig` 代码块 |
| **前端组件** | `ChatPanel.tsx:151-154` → `ResultsPanel.tsx` |

#### LLM 输出格式

```markdown
根据查询结果，女性客户平均消费金额为 1280 元。

```chartconfig
{
  "type": "bar",
  "data": {...},
  "options": {...}
}
```
```

#### 前端处理

```typescript
// ChatPanel.tsx:151-154
} else if (data.type === 'chart_config') {
  console.log('[图表配置] 收到图表配置事件:', data.config);
  setChartConfig(data.config);
}
```

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
│    约束：MySQL 5.7 禁用 WITH/窗口函数                     │
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
│    目的：RAG 检索，获取相关：                              │
│    - DDL 表结构                                            │
│    - 业务文档                                              │
│    - 历史相似 SQL                                          │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. LLM 生成 SQL（根据步骤 1-3 的上下文）                  │
│    - 根据 MySQL 版本调整语法                               │
│    - 参考历史 SQL 示例                                     │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. validate_sql_syntax(sql)                               │
│    目的：验证生成的 SQL 语法是否正确                       │
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

### 3.3 System Prompt

**文件**: `backend/vanna/src/Improve/config/prompts.py`

```python
SYSTEM_PROMPT = """你是一个专业的 NL2SQL Agent，负责将自然语言问题转换为 SQL 查询并执行。

【最高优先级警告 - 请首先阅读】
如果当前数据库版本未知，你必须先调用 check_mysql_version() 确认！

MySQL 5.7 绝对禁止使用以下语法:
1. WITH ... AS (...) - CTE/公用表表达式
2. ROW_NUMBER() OVER() - 窗口函数
...

**强制工作流程（必须严格遵守）:**
1. 第一步: 调用 check_mysql_version() - 必须！
2. 调用 get_all_tables_info() 了解数据库结构
3. 调用 get_table_schema(question) 获取相关的表结构、历史SQL示例和业务文档
4. 直接在 AIMessage 中编写SQL
5. 调用 validate_sql_syntax(sql) 验证SQL语法
6. 调用 execute_sql(sql) 执行SQL并返回结果
"""
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

**功能**:
- 打印完整的 Agent 执行日志
- 对 `get_all_tables_info` 和 `get_table_schema` 进行精简输出
- 方便调试和问题排查

#### 2. UI 事件中间件（前端展示）

**文件**: `backend/vanna/src/Improve/middleware/ui_events_middleware.py`

| 中间件 | 作用 |
|--------|------|
| `ui_model_trace` | 拦截 LLM 调用，提取用户问题，注入 ui_events |
| `ui_tool_trace` | 拦截工具调用，生成友好描述，注入 ui_events |

**功能**:
- 使用 LLM 自动生成工具调用的简洁描述（15-20 字）
- 记录 `tool_start`、`tool_end`、`llm_end` 事件
- 将事件注入到 `AIMessage.additional_kwargs["ui_events"]`
- 前端根据这些事件展示思考步骤

### 5.3 中间件工作原理

#### 追踪中间件

```python
# trace_middleware.py:33-87
@wrap_model_call
def trace_model_call(request, handler):
    # 1. 记录开始时间
    t0 = time.time()
    
    # 2. 打印输入（messages）
    logger.info(f"[LLM START]")
    
    # 3. 执行真正的 LLM 调用
    resp = handler(request)
    
    # 4. 打印输出和耗时
    dt = (time.time() - t0) * 1000
    logger.info(f"[LLM END] {dt:.1f} ms")
    
    return resp

@wrap_tool_call
def trace_tool_call(request, handler):
    # 1. 提取工具名和参数
    tool_name = tool_call.get("name")
    tool_input = tool_call.get("args")
    
    logger.info(f"[TOOL START] {tool_name}")
    
    # 2. 执行工具
    result = handler(request)
    
    # 3. 打印结果
    dt = (time.time() - t0) * 1000
    logger.info(f"[TOOL END] {dt:.1f} ms")
    
    return result
```

#### UI 事件中间件

```python
# ui_events_middleware.py:113-189
@wrap_tool_call
def ui_tool_trace(request, handler):
    # 1. 提取工具名和参数
    tool_name = tool_call.get("name")
    tool_args = tool_call.get("args")
    
    # 2. 使用 LLM 生成友好描述
    description = _generate_tool_description_by_llm(tool_name, tool_args, user_question)
    
    # 3. 记录 tool_start 事件
    events.append({
        "kind": "tool_start",
        "name": tool_name,
        "title": description,
    })
    
    # 4. 执行工具
    result = handler(request)
    
    # 5. 记录 tool_end 事件
    events.append({
        "kind": "tool_end",
        "name": tool_name,
        "duration_ms": dt,
    })
    
    # 6. 注入到 ToolMessage
    result.additional_kwargs['ui_events'] = events
    
    return result

@wrap_model_call
def ui_model_trace(request, handler):
    # 1. 提取用户问题
    for msg in messages:
        if msg.type == 'human':
            CURRENT_QUESTION.set(msg.content)
    
    # 2. 清空当前回合的事件
    RUN_UI_EVENTS.set([])
    
    # 3. 执行模型
    resp = handler(request)
    
    # 4. 注入 ui_events 到 AIMessage
    events = RUN_UI_EVENTS.get()
    events.append({"kind": "llm_end", "duration_ms": dt})
    ai_msg.additional_kwargs["ui_events"] = events
    
    return resp
```

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

## 七、API 接口清单

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/v1/chat` | POST | 普通对话（非流式） |
| `/api/v1/chat/stream` | POST | 流式对话（SSE） |

---

## 八、增加新功能指南

### 8.1 增加新工具

**步骤 1**: 在 `database_tools.py` 或 `rag_tools.py` 中定义新工具

```python
@tool
def my_new_tool(param: str) -> str:
    """新工具说明"""
    # 工具逻辑
    return result
```

**步骤 2**: 在 `nl2sql_agent.py` 中注册工具

```python
tools = [
    # ... 现有工具 ...
    my_new_tool,  # 添加新工具
]
```

**步骤 3**: 在 `prompts.py` 的 SYSTEM_PROMPT 中添加工具说明

```python
**可用工具:**
...
6. my_new_tool(param) - 新工具说明
```

### 8.2 增加新中间件

**步骤 1**: 创建中间件文件

```python
# middleware/my_middleware.py
from langchain.agents.middleware import wrap_model_call, wrap_tool_call

@wrap_model_call
def my_model_middleware(request, handler):
    # 在调用 LLM 前后执行逻辑
    return handler(request)

@wrap_tool_call
def my_tool_middleware(request, handler):
    # 在调用工具前后执行逻辑
    return handler(request)
```

**步骤 2**: 在 `nl2sql_agent.py` 中注册

```python
middleware = []
middleware.extend([trace_model_call, trace_tool_call])
middleware.extend([ui_model_trace, ui_tool_trace])
middleware.extend([my_model_middleware, my_tool_middleware])  # 新增
```

### 8.3 修改 SSE 事件类型

**步骤 1**: 在后端 `api_server.py` 中添加新事件类型

```python
new_event = {
    'type': 'new_type',
    'data': {...}
}
yield f"data: {json.dumps(new_event)}\n\n"
```

**步骤 2**: 在前端 `ChatPanel.tsx` 中处理新事件

```typescript
} else if (data.type === 'new_type') {
  // 处理新事件
}
```

---

## 九、总结

### 模块现状

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

### 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| LangChain | 1.0.3 | Agent 框架 |
| LangChain Core | 1.0.3 | 核心组件 |
| LangChain OpenAI | 1.0.2 | LLM 接口 |
| SSE | - | 流式响应 |
| Milvus | - | 向量存储 |

### 注意事项

1. **SQL 执行互斥锁**: 使用 `_sql_execution_lock` 确保串行执行
2. **MySQL 5.7 兼容**: System Prompt 中强调禁用 WITH/窗口函数
3. **中间件顺序**: UI 事件中间件应在追踪中间件之后
4. **前端事件**: ui_events 注入到 AIMessage.additional_kwargs
