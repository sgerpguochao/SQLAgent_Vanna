"""
NL2SQL FastAPI 服务
提供对话、训练数据管理等接口
"""
import os
import time
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
import asyncio
import json
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入 Vanna 客户端
from src.Improve.clients import create_vanna_client

# 导入 Agent 相关模块
from src.Improve.agent import create_nl2sql_agent, PostTrainingProcessor
from src.Improve.shared import set_vanna_client, set_api_key, set_llm_instance, get_last_query_result, clear_last_query_result

# 加载环境变量
load_dotenv()

# ==================== Pydantic 模型 ====================

class ChatRequest(BaseModel):
    """对话请求"""
    question: str = Field(..., description="用户问题", json_schema_extra={"example": "女性客户的平均消费金额是多少？"})
    stream: bool = Field(default=False, description="是否流式返回")
    enable_training: bool = Field(default=False, description="是否启用训练决策")

class ChatResponse(BaseModel):
    """对话响应"""
    question: str
    answer: str
    execution_time: float
    timestamp: str
    ui_events: Optional[List[Dict[str, Any]]] = Field(None, description="UI 事件列表（工具调用描述）")

class TrainingDataRequest(BaseModel):
    """添加训练数据请求"""
    data_type: str = Field(..., description="数据类型: 'sql', 'ddl', 'documentation'")
    content: Any = Field(..., description="训练数据内容（str 或 List[str]）")
    question: Optional[str] = Field(None, description="问题（仅 SQL 类型需要）")
    db_name: Optional[str] = Field("", description="数据库名称")
    table_name: Optional[str] = Field("", description="表名称（ddl/doc类型使用）")
    tables: Optional[str] = Field("", description="涉及的数据表（sql类型使用，逗号分隔）")

class TrainingDataResponse(BaseModel):
    """训练数据响应"""
    success: bool
    message: str
    ids: Optional[List[str]] = None

class DeleteTrainingDataRequest(BaseModel):
    """删除训练数据请求"""
    id: str = Field(..., description="训练数据 ID")

class DeleteTrainingDataResponse(BaseModel):
    """删除训练数据响应"""
    success: bool
    message: str

class QueryRequest(BaseModel):
    """查询请求"""
    query: Optional[str] = Field(None, description="自然语言查询")
    sql: Optional[str] = Field(None, description="SQL查询语句")
    table_name: Optional[str] = Field(None, description="表名")
    file_id: Optional[str] = Field(None, description="文件ID")
    limit: Optional[int] = Field(100, description="结果数量限制")
    db_name: Optional[str] = Field(None, description="数据库名称，用于切换数据库连接")

class QueryResponse(BaseModel):
    """查询响应"""
    success: bool
    data: List[Dict[str, Any]]
    columns: List[str]
    sql: Optional[str] = None
    answer: Optional[str] = None
    total_rows: int
    returned_rows: int

class DatabaseConnectionRequest(BaseModel):
    """数据库连接请求"""
    host: str = Field(..., description="数据库主机地址")
    port: str = Field(default="3306", description="数据库端口")
    username: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")
    database: Optional[str] = Field(None, description="数据库名称(可选)")

class DatabaseConnectionResponse(BaseModel):
    """数据库连接响应"""
    success: bool
    message: str
    databases: Optional[List[str]] = None
    tables: Optional[List[Dict[str, Any]]] = None

# ==================== FastAPI 应用（占位,会被 lifespan 覆盖）====================

app = None  # 会在下面的 lifespan 部分重新创建

# ==================== 全局变量 ====================

vn = None  # Vanna 客户端
agent = None  # Agent 实例
llm = None  # LLM 实例

# 数据库连接配置缓存 (db_name -> connection_config)
db_connection_configs: Dict[str, Dict[str, Any]] = {}

# ==================== 初始化函数 ====================

def initialize_system():
    """初始化 NL2SQL 系统"""
    global vn, agent, llm
    
    # 禁用代理
    os.environ.pop("HTTP_PROXY", None)
    os.environ.pop("HTTPS_PROXY", None)
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    os.environ.pop("ALL_PROXY", None)
    os.environ.pop("all_proxy", None)
    os.environ["LANGCHAIN_DEBUG"] = "false"
    
    # 读取配置
    api_key = os.getenv('API_KEY')
    base_url = os.getenv('BASE_URL')
    llm_model = os.getenv('LLM_MODEL', 'gpt-4o-mini')
    milvus_uri = os.getenv('MILVUS_URI')
    embedding_api_url = os.getenv('EMBEDDING_API_URL')
    embedding_provider = os.getenv('EMBEDDING_PROVIDER', 'jina')
    embedding_api_key = os.getenv('EMBEDDING_API_KEY')
    embedding_model_name = os.getenv('EMBEDDING_MODEL_NAME')
    metric_type = os.getenv('MILVUS_METRIC_TYPE', 'COSINE')
    mysql_host = os.getenv('MYSQL_HOST')
    mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
    mysql_database = os.getenv('MYSQL_DATABASE')
    mysql_user = os.getenv('MYSQL_USER')
    mysql_password = os.getenv('MYSQL_PASSWORD')
    llm_temperature = float(os.getenv('LLM_TEMPERATURE', '0.1'))
    llm_max_tokens = int(os.getenv('LLM_MAX_TOKENS', '14000'))
    
    # 验证必填参数
    required_params = {
        'API_KEY': api_key,
        'BASE_URL': base_url,
        'MILVUS_URI': milvus_uri,
        'EMBEDDING_API_URL': embedding_api_url,
        'MYSQL_HOST': mysql_host,
        'MYSQL_DATABASE': mysql_database,
        'MYSQL_USER': mysql_user,
        'MYSQL_PASSWORD': mysql_password,
    }
    
    missing_params = [k for k, v in required_params.items() if not v]
    if missing_params:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_params)}")
    
    logger.info("\nInitialize NL2SQL system...")

    # 创建 Vanna 客户端
    vn = create_vanna_client(
        openai_api_key=api_key,
        openai_base_url=base_url,
        model=llm_model,
        max_tokens=llm_max_tokens,
        milvus_uri=milvus_uri,
        embedding_api_url=embedding_api_url,
        embedding_provider=embedding_provider,
        embedding_api_key=embedding_api_key,
        embedding_model_name=embedding_model_name,
        metric_type=metric_type,
    )
    
    # 连接数据库
    vn.connect_to_mysql(
        host=mysql_host,
        dbname=mysql_database,
        user=mysql_user,
        password=mysql_password,
        port=mysql_port,
    )
    logger.info("Success connect to MySQL")

    # 设置全局上下文
    set_vanna_client(vn)
    set_api_key(api_key)
    
    # 创建 LLM
    llm = ChatOpenAI(
        model=llm_model,
        temperature=llm_temperature,
        openai_api_key=api_key,
        openai_api_base=base_url,
    )

    set_llm_instance(llm)
    
    # 创建 Agent（启用中间件和 UI 事件）
    logger.info("Creating NL2SQL Agent...")
    agent = create_nl2sql_agent(
        llm,
        enable_middleware=True,
        enable_ui_events=True  # 启用 UI 事件中间件
    )

    logger.info("System initialized successfully\n")

# ==================== 生命周期事件 ====================

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    initialize_system()
    yield
    # 关闭时清理（如果需要）
    logger.info("Service shutdown")

# 使用新的 lifespan 方式
app = FastAPI(
    title="NL2SQL API",
    description="将自然语言转换为 SQL 查询的智能服务",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源,生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# ==================== API 接口 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "NL2SQL API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/v1/chat",
            "add_training": "/api/v1/training/add",
            "get_training": "/api/v1/training/get",
            "delete_training": "/api/v1/training/delete"
        }
    }

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    对话接口：将自然语言问题转换为 SQL 并执行
    
    Args:
        request: 对话请求
        
    Returns:
        ChatResponse: 包含答案、SQL、执行时间等信息
    """
    if not agent:
        raise HTTPException(status_code=500, detail="System not initialized")
    
    start_time = time.time()
    
    try:
        # 准备配置
        cfg = {
            "configurable": {"thread_id": f"api-{int(time.time())}"},
            "recursion_limit": int(os.getenv('AGENT_RECURSION_LIMIT', '150')),
        }
        
        # 执行 Agent
        final_event = None
        for event in agent.stream(
            {"messages": [{"role": "user", "content": request.question}]},
            stream_mode="values",
            config=cfg,
        ):
            final_event = event
        
        if not final_event:
            raise HTTPException(status_code=500, detail="Agent execution failed")
        
        # 提取最终答案和 UI 事件
        messages = final_event.get("messages", [])
        answer = "Sorry, I cannot generate an answer"
        ui_events = None
        
        # 从后往前找最后一条 AI 消息
        for msg in reversed(messages):
            if getattr(msg, 'type', '') == 'ai':
                content = getattr(msg, 'content', '').strip()
                if content and len(content) > 10:
                    answer = content
                    # 提取 ui_events（如果存在）
                    additional_kwargs = getattr(msg, 'additional_kwargs', {})
                    ui_events = additional_kwargs.get('ui_events')
                    break
        
        elapsed = time.time() - start_time
        
        # 训练决策（如果启用）
        if request.enable_training and final_event:
            try:
                processor = PostTrainingProcessor()
                decision_result = processor.decide_and_add_to_training(
                    question=request.question,
                    conversation_history=final_event["messages"],
                    vanna_client=vn
                )
                logger.info(f"Training decision: {decision_result}")
            except Exception as e:
                logger.warning(f"Training decision failed: {e}")
        
        return ChatResponse(
            question=request.question,
            answer=answer,
            execution_time=elapsed,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            ui_events=ui_events
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口 - 两阶段响应
    
    第一阶段：实时推送 Agent 执行步骤
    第二阶段：流式返回最终答案
    
    SSE 事件格式：
    - {"type": "step", "action": "查询数据库结构", "status": "进行中"}
    - {"type": "step", "action": "生成SQL查询", "status": "完成"}
    - {"type": "answer", "content": "女性客户的平均...", "done": false}
    - {"type": "done"}
    
    Args:
        request: 对话请求
        
    Returns:
        StreamingResponse: SSE 流式响应
    """
    if not agent:
        raise HTTPException(status_code=500, detail="System not initialized")
    
    async def generate():
        try:
            cfg = {
                "configurable": {"thread_id": f"api-stream-{int(time.time())}"},
                "recursion_limit": int(os.getenv('AGENT_RECURSION_LIMIT', '150')),
            }
            
            final_event = None
            last_tool = None
 

            # 第一阶段：实时推送 Agent 执行步骤（流式的工具调用）
            for event in agent.stream(
                
                {"messages": [{"role": "user", "content": request.question}]},
                stream_mode="values",
                config=cfg,
            ):
                final_event = event
                messages = event.get("messages", [])
                
                if messages:
                    last_msg = messages[-1]
                    msg_type = getattr(last_msg, 'type', 'unknown')
                    
                    # 检测工具调用（立即推送工具名，等待 ToolMessage 中的描述）
                    if msg_type == 'ai' and hasattr(last_msg, 'tool_calls'):
                        for tool_call in last_msg.tool_calls:
                            tool_name = tool_call.get('name', 'unknown')
                            
                            if tool_name != last_tool:
                                last_tool = tool_name
                                
                                # 立即推送"准备中"状态（等待 ToolMessage 更新）
                                step_data = {
                                    'type': 'step',
                                    'action': f'{tool_name}',  # 只显示工具名
                                    'tool_name': tool_name,
                                    'status': 'preparing',
                                }
                                yield f"data: {json.dumps(step_data, ensure_ascii=False)}\n\n"
                    
                    # 检测工具执行结果（从 ToolMessage 读取 ui_events）
                    elif msg_type == 'tool' and last_tool:
                        # 从当前 ToolMessage 中读取 ui_events
                        additional_kwargs = getattr(last_msg, 'additional_kwargs', {})
                        ui_events = additional_kwargs.get('ui_events', [])

                        duration_ms = None
                        llm_description = None
                        tool_result = None

                        # 查找 tool_start（获取描述）和 tool_end（获取耗时）
                        for ui_event in ui_events:
                            if ui_event.get('name') == last_tool:
                                if ui_event.get('kind') == 'tool_start':
                                    llm_description = ui_event.get('title', '')
                                elif ui_event.get('kind') == 'tool_end':
                                    duration_ms = ui_event.get('duration_ms')

                        # 提取工具执行结果（截取前500字符避免过长）
                        tool_content = getattr(last_msg, 'content', '')
                        if tool_content:
                            tool_result = tool_content[:500] if len(tool_content) > 500 else tool_content

                        # 先推送"进行中"状态（带 LLM 描述）
                        if llm_description:
                            step_data = {
                                'type': 'step',
                                'action': llm_description,
                                'tool_name': last_tool,
                                'status': 'running',
                                'update': True  # 更新之前的状态
                            }
                            yield f"data: {json.dumps(step_data, ensure_ascii=False)}\n\n"

                        # 再推送"完成"状态（带耗时和结果）
                        step_data = {
                            'type': 'step',
                            'action': llm_description or f'{last_tool}',
                            'tool_name': last_tool,
                            'status': 'completed',
                            'duration_ms': duration_ms,
                            'result': tool_result,  # 添加工具执行结果
                            'update': True  # 更新之前的状态
                        }
                        yield f"data: {json.dumps(step_data, ensure_ascii=False)}\n\n"
                
                await asyncio.sleep(0.01)
            
            # 第二阶段：提取并推送查询数据
            if final_event:
                messages = final_event.get("messages", [])
                answer = None
                sql_query = None
                query_data = None

                logger.info(f"[Data Extraction] Total messages: {len(messages)}")

                # 从全局缓存中获取 DataFrame（execute_sql 工具执行时保存的）
                df = get_last_query_result()
                if df is not None and len(df) > 0:
                    # 将 DataFrame 转换为 JSON 格式（list of dicts）
                    # 处理 Decimal 类型，确保 JSON 序列化
                    import decimal
                    
                    def convert_decimal(obj):
                        """将 Decimal 转换为 float 或 string"""
                        if isinstance(obj, decimal.Decimal):
                            return float(obj)
                        elif isinstance(obj, dict):
                            return {k: convert_decimal(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [convert_decimal(item) for item in obj]
                        return obj
                    
                    query_data = df.to_dict('records')
                    query_data = [convert_decimal(record) for record in query_data]
                    
                    logger.info(f"[Data Extraction] Retrieved query data from cache, rows: {len(query_data)}")
                    # 清空缓存，避免下次查询获取到旧数据
                    clear_last_query_result()
                else:
                    logger.warning(f"[Data Extraction] No query result found in cache")

                # 提取执行的 SQL
                for msg in messages:
                    if getattr(msg, 'type', '') == 'ai' and hasattr(msg, 'tool_calls'):
                        for tool_call in msg.tool_calls:
                            if tool_call.get('name') == 'execute_sql':
                                args = tool_call.get('args', {})
                                sql_query = args.get('sql', '')
                                if sql_query:
                                    break
                        if sql_query:
                            break

                # 推送查询数据
                if query_data:
                    logger.info(f"[Data Extraction] Preparing to push data event, rows: {len(query_data)}, SQL: {sql_query[:100] if sql_query else 'None'}")
                    data_event = {
                        'type': 'data',
                        'data': query_data,
                        'columns': list(query_data[0].keys()) if query_data else [],
                        'sql': sql_query
                    }
                    yield f"data: {json.dumps(data_event, ensure_ascii=False)}\n\n"
                    logger.info(f"[Data Extraction] Data event pushed successfully")
                else:
                    logger.warning(f"[Data Extraction] No query data found, cannot push data event")

                # 提取最终答案：找最后一条非空的 AI 消息
                for msg in reversed(messages):
                    if getattr(msg, 'type', '') == 'ai':
                        content = getattr(msg, 'content', '').strip()
                        # 只要有实质内容就使用（无论是否有 tool_calls）
                        if content and len(content) > 10:
                            answer = content
                            break

                if answer:
                    # 处理图表
                    import re

                    # 匹配 ```chartconfig ... ``` 代码块
                    chartconfig_pattern = r'```chartconfig\s*\n?(.*?)\n?```'

                    # 先提取图表配置 JSON
                    chartconfig_match = re.search(chartconfig_pattern, answer, re.DOTALL)
                    chart_config = None
                    if chartconfig_match:
                        logger.info(f"[Answer Processing] Chart config JSON detected, removing from answer")
                        try:
                            # 提取 JSON 内容
                            chart_config_str = chartconfig_match.group(1).strip()
                            chart_config = json.loads(chart_config_str)
                            logger.info(f"[Answer Processing] Chart config JSON extracted and parsed successfully")
                        except json.JSONDecodeError as e:
                            logger.warning(f"[Answer Processing] Chart config JSON parsing failed: {e}")
                            chart_config = None
                        except Exception as e:
                            logger.warning(f"[Answer Processing] Chart config extraction failed: {e}")
                            chart_config = None

                        # 从答案中移除图表配置代码块
                        answer = re.sub(chartconfig_pattern, '', answer, flags=re.DOTALL).strip()
                        logger.info(f"[Answer Processing] Chart config removed from answer, remaining length: {len(answer)}")

                    # 推送图表配置（如果存在）
                    if chart_config:
                        logger.info(f"[Chart Config] Preparing to push chart config")
                        chart_event = {
                            'type': 'chart_config',
                            'config': chart_config
                        }
                        yield f"data: {json.dumps(chart_event, ensure_ascii=False)}\n\n"
                        logger.info(f"[Chart Config] Chart config pushed successfully")

                    # 流式推送 增量 Token
                    for i, char in enumerate(answer):
                        chunk_data = {
                            'type': 'answer',
                            'content': char,
                            'done': False
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.02)  

            # 结束标记
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            error_data = {'type': 'error', 'message': str(e)}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/v1/training/add", response_model=TrainingDataResponse)
async def add_training_data(request: TrainingDataRequest):
    """
    添加训练数据
    
    Args:
        request: 训练数据请求
        
    Returns:
        TrainingDataResponse: 添加结果
    """
    if not vn:
        raise HTTPException(status_code=500, detail="System not initialized")
    
    try:
        ids = None

        if request.data_type == "sql":
            if not request.question:
                raise HTTPException(status_code=400, detail="SQL type requires question parameter")
            if not isinstance(request.content, str):
                raise HTTPException(status_code=400, detail="SQL type content must be a string")
            ids = [vn.add_question_sql(
                question=request.question,
                sql=request.content,
                db_name=request.db_name,
                tables=request.tables
            )]

        elif request.data_type == "ddl":
            ids = vn.add_ddl(
                request.content,
                db_name=request.db_name,
                table_name=request.table_name
            )
            if isinstance(ids, str):
                ids = [ids]

        elif request.data_type == "documentation":
            ids = vn.add_documentation(
                request.content,
                db_name=request.db_name,
                table_name=request.table_name
            )
            if isinstance(ids, str):
                ids = [ids]
        else:
            raise HTTPException(status_code=400, detail="Invalid data_type, must be 'sql', 'ddl', or 'documentation'")
        
        return TrainingDataResponse(
            success=True,
            message=f"Successfully added {len(ids)} {request.data_type} training data",
            ids=ids
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add training data: {str(e)}")

@app.get("/api/v1/training/get")
async def get_training_data(
    limit: int = 100,
    offset: int = 0,
    data_type: Optional[str] = None
):
    """
    获取训练数据
    
    Args:
        limit: 返回数量限制
        offset: 偏移量
        data_type: 数据类型过滤 ('sql', 'ddl', 'doc')
        
    Returns:
        训练数据列表
    """
    if not vn:
        raise HTTPException(status_code=500, detail="System not initialized")
    
    try:
        df = vn.get_training_data()

        # 添加 data_type 列，根据数据内容判断
        def extract_data_type(row):
            # 如果有 question 字段且不为空，说明是 SQL 查询
            if 'question' in row.index and pd.notna(row['question']) and row['question']:
                return 'sql'
            # 如果 content 包含 CREATE TABLE，说明是 DDL
            elif 'content' in row.index and pd.notna(row['content']) and 'CREATE TABLE' in str(row['content']).upper():
                return 'ddl'
            # 否则判断为文档
            elif 'content' in row.index and pd.notna(row['content']):
                return 'documentation'
            else:
                return 'unknown'

        df['data_type'] = df.apply(extract_data_type, axis=1)

        # 过滤数据类型
        if data_type:
            suffix_map = {
                'sql': '-sql',
                'ddl': '-ddl',
                'doc': '-doc',
                'documentation': '-doc'
            }
            suffix = suffix_map.get(data_type.lower())
            if suffix:
                df = df[df['id'].str.endswith(suffix)]

        # 分页
        total = len(df)
        df = df.iloc[offset:offset + limit]

        # 替换 NaN 值为 None，以便 JSON 序列化
        df = df.fillna(value=pd.NA)

        # 转换为字典时处理 NA 值
        records = df.to_dict(orient='records')
        # 将 pd.NA 转换为 None
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None

        return {
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": records
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get training data: {str(e)}")

@app.delete("/api/v1/training/delete", response_model=DeleteTrainingDataResponse)
async def delete_training_data(request: DeleteTrainingDataRequest):
    """
    删除训练数据
    
    Args:
        request: 删除请求
        
    Returns:
        DeleteTrainingDataResponse: 删除结果
    """
    if not vn:
        raise HTTPException(status_code=500, detail="System not initialized")
    
    try:
        success = vn.remove_training_data(request.id)
        
        if success:
            return DeleteTrainingDataResponse(
                success=True,
                message=f"Successfully deleted training data: {request.id}"
            )
        else:
            return DeleteTrainingDataResponse(
                success=False,
                message=f"Deletion failed: ID not found or invalid format: {request.id}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete training data: {str(e)}")

@app.post("/api/v1/database/test", response_model=DatabaseConnectionResponse)
async def test_database_connection(request: DatabaseConnectionRequest):
    """
    测试数据库连接

    Args:
        request: 数据库连接请求

    Returns:
        DatabaseConnectionResponse: 测试结果
    """
    try:
        import pymysql

        # 尝试连接数据库
        connection = pymysql.connect(
            host=request.host,
            port=int(request.port),
            user=request.username,
            password=request.password,
            database=request.database if request.database else None,
            connect_timeout=5
        )

        connection.close()

        return DatabaseConnectionResponse(
            success=True,
            message="Database connection test successful!"
        )

    except Exception as e:
        logger.warning(f"Database connection test failed: {str(e)}")
        return DatabaseConnectionResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )

@app.post("/api/v1/database/connect", response_model=DatabaseConnectionResponse)
async def connect_database(request: DatabaseConnectionRequest):
    """
    连接数据库并获取表结构

    Args:
        request: 数据库连接请求

    Returns:
        DatabaseConnectionResponse: 包含数据库列表和表结构
    """
    global vn

    try:
        import pymysql

        # 连接到MySQL服务器(不指定数据库)
        connection = pymysql.connect(
            host=request.host,
            port=int(request.port),
            user=request.username,
            password=request.password,
            connect_timeout=5
        )

        cursor = connection.cursor()

        # 如果指定了数据库,直接使用该数据库
        if request.database:
            cursor.execute(f"USE `{request.database}`")

            # 获取该数据库的所有表
            cursor.execute("SHOW TABLES")
            tables_raw = cursor.fetchall()

            tables = []
            for (table_name,) in tables_raw:
                # 获取每个表的列信息
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns = cursor.fetchall()

                table_info = {
                    "name": table_name,
                    "type": "table",
                    "children": [
                        {
                            "name": col[0],
                            "type": "column",
                            "dataType": col[1],
                            "nullable": col[2] == "YES",
                            "key": col[3],
                            "default": col[4],
                            "extra": col[5]
                        }
                        for col in columns
                    ]
                }
                tables.append(table_info)

            cursor.close()
            connection.close()

            # 保存数据库连接配置到全局缓存
            if request.database and request.host and request.username:
                db_connection_configs[request.database] = {
                    "host": request.host,
                    "dbname": request.database,
                    "user": request.username,
                    "password": request.password,
                    "port": int(request.port)
                }
                logger.info(f"Cached connection config for database: {request.database}")

            # 更新全局vn客户端连接
            if vn:
                try:
                    vn.connect_to_mysql(
                        host=request.host,
                        dbname=request.database,
                        user=request.username,
                        password=request.password,
                        port=int(request.port)
                    )
                    logger.info(f"Switched to database: {request.database}")
                except Exception as e:
                    logger.warning(f"Failed to update vn connection: {str(e)}")

            return DatabaseConnectionResponse(
                success=True,
                message=f"Successfully connected to database {request.database}",
                databases=[request.database],
                tables=tables
            )
        else:
            # 未指定数据库,返回所有数据库列表
            cursor.execute("SHOW DATABASES")
            databases = [db[0] for db in cursor.fetchall()]

            # 过滤掉系统数据库
            databases = [db for db in databases if db not in ['information_schema', 'mysql', 'performance_schema', 'sys']]

            cursor.close()
            connection.close()

            return DatabaseConnectionResponse(
                success=True,
                message="Successfully connected to MySQL server",
                databases=databases,
                tables=[]
            )

    except Exception as e:
        logger.warning(f"Database connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

@app.post("/api/query", response_model=QueryResponse)
async def query_data(request: QueryRequest):
    """
    执行数据查询

    Args:
        request: 查询请求

    Returns:
        查询结果
    """
    global vn

    if not vn:
        raise HTTPException(status_code=500, detail="System not initialized")

    # 如果提供了 db_name，切换到对应的数据库连接
    if request.db_name:
        if request.db_name in db_connection_configs:
            config = db_connection_configs[request.db_name]
            try:
                vn.connect_to_mysql(**config)
                logger.info(f"[Query] Switched to database: {request.db_name}")
            except Exception as e:
                logger.warning(f"[Query] Failed to switch to database {request.db_name}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to connect to database {request.db_name}: {str(e)}")
        else:
            logger.warning(f"[Query] Database {request.db_name} not found in connection cache")
            raise HTTPException(status_code=400, detail=f"Database {request.db_name} not found. Please reconnect to this database first.")

    try:
        # 如果提供了SQL，直接执行
        if request.sql:
            logger.info(f"[Direct SQL Query] Executing SQL: {request.sql[:100]}...")
            df = vn.run_sql(request.sql)

            if df is None or df.empty:
                return QueryResponse(
                    success=True,
                    data=[],
                    columns=[],
                    sql=request.sql,
                    answer="Query successful, but no results returned",
                    total_rows=0,
                    returned_rows=0
                )

            return QueryResponse(
                success=True,
                data=df.to_dict(orient='records'),
                columns=df.columns.tolist(),
                sql=request.sql,
                answer=f"Query successful, returned {len(df)} records",
                total_rows=len(df),
                returned_rows=len(df)
            )

        # 如果提供了自然语言查询，使用vanna生成SQL
        elif request.query:
            logger.info(f"[Natural Language Query] Question: {request.query}")

            # 使用vanna生成SQL
            generated_sql = vn.generate_sql(question=request.query)
            logger.info(f"[Generated SQL] {generated_sql}")

            if not generated_sql:
                raise HTTPException(status_code=500, detail="Unable to generate SQL query")

            # 执行SQL
            df = vn.run_sql(generated_sql)

            if df is None or df.empty:
                return QueryResponse(
                    success=True,
                    data=[],
                    columns=[],
                    sql=generated_sql,
                    answer="Query successful, but no results returned",
                    total_rows=0,
                    returned_rows=0
                )

            # 生成自然语言答案（简化版本）
            answer = f"Query successful, found {len(df)} records"

            limit = request.limit or 100
            return QueryResponse(
                success=True,
                data=df.head(limit).to_dict(orient='records'),
                columns=df.columns.tolist(),
                sql=generated_sql,
                answer=answer,
                total_rows=len(df),
                returned_rows=min(len(df), limit)
            )
        else:
            raise HTTPException(status_code=400, detail="Must provide either query or sql parameter")

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "vanna_initialized": vn is not None,
        "agent_initialized": agent is not None,
        "llm_initialized": llm is not None,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }

# ==================== 主函数 ====================

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='NL2SQL API Server')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务监听地址')
    parser.add_argument('--port', type=int, default=8100, help='服务监听端口')
    parser.add_argument('--reload', action='store_true', help='开发模式（热重载）')
    args = parser.parse_args()
    
    # 启动服务
    logger.info(f"\nStarting NL2SQL API service")
    logger.info(f"Listening on: {args.host}:{args.port}")
    logger.info(f"API docs: http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/docs\n")
    
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )
