#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 get_all_tables_info 方法的 Plan 过滤功能

测试场景：
1. 测试无问题参数（返回所有表）
2. 测试 Plan 过滤（问题与 topic 相似度 >= 0.75）
3. 测试关键字过滤（Plan 无结果时的备选方案）
"""

import sys
import os

# 强制重新加载模块
for module in list(sys.modules.keys()):
    if module.startswith('src.'):
        del sys.modules[module]

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "vanna"))

# 设置工作目录
os.chdir(os.path.join(PROJECT_ROOT, "vanna"))

# 导入 Vanna 客户端
from src.Improve.clients.vanna_client import create_vanna_client
from src.Improve.tools.database_tools import get_all_tables_info, _filter_tables_by_plan, _extract_keywords, _filter_tables_by_keywords
from src.Improve.shared import set_vanna_client

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def main():
    print("=" * 60)
    print("测试 get_all_tables_info 方法")
    print("=" * 60)

    # 创建 Vanna 客户端
    print("\n[1] 创建 Vanna 客户端...")
    vn = create_vanna_client(
        openai_api_key=os.getenv("API_KEY"),
        openai_base_url=os.getenv("BASE_URL"),
        model=os.getenv("LLM_MODEL"),
        milvus_uri=os.getenv("MILVUS_URI"),
        embedding_api_url=os.getenv("EMBEDDING_API_URL"),
    )
    vn.run_sql_is_set = True
    vn.static_documentation = ""

    # 导入共享上下文
    from src.Improve.shared import set_vanna_client
    set_vanna_client(vn)

    # 连接 MySQL 数据库
    print("\n[2] 连接 MySQL 数据库...")
    db_config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", 3306)),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", "csd123456"),
        "dbname": os.getenv("MYSQL_DATABASE", "ai_sales_data"),
    }
    vn.connect_to_mysql(**db_config)
    print(f"已连接到数据库: {db_config['dbname']}")

    # 获取当前数据库名
    db_query = "SELECT DATABASE()"
    db_result = vn.run_sql(db_query)
    db_name = db_result.iloc[0, 0]
    print(f"当前数据库: {db_name}")

    # 获取所有表（包含 TABLE_COMMENT 用于关键字过滤）
    tables_query = f"""
    SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = '{db_name}'
    """
    all_tables_df = vn.run_sql(tables_query)
    all_table_names = all_tables_df['TABLE_NAME'].tolist()
    print(f"\n数据库中共有 {len(all_table_names)} 个表:")
    for t in all_table_names:
        print(f"  - {t}")

    # ==================== 测试场景 1：无问题参数 ====================
    print("\n" + "=" * 60)
    print("测试场景 1: 无问题参数（返回所有表）")
    print("=" * 60)
    result = get_all_tables_info.invoke({})
    print(f"返回表数量: {result.count('表名:')}")
    print(result[:500] if len(result) > 500 else result)

    # ==================== 测试场景 2：Plan 过滤 ====================
    print("\n" + "=" * 60)
    print("测试场景 2: Plan 过滤")
    print("=" * 60)
    test_questions = [
        "查询产品的销售情况",
        "分析员工的绩效",
        "客户消费情况如何",
    ]

    for q in test_questions:
        print(f"\n--- 问题: {q} ---")

        # 测试 Plan 过滤
        filtered = _filter_tables_by_plan(vn, db_name, q, all_table_names)
        print(f"Plan 过滤结果: {filtered}")

        # 测试完整方法
        result = get_all_tables_info.invoke({"question": q})
        print(f"返回表数量: {result.count('表名:')}")
        print(f"返回内容前300字: {result[:300]}...")

    # ==================== 测试场景 3：关键字过滤 ====================
    print("\n" + "=" * 60)
    print("测试场景 3: 关键字过滤")
    print("=" * 60)

    # 使用一个 vannaplan 中不存在相关 topic 的问题
    test_question = "服务器状态监控"
    print(f"\n--- 问题: {test_question} ---")

    # 先测试 Plan 过滤
    filtered = _filter_tables_by_plan(vn, db_name, test_question, all_table_names)
    print(f"Plan 过滤结果: {filtered}")

    # 测试关键字过滤
    keywords = _extract_keywords(test_question)
    print(f"提取的关键词: {keywords}")
    filtered_df = _filter_tables_by_keywords(all_tables_df, keywords)
    print(f"关键字过滤结果: {filtered_df['TABLE_NAME'].tolist()}")

    # 测试完整方法
    result = get_all_tables_info.invoke({"question": test_question})
    print(f"返回表数量: {result.count('表名:')}")

    # ==================== 测试场景 4：边界情况 ====================
    print("\n" + "=" * 60)
    print("测试场景 4: 边界情况")
    print("=" * 60)

    # 空问题
    result = get_all_tables_info.invoke({"question": ""})
    print(f"\n空问题 - 返回表数量: {result.count('表名:')}")

    # 只有一个词的问题
    result = get_all_tables_info.invoke({"question": "产品"})
    print(f"单词问题 - 返回表数量: {result.count('表名:')}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
