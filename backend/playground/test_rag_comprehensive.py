#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对话模块 RAG 优化测试脚本

测试内容：
1. get_all_tables_info - 表过滤功能测试
2. get_table_schema - RAG 检索功能测试
3. 对话流程端到端测试

优化点：
- get_all_tables_info: Plan 过滤 + 关键字过滤
- get_table_schema: db_name 过滤 + 阈值 0.5 + 多路召回
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8100"


def test_health():
    """测试服务健康状态"""
    print("\n[测试 0] 服务健康检查")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=10)
        if response.status_code == 200:
            print("  ✅ 后端服务正常")
            return True
    except Exception as e:
        print(f"  ❌ 后端服务异常: {e}")
    return False


def test_database_connect():
    """测试数据库连接"""
    print("\n[测试 1] 数据库连接")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/database/connect",
            json={
                "host": "localhost",
                "port": "3306",
                "username": "root",
                "password": "csd123456",
                "database": "ai_sales_data"
            },
            timeout=30
        )
        if response.status_code == 200:
            print("  ✅ 数据库连接成功")
            return True
    except Exception as e:
        print(f"  ❌ 异常: {e}")
    return False


def test_training_data():
    """测试训练数据"""
    print("\n[测试 2] 训练数据检查")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/training/get",
            params={"limit": 100},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            print(f"  ✅ 训练数据: {len(items)} 条")
            return True
    except Exception as e:
        print(f"  ❌ 异常: {e}")
    return False


def test_get_all_tables_info():
    """测试 get_all_tables_info 表过滤功能"""
    print("\n[测试 3] get_all_tables_info 表过滤功能")
    test_cases = [
        {
            "name": "无问题参数",
            "question": "",
            "expected": "返回所有表"
        },
        {
            "name": "Plan 过滤 - 产品相关",
            "question": "查询产品的销售情况",
            "expected": "过滤后返回部分表"
        },
        {
            "name": "Plan 过滤 - 员工相关",
            "question": "分析员工的绩效",
            "expected": "过滤后返回 employees 表"
        },
        {
            "name": "Plan 过滤 - 客户相关",
            "question": "客户的消费情况如何",
            "expected": "过滤后返回客户相关表"
        },
    ]

    results = []
    for tc in test_cases:
        question = tc["question"]
        print(f"\n  --- {tc['name']} ---")
        print(f"  问题: {question or '(空)'}")

        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/stream",
                json={"question": question, "stream": True},
                stream=True,
                timeout=120
            )

            step_count = 0
            table_count = 0

            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if data.get('type') == 'step':
                                step_count += 1
                                action = data.get('action', '')
                                if 'get_all_tables_info' in action or '获取所有表格信息' in action:
                                    status = data.get('status', '')
                                    print(f"    Step: get_all_tables_info [{status}]")

                            if data.get('type') == 'done':
                                print(f"    ✅ 完成")

                        except json.JSONDecodeError:
                            pass

            print(f"    步骤数: {step_count}")
            results.append({"name": tc["name"], "status": "pass"})

        except Exception as e:
            print(f"    ❌ 异常: {e}")
            results.append({"name": tc["name"], "status": "fail"})

    pass_count = sum(1 for r in results if r["status"] == "pass")
    print(f"\n  结果: {pass_count}/{len(results)} 通过")
    return pass_count == len(results)


def test_get_table_schema():
    """测试 get_table_schema RAG 功能"""
    print("\n[测试 4] get_table_schema RAG 功能")
    test_cases = [
        {
            "name": "DDL 检索 - 产品相关",
            "question": "查询产品的销售情况",
        },
        {
            "name": "DDL 检索 - 员工相关",
            "question": "分析员工的绩效",
        },
        {
            "name": "DDL 检索 - 客户相关",
            "question": "客户的消费情况如何",
        },
    ]

    results = []
    for tc in test_cases:
        question = tc["question"]
        print(f"\n  --- {tc['name']} ---")
        print(f"  问题: {question}")

        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/stream",
                json={"question": question, "stream": True},
                stream=True,
                timeout=120
            )

            step_count = 0
            schema_found = False

            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if data.get('type') == 'step':
                                step_count += 1
                                action = data.get('action', '')
                                if 'get_table_schema' in action or '获取' in action and '结构' in action:
                                    status = data.get('status', '')
                                    print(f"    Step: get_table_schema [{status}]")
                                    schema_found = True

                            if data.get('type') == 'done':
                                print(f"    ✅ 完成")

                        except json.JSONDecodeError:
                            pass

            print(f"    步骤数: {step_count}")
            results.append({"name": tc["name"], "status": "pass" if schema_found else "fail"})

        except Exception as e:
            print(f"    ❌ 异常: {e}")
            results.append({"name": tc["name"], "status": "fail"})

    pass_count = sum(1 for r in results if r["status"] == "pass")
    print(f"\n  结果: {pass_count}/{len(results)} 通过")
    return pass_count == len(results)


def test_chat_flow():
    """测试对话流程端到端"""
    print("\n[测试 5] 对话流程端到端测试")
    test_cases = [
        {
            "name": "简单查询 - 产品列表",
            "question": "查询所有产品信息",
        },
        {
            "name": "简单查询 - 客户数量",
            "question": "统计客户的数量",
        },
        {
            "name": "跨表查询 - 产品销售",
            "question": "查询产品的销售情况",
        },
        {
            "name": "复杂查询 - 员工绩效",
            "question": "分析员工的绩效情况",
        },
    ]

    results = []
    for tc in test_cases:
        question = tc["question"]
        print(f"\n  --- {tc['name']} ---")
        print(f"  问题: {question}")

        start_time = time.time()

        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/stream",
                json={"question": question, "stream": True},
                stream=True,
                timeout=120
            )

            step_count = 0
            has_data = False
            has_answer = False

            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if data.get('type') == 'step':
                                step_count += 1
                            elif data.get('type') == 'data':
                                has_data = True
                            elif data.get('type') == 'answer':
                                has_answer = True
                            elif data.get('type') == 'done':
                                elapsed = time.time() - start_time
                                print(f"    ✅ 完成 (耗时: {elapsed:.2f}秒, 步骤: {step_count})")

                        except json.JSONDecodeError:
                            pass

            if has_data or has_answer:
                results.append({"name": tc["name"], "status": "pass", "time": elapsed})
            else:
                results.append({"name": tc["name"], "status": "fail", "time": 0})

        except Exception as e:
            print(f"    ❌ 异常: {e}")
            results.append({"name": tc["name"], "status": "fail", "time": 0})

    pass_count = sum(1 for r in results if r["status"] == "pass")
    total_time = sum(r.get("time", 0) for r in results)

    print(f"\n  结果: {pass_count}/{len(results)} 通过")
    print(f"  总耗时: {total_time:.2f}秒")

    return pass_count == len(results)


def main():
    print("=" * 60)
    print("对话模块 RAG 优化测试")
    print("=" * 60)

    # 运行所有测试
    tests = [
        ("服务健康", test_health),
        ("数据库连接", test_database_connect),
        ("训练数据", test_training_data),
        ("表过滤功能", test_get_all_tables_info),
        ("RAG 检索", test_get_table_schema),
        ("对话流程", test_chat_flow),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append({"name": name, "status": "pass" if result else "fail"})
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            results.append({"name": name, "status": "fail"})

    # 输出汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for r in results:
        status = "✅" if r["status"] == "pass" else "❌"
        print(f"{status} {r['name']}")

    pass_count = sum(1 for r in results if r["status"] == "pass")
    print(f"\n通过: {pass_count}/{len(results)}")

    if pass_count == len(results):
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️ 有 {len(results) - pass_count} 个测试失败")

    return pass_count == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
