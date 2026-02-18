"""
主 Agent 逻辑模块：负责初始化、流程控制，只调用各功能模块，不做具体实现。
包含：create_nl2sql_agent 函数和全局 Vanna 客户端管理
"""

import logging
logger = logging.getLogger(__name__)

from typing import Optional
from langchain_openai import ChatOpenAI  # type: ignore
from langchain.agents import create_agent  # type: ignore


# 导入工具（使用相对导入）
from ..tools.database_tools import (
    get_all_tables_info,
    check_mysql_version,
    validate_sql_syntax,
    execute_sql
)
from ..tools.rag_tools import get_table_schema

# 导入中间件（使用相对导入）
from ..middleware import (
    trace_model_call,
    trace_tool_call,
    ui_model_trace,
    ui_tool_trace,
)

# 导入配置（使用相对导入）
from ..config.prompts import SYSTEM_PROMPT


# ==================== Agent 创建函数 ====================

def create_nl2sql_agent(llm: ChatOpenAI, enable_middleware: bool = True, enable_ui_events: bool = True):
    """创建 NL2SQL Agent（挂载 TraceMiddleware 和 UI 事件中间件）
    
    Args:
        llm: ChatOpenAI 模型实例
        enable_middleware: 是否启用中间件追踪（LLM/工具调用日志）
        enable_ui_events: 是否启用 UI 事件注入（用于前端展示）
        
    Returns:
        Agent 实例
    """
    # 定义基础工具
    tools = [
        get_all_tables_info,
        get_table_schema,
        check_mysql_version,
        validate_sql_syntax,
        execute_sql,
    ]
    
    # 中间件列表（按顺序执行）
    middleware = []
    if enable_middleware:
        middleware.extend([trace_model_call, trace_tool_call])
    if enable_ui_events:
        # UI 事件中间件应该在 trace 之后，这样可以利用 trace 的输出
        middleware.extend([ui_model_trace, ui_tool_trace])
    
    # 使用 LangChain 1.0 的 create_agent API（挂载中间件）
    agent = create_agent(
        llm, 
        tools, 
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,  # 挂载中间件
    )
    
    return agent
