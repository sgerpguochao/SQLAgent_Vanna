#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 get_table_schema 方法的 RAG 过滤功能

测试场景：
1. 测试 get_related_ddl（带 db_name 过滤、阈值 0.5）
2. 测试 get_related_documentation（带 db_name 过滤）
3. 测试 get_similar_question_sql（带 db_name 过滤）
4. 测试 _get_ddl_by_keywords（带 db_name 过滤）
5. 测试 _get_doc_by_keywords（带 db_name 过滤）
6. 测试完整的 get_table_schema 方法
"""

import sys
import os

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "vanna"))
os.chdir(os.path.join(PROJECT_ROOT, "vanna"))

# 导入 Vanna 客户端
from src.Improve.clients.vanna_client import create_vanna_client
from src.Improve.shared import set_vanna_client
from src.Improve.tools.rag_tools import get_table_schema

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def main():
    print("=" * 60)
    print("测试 get_table_schema 方法")
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

    # 设置 vanna 客户端
    set_vanna_client(vn)

    # 获取当前数据库名
    db_query = "SELECT DATABASE()"
    db_result = vn.run_sql(db_query)
    db_name = db_result.iloc[0, 0]
    print(f"当前数据库: {db_name}")

    # ==================== 测试 1: get_related_ddl ====================
    print("\n" + "=" * 60)
    print("测试 1: get_related_ddl (阈值 0.5, topk=5, db_name 过滤)")
    print("=" * 60)
    test_question = "查询产品的销售情况"
    result = vn.get_related_ddl(
        question=test_question,
        db_name=db_name,
        threshold=0.5,
        top_k=5
    )
    print(f"问题: {test_question}")
    print(f"返回 DDL 数量: {len(result)}")
    for i, ddl in enumerate(result, 1):
        print(f"  DDL {i}: {ddl[:100]}...")

    # ==================== 测试 2: get_related_documentation ====================
    print("\n" + "=" * 60)
    print("测试 2: get_related_documentation (topk=5, db_name 过滤)")
    print("=" * 60)
    result = vn.get_related_documentation(
        question=test_question,
        db_name=db_name,
        top_k=5
    )
    print(f"问题: {test_question}")
    print(f"返回文档数量: {len(result)}")
    for i, doc in enumerate(result, 1):
        print(f"  文档 {i}: {doc[:100]}...")

    # ==================== 测试 3: get_similar_question_sql ====================
    print("\n" + "=" * 60)
    print("测试 3: get_similar_question_sql (topk=3, db_name 过滤)")
    print("=" * 60)
    result = vn.get_similar_question_sql(
        question=test_question,
        db_name=db_name,
        top_k=3
    )
    print(f"问题: {test_question}")
    print(f"返回 SQL 数量: {len(result)}")
    for i, pair in enumerate(result, 1):
        print(f"  SQL {i}: {pair.get('question', '')[:50]}... -> {pair.get('sql', '')[:50]}...")

    # ==================== 测试 4: _get_ddl_by_keywords ====================
    print("\n" + "=" * 60)
    print("测试 4: _get_ddl_by_keywords (db_name 过滤)")
    print("=" * 60)
    keywords = ["产品", "订单"]
    result = vn._get_ddl_by_keywords(keywords, db_name=db_name, top_k=5)
    print(f"关键词: {keywords}")
    print(f"返回 DDL 数量: {len(result)}")
    for i, ddl in enumerate(result, 1):
        print(f"  DDL {i}: {ddl[:100]}...")

    # ==================== 测试 5: _get_doc_by_keywords ====================
    print("\n" + "=" * 60)
    print("测试 5: _get_doc_by_keywords (db_name 过滤)")
    print("=" * 60)
    result = vn._get_doc_by_keywords(keywords, db_name=db_name, top_k=5)
    print(f"关键词: {keywords}")
    print(f"返回文档数量: {len(result)}")
    for i, doc in enumerate(result, 1):
        print(f"  文档 {i}: {doc[:100]}...")

    # ==================== 测试 6: 完整 get_table_schema ====================
    print("\n" + "=" * 60)
    print("测试 6: 完整 get_table_schema 方法")
    print("=" * 60)
    test_questions = [
        "查询产品的销售情况",
        "分析员工的绩效",
        "客户的消费情况如何",
    ]

    for q in test_questions:
        print(f"\n--- 问题: {q} ---")
        result = get_table_schema.invoke({"question": q})
        # 只打印前 300 个字符
        print(f"结果: {result[:300]}...")
        print("-" * 40)

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
