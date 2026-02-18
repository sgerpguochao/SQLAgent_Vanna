"""
基于 LangChain 1.0 create_agent 的 NL2SQL Agent
使用官方 Agent API 实现 ReAct 推理模式

模块化设计：所有功能通过导入实现，主文件只负责流程控制
"""
import os
import sys
import time
import argparse
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 导入 Vanna 客户端
from src.Improve.clients import create_vanna_client

# 导入 Agent 相关模块
from src.Improve.agent import create_nl2sql_agent, PostTrainingProcessor
from src.Improve.shared import set_vanna_client, set_api_key, set_llm_instance

# 导入配置
from src.Improve.config import (
    TEST_QUESTIONS,
)


def main():
    """主函数"""
    # ==================== 解析命令行参数 ====================
    parser = argparse.ArgumentParser(description='NL2SQL Agent with LangChain 1.0')
    parser.add_argument('test_key', nargs='?', default=None, 
                       help='测试问题键 (electronics_simple/electronics_complex/clothing_simple/clothing_complex)')
    parser.add_argument('--enable-training', action='store_true', default=True, 
                       help='启用训练工具（允许 Agent 将优质 SQL 加入训练集）')
    parser.add_argument('--enable-middleware', action='store_true', default=False,
                       help='启用中间件追踪（详细的LLM/工具调用日志，自动精简 get_all_tables_info 和 get_table_schema 输出）')
    args = parser.parse_args()
    
    # 直接使用参数
    enable_middleware = args.enable_middleware

    # === 禁用代理（避免 SOCKS 代理错误）===
    os.environ.pop("HTTP_PROXY", None)
    os.environ.pop("HTTPS_PROXY", None)
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    os.environ.pop("ALL_PROXY", None)
    os.environ.pop("all_proxy", None)

    # === 全局 Debug（始终关闭 LangChain 默认调试）===
    os.environ["LANGCHAIN_DEBUG"] = "false"
    
    # === 显示当前模式 ===
    print("🔍 追踪模式:")
    if enable_middleware:
        print("  ✅ 中间件追踪: 已启用")
        print("  📦 工具输出: get_all_tables_info 和 get_table_schema 将自动精简显示")
    else:
        print("  ❌ 中间件追踪: 已禁用")
        print("  💡 提示: 使用 --enable-middleware 启用追踪")
    
        # ==================== 加载环境变量 ====================
    load_dotenv()  # 自动查找当前目录的 .env 文件
    
    # 必填参数（从 .env 读取）
    api_key = os.getenv('API_KEY')
    base_url = os.getenv('BASE_URL')
    llm_model = os.getenv('LLM_MODEL', 'gpt-4o-mini')  # 有默认值
    
    milvus_uri = os.getenv('MILVUS_URI')
    embedding_api_url = os.getenv('EMBEDDING_API_URL')
    
    # 可选参数（从 .env 读取，有默认值）
    embedding_provider = os.getenv('EMBEDDING_PROVIDER', 'jina')
    embedding_api_key = os.getenv('EMBEDDING_API_KEY')  # 可选
    embedding_model_name = os.getenv('EMBEDDING_MODEL_NAME')  # 可选
    metric_type = os.getenv('MILVUS_METRIC_TYPE', 'COSINE')
    
    # MySQL 配置（从 .env 读取）
    mysql_host = os.getenv('MYSQL_HOST')
    mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
    mysql_database = os.getenv('MYSQL_DATABASE')
    mysql_user = os.getenv('MYSQL_USER')
    mysql_password = os.getenv('MYSQL_PASSWORD')
    
    # LLM 生成参数（从 .env 读取，有默认值）
    llm_temperature = float(os.getenv('LLM_TEMPERATURE', '0.1'))
    llm_max_tokens = int(os.getenv('LLM_MAX_TOKENS', '14000'))
    
    # Agent 配置（从 .env 读取，有默认值）
    agent_recursion_limit = int(os.getenv('AGENT_RECURSION_LIMIT', '150'))
    
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
        print(f"❌ 缺少必填环境变量: {', '.join(missing_params)}")
        print(f"💡 请在 .env 文件中配置这些参数（参考 .env.example）")
        sys.exit(1)

    print("\n🚀 初始化 NL2SQL Agent (LangChain 1.0)...")
    if args.enable_training:
        print("✨ 训练模式已启用 - Agent 可以自主将优质 SQL 加入训练集")
    
    # ==================== 1. 创建 Vanna 客户端 ====================
    vn = create_vanna_client(
        # 必填参数
        openai_api_key=api_key,
        openai_base_url=base_url,
        model=llm_model,
        max_tokens=llm_max_tokens,
        milvus_uri=milvus_uri,
        embedding_api_url=embedding_api_url,
        # 可选参数（使用 .env 配置或默认值）
        embedding_provider=embedding_provider,
        embedding_api_key=embedding_api_key,
        embedding_model_name=embedding_model_name,
        metric_type=metric_type,
    )
    
    # ==================== 2. 连接数据库 ====================
    vn.connect_to_mysql(
        host=mysql_host,
        dbname=mysql_database,
        user=mysql_user,
        password=mysql_password,
        port=mysql_port,
    )
    print("✅ 数据库连接成功")
    
    # 测试连接
    vn.get_similar_question_sql("How many products are there?")

    # ==================== 3. 训练模型 ====================
    try:
        from nl2sql_training_data import get_documentations, get_ddls
        print("📚 加载训练数据...")
        vn.train(documentation=get_documentations())
        vn.train(ddl=get_ddls())
        print("✅ 训练数据加载完成")
    except Exception as e:
        print(f"⚠️ 训练数据加载失败: {e}")
    
    # ==================== 4. 设置全局 Vanna 客户端（供工具访问）====================
    set_vanna_client(vn)
    set_api_key(api_key)
    
    # ==================== 5. 创建 LLM（全局单例，避免重复创建）====================
    llm = ChatOpenAI(
        model=llm_model,
        temperature=llm_temperature,
        openai_api_key=api_key,
        openai_api_base=base_url,
    )
    
    # 保存到全局上下文，供 PostTrainingProcessor 等模块复用
    set_llm_instance(llm)
    
    # ==================== 6. 创建 Agent ====================
    print("🤖 创建 NL2SQL Agent...")
    agent = create_nl2sql_agent(
        llm, 
        enable_middleware=enable_middleware,
    )
    
    # ==================== 7. 选择测试问题 ====================
    if args.test_key:
        if args.test_key not in TEST_QUESTIONS:
            print(f"❌ 无效的测试问题键: {args.test_key}")
            print(f"可用键: {', '.join(TEST_QUESTIONS.keys())}")
            sys.exit(1)
        test_question = TEST_QUESTIONS[args.test_key]
    else:
        # 默认使用服装复杂问题
        test_question = TEST_QUESTIONS["clothing_complex"]
        print(f"💡 提示: 可通过命令行参数选择测试问题，例如:")
        print(f"   python react_agent.py electronics_complex")
        print(f"   python react_agent.py clothing_simple --enable-training")
        print(f"   python react_agent.py clothing_complex --enable-training")
        print()
    
    print("\n" + "="*80)
    print("🤖 NL2SQL Agent (LangChain 1.0)")
    print("="*80)
    print(f"📝 问题: {test_question}")
    print(f"⏱️  开始时间: {time.strftime('%H:%M:%S')}")
    print("="*80 + "\n")
    
    start_time = time.time()
    
    # ==================== 8. 准备配置 ====================
    cfg = {
        "configurable": {"thread_id": f"run-{int(time.time())}"},
        "recursion_limit": agent_recursion_limit,
    }
    
    # ==================== 9. 执行 Agent（流式输出）====================
    final_event = None
    last_printed_count = 0
    
    print("🔄 开始流式执行...\n")
    
    for event in agent.stream(
        {"messages": [{"role": "user", "content": test_question}]},
        stream_mode="values",
        config=cfg,
    ):
        messages = event.get("messages", [])
        
        # 打印所有新增的消息
        for i in range(last_printed_count, len(messages)):
            msg = messages[i]
            
            # 如果启用了中间件，跳过这两个工具的 pretty_print（中间件已经打印了精简版）
            if enable_middleware and hasattr(msg, 'name') and msg.name in ('get_all_tables_info', 'get_table_schema'):
                continue
            
            # 使用 pretty_print 显示格式化消息
            if hasattr(msg, 'pretty_print'):
                msg.pretty_print()
            else:
                # 降级到普通打印
                msg_type = getattr(msg, 'type', 'unknown')
                content = getattr(msg, 'content', str(msg))
                print(f"\n[{msg_type.upper()}] {content[:500]}{'...' if len(content) > 500 else ''}")
        
        last_printed_count = len(messages)
        final_event = event
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*80)
    print(f"✅ 完成 | 耗时: {elapsed:.1f}秒")
    print("="*80 + "\n")
    
    # ==================== 10. 训练决策（如果启用）====================
    if args.enable_training and final_event:
        print("\n" + "="*80)
        print("🤖 开始训练决策...")
        print("="*80 + "\n")
        
        # 创建后处理训练处理器（复用全局 LLM 实例）
        post_training_processor = PostTrainingProcessor()
        
        # 执行训练决策
        decision_result = post_training_processor.decide_and_add_to_training(
            question=test_question,
            conversation_history=final_event["messages"],
            vanna_client=vn
        )
        
        print(decision_result)


if __name__ == "__main__":
    main()
