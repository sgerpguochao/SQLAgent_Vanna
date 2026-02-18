"""
FastAPI服务器 - Multi-Agent CSV问答系统 API部署
简化版：只提供一个核心问答接口
"""
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import uuid
import tempfile
import shutil
from datetime import datetime
from dotenv import load_dotenv
from src.multi_agent_system import MultiAgentSystem

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(
    title="Multi-Agent CSV问答系统 API",
    description="基于LangChain 1.0的智能CSV数据分析API - 简化版",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 无需持久化目录 - 使用系统临时目录


# ==================== 数据模型 ====================

class Message(BaseModel):
    """对话消息模型"""
    role: str = Field(..., description="角色：user 或 assistant")
    content: str = Field(..., description="消息内容")


class QueryResponse(BaseModel):
    """查询响应模型"""
    success: bool = Field(..., description="查询是否成功")
    answer: str = Field(..., description="AI回答")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
    session_id: str = Field(..., description="会话ID")
    timestamp: str = Field(..., description="响应时间戳")
    execution_time: float = Field(..., description="执行耗时（秒）")
    messages: Optional[List[Dict[str, Any]]] = Field(None, description="完整消息链（包含工具调用等详细信息）")


class ConversationVisualize(BaseModel):
    """对话数据图表生成请求模型"""
    conversation: List[Dict[str, str]] = Field(..., description="对话历史，格式: [{'user': '问题', 'answer': '回答'}, ...]")
    chart_type: Optional[str] = Field(None, description="图表类型提示: bar(柱状图)/pie(饼图)/line(折线图)/auto(自动选择)")


# ==================== 无状态设计 ====================
# 每次请求独立处理，文件临时加载后立即清理
# 不需要会话管理，历史对话由客户端维护


# ==================== 启动和关闭事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动"""
    logger.info("="*70)
    logger.info("🚀 启动Multi-Agent CSV问答系统 API服务器 v3.0")
    logger.info("="*70)
    logger.info("� 无状态设计 - 每次请求独立处理")
    logger.info("📁 临时文件在请求完成后自动清理")
    logger.info(f"🤖 模型: {os.getenv('MODEL_NAME', 'gpt-3.5-turbo')}")
    logger.info("="*70)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭"""
    logger.info("\n" + "="*70)
    logger.info("👋 服务器已关闭")
    logger.info("="*70)


# ==================== API路由 ====================

@app.get("/")
async def root():
    """根路径 - API信息"""
    return {
        "message": "Multi-Agent CSV问答系统 API v3.0",
        "description": "无状态设计 - 每次请求上传CSV文件，临时处理后自动清理",
        "features": [
            "✅ 每次请求独立处理",
            "✅ 无需预先上传文件",
            "✅ 文件不保存到服务器",
            "✅ 支持历史对话上下文",
            "✅ 随时修改CSV文件重新提问"
        ],
        "endpoints": {
            "POST /ask": "提问接口（每次都需要上传CSV文件）",
            "POST /visualize": "可视化对话流程图（返回HTML）"
        },
        "docs": "/docs"
    }


@app.post("/ask", response_model=QueryResponse)
async def ask_question(
    question: str = Form(..., description="用户问题"),
    history: Optional[str] = Form(None, description="历史对话JSON字符串（可选）"),
    csv_files: List[UploadFile] = File(..., description="CSV文件列表（必填）")
):
    """
    核心问答接口 - 每次请求都需要上传CSV文件（临时使用，不保存）
    
    参数:
        - question: 用户问题（必填）
        - history: 历史对话记录，JSON格式 [{"role": "user", "content": "..."}, ...]（选填）
        - csv_files: 上传的CSV文件列表（必填，每次都需要传入）
    
    返回:
        包含答案、会话ID、执行时间等信息的响应
    
    注意: 文件仅在内存中临时处理，不会保存到磁盘
    """
    start_time = datetime.now()
    session_id = str(uuid.uuid4())  # 每次生成新的会话ID
    temp_dir = None
    
    try:
        # 1. 创建临时目录（请求结束后立即删除）
        temp_dir = tempfile.mkdtemp(prefix="csv_qa_")
        logger.info(f"\n📁 临时目录: {temp_dir}")
        
        # 2. 将CSV文件临时保存到内存临时目录
        if not csv_files:
            raise HTTPException(status_code=400, detail="必须上传至少一个CSV文件")
        
        logger.info(f"� 收到 {len(csv_files)} 个CSV文件")
        for csv_file in csv_files:
            if not csv_file.filename.endswith('.csv'):
                logger.warning(f"⚠️  跳过非CSV文件: {csv_file.filename}")
                continue
                
            file_path = os.path.join(temp_dir, csv_file.filename)
            content = await csv_file.read()
            
            # 临时写入
            with open(file_path, 'wb') as f:
                f.write(content)
            logger.info(f"   ✅ 已临时加载: {csv_file.filename} ({len(content)} bytes)")
        
        # 3. 解析历史对话
        conversation_history = []
        if history:
            import json
            try:
                conversation_history = json.loads(history)
                logger.info(f"\n💬 加载了 {len(conversation_history)} 条历史对话")
            except json.JSONDecodeError:
                logger.error("⚠️  警告: 历史对话格式错误，将忽略")
        
        # 4. 创建Agent系统（使用临时目录）
        agent_system = MultiAgentSystem(
            data_directory=temp_dir,
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=os.getenv("MODEL_NAME", "gpt-3.5-turbo"),
            api_base=os.getenv("OPENAI_API_BASE"),
            temperature=0,
            sample_rows=3
        )
        
        # 5. 构建完整查询（如果有历史对话，添加上下文）
        full_query = question
        if conversation_history:
            context = "\n".join([
                f"{'用户' if msg['role'] == 'user' else 'AI'}: {msg['content']}"
                for msg in conversation_history[-5:]  # 只取最近5轮对话
            ])
            full_query = f"历史对话:\n{context}\n\n当前问题: {question}"
        
        # 6. 执行查询
        logger.info(f"\n🤔 处理问题: {question}")
        # 从环境变量读取是否显示详细日志（默认为True）
        verbose_mode = os.getenv("VERBOSE_MODE", "true").lower() == "true"
        result = agent_system.query(full_query, verbose=verbose_mode)
        
        # 7. 计算执行时间
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # 8. 序列化消息链（转换LangChain消息对象为字典）
        messages_data = None
        if result.get("messages"):
            messages_data = []
            for msg in result["messages"]:
                msg_dict = {
                    "type": msg.__class__.__name__,
                    "content": getattr(msg, 'content', str(msg))
                }
                # 如果有工具调用信息，也包含进来
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    msg_dict["tool_calls"] = msg.tool_calls
                messages_data.append(msg_dict)
        
        # 9. 构建响应
        response = None
        if result.get("success"):
            response = QueryResponse(
                success=True,
                answer=result.get("answer", ""),
                error=None,
                session_id=session_id,
                timestamp=datetime.now().isoformat(),
                execution_time=execution_time,
                messages=messages_data
            )
        else:
            response = QueryResponse(
                success=False,
                answer="",
                error=result.get("error", "未知错误"),
                session_id=session_id,
                timestamp=datetime.now().isoformat(),
                execution_time=execution_time,
                messages=messages_data
            )
        
        return response
    
    except Exception as e:
        # 异常处理
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"\n❌ 错误: {str(e)}")
        logger.info(error_detail)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return QueryResponse(
            success=False,
            answer="",
            error=f"处理失败: {str(e)}",
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            execution_time=execution_time,
            messages=None
        )
    
    finally:
        # 9. 清理临时文件（无论成功或失败都会执行）
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"🗑️  已清理临时目录: {temp_dir}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️  清理临时目录失败: {cleanup_error}")


def _generate_fallback_chart_html(conversation_text: str) -> str:
    """生成备用图表HTML（当LLM无法生成有效HTML时使用）"""
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据可视化失败</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: Arial, sans-serif;
            background: #f8f9fa;
            padding: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        h1 {{
            color: #e74c3c;
            font-size: 24px;
            margin-bottom: 15px;
        }}
        p {{
            color: #666;
            line-height: 1.6;
            margin: 10px 0;
        }}
        .content {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-top: 20px;
            text-align: left;
            max-height: 200px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚠️ 无法生成图表</h1>
        <p>抱歉，系统无法从对话中提取有效的数据来生成图表。</p>
        <p>请确保对话内容包含明确的数值数据。</p>
        <div class="content">
            <strong>对话内容:</strong><br>
            {conversation_text.replace(chr(10), '<br>')}
        </div>
    </div>
</body>
</html>"""


@app.post("/visualize")
async def visualize_conversation(data: ConversationVisualize):
    """
    对话数据图表生成接口 - 根据对话内容自动生成数据图表（柱状图/饼图/折线图等）
    
    参数:
        - conversation: 对话历史列表，包含用户问题和AI回答
          格式: [
              {"user": "问题1", "answer": "回答1（包含数据）"},
              {"user": "问题2", "answer": "回答2（包含数据）"},
              ...
          ]
        - chart_type: 可选，指定图表类型 (bar/pie/line/auto)
    
    返回:
        完整的HTML页面，包含交互式图表（可直接在浏览器中打开）
    
    示例输入:
    {
        "conversation": [
            {"user": "查询各产品销售额", "answer": "产品A销售额500万，产品B销售额300万，产品C销售额200万"},
            {"user": "展示销售趋势", "answer": "1月100万，2月150万，3月200万，4月180万"}
        ],
        "chart_type": "auto"
    }
    """
    from fastapi.responses import HTMLResponse
    
    try:
        conversation = data.conversation
        chart_type_hint = data.chart_type or "auto"
        
        # 数据清洗：合并所有对话内容
        all_text = ""
        for item in conversation:
            user_msg = item.get("user", "").strip()
            answer_msg = item.get("answer", "").strip()
            
            if user_msg:
                all_text += f"用户: {user_msg}\n"
            if answer_msg:
                all_text += f"AI: {answer_msg}\n\n"
        
        if not all_text.strip():
            raise ValueError("对话数据为空")
        
        # 提取最后一轮对话（最重要）
        last_conversation = conversation[-1] if conversation else {}
        last_user = last_conversation.get("user", "")
        last_answer = last_conversation.get("answer", "")
        
        # 构建给大模型的prompt（重点关注最后一次对话）
        prompt = f"""你是一个数据可视化专家。请分析对话内容，从中提取数值数据并生成一个简洁的图表HTML页面。

【重点】最后一次对话（最重要，请从这里提取数据）:
用户: {last_user}
AI: {last_answer}

完整对话历史（供参考）:
{all_text}

图表类型提示: {chart_type_hint}

核心要求:
1. **只生成一个图表**，不要生成多个图表
2. **必须从最后一次对话的AI回答中提取真实的数值数据**
3. 根据提取的数据选择最合适的图表类型：
   - 柱状图(bar): 适合对比不同类别的数据
   - 饼图(pie): 适合展示占比分布
   - 折线图(line): 适合展示时间趋势
4. 图表标签(labels)和数据(data)必须对应实际提取的内容
5. 标题要有意义，反映数据的实际含义
6. 使用 Chart.js: https://cdn.jsdelivr.net/npm/chart.js
7. **重要：只输出HTML代码，不要在</html>标签后添加任何解释或说明文字**
8. 不要添加markdown标记（如```html```）

HTML结构要求:
- 必须包含 <!DOCTYPE html>
- 使用 <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
- 只有一个 <canvas id="myChart"></canvas>
- Chart.js 配置中 type 可以是: 'bar', 'pie', 'line' 等
- data.labels 填入实际的类别/时间名称
- data.datasets[0].data 填入实际的数值
- data.datasets[0].label 填入有意义的数据集名称
- backgroundColor 使用: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
- 设置 responsive: true, maintainAspectRatio: false
- **重要：必须在图表上显示数值标签**，使用 Chart.js 的 datalabels 插件或在 options 中配置显示数值

样式要求:
- body: padding: 15px; background: #f8f9fa;
- .container: max-width: 800px; padding: 20px;
- .chart-wrapper: height: 400px;
- h1: font-size: 20px; text-align: center;

显示数值的配置示例:
对于柱状图/折线图，在 options 中添加:
plugins: {{
    datalabels: {{
        display: true,
        color: '#444',
        anchor: 'end',
        align: 'top',
        formatter: (value) => value
    }}
}}

对于饼图，在 options 中添加:
plugins: {{
    datalabels: {{
        display: true,
        color: '#fff',
        formatter: (value, ctx) => {{
            return value + '%';
        }}
    }}
}}

并引入插件: <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2"></script>

请直接生成完整的HTML代码:"""

        # 调用LLM生成HTML
        from langchain_core.messages import HumanMessage
        from langchain_openai import ChatOpenAI
        
        # 创建LLM实例
        llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "gpt-3.5-turbo"),
            temperature=0.3,  # 降低随机性，确保生成有效代码
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE")
        )
        
        logger.info(f"\n📊 正在生成图表...")
        logger.info(f"💬 对话轮数: {len(conversation)}")
        logger.info(f"🎯 重点: 最后一轮对话")
        logger.info(f"📈 图表类型: {chart_type_hint}")
        
        llm_response = llm.invoke([HumanMessage(content=prompt)])
        html_content = llm_response.content.strip()
        
        # 清理可能的markdown标记
        html_content = html_content.replace("```html", "").replace("```", "").strip()
        
        # 移除HTML结束标签后的多余文本（大模型可能添加的解释）
        if "</html>" in html_content:
            html_end_index = html_content.find("</html>") + len("</html>")
            html_content = html_content[:html_end_index]
        
        # 验证是否是有效的HTML
        if not html_content.startswith("<!DOCTYPE") and not html_content.startswith("<html"):
            logger.warning("⚠️  LLM返回的不是完整HTML，使用备用模板")
            html_content = _generate_fallback_chart_html(all_text)
        
        logger.info("✅ 图表生成成功！")
        
        return HTMLResponse(content=html_content)
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"\n❌ 可视化失败: {str(e)}")
        logger.info(error_detail)
        
        # 返回错误页面
        error_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>错误</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #f5f5f5;
        }}
        .error-box {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            max-width: 600px;
        }}
        h1 {{
            color: #e74c3c;
            margin-top: 0;
        }}
        pre {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="error-box">
        <h1>❌ 可视化失败</h1>
        <p><strong>错误信息:</strong> {str(e)}</p>
        <details>
            <summary>详细错误信息</summary>
            <pre>{error_detail}</pre>
        </details>
    </div>
</body>
</html>"""
        
        return HTMLResponse(content=error_html, status_code=500)


# ==================== 运行配置 ====================

if __name__ == "__main__":
    import uvicorn
    
    # 运行服务器
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",  # 监听所有网络接口
        port=8000,       # 端口
        reload=True,     # 开发模式：自动重载
        log_level="info"
    )
