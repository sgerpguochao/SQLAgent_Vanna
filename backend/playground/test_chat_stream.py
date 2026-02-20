#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对话流程接口测试

测试 NL2SQL 系统的对话功能，包括：
1. 简单的数据分析查询
2. 复杂的跨表查询
3. 使用 Plan 过滤的查询
4. 边界情况测试
"""

import requests
import json
import time
import sys

# API 基础地址
BASE_URL = "http://localhost:8100"

# 测试问题列表
TEST_QUESTIONS = [
    {
        "name": "简单查询 - 产品列表",
        "question": "查询所有产品信息",
        "expected_tables": ["products"],  # 期望涉及的表
    },
    {
        "name": "简单查询 - 客户统计",
        "question": "统计客户的数量",
        "expected_tables": ["customers"],
    },
    {
        "name": "跨表查询 - 产品销售",
        "question": "查询产品的销售情况",
        "expected_tables": ["products", "order_items", "sales_orders"],  # 期望涉及的表
    },
    {
        "name": "复杂查询 - 员工绩效",
        "question": "分析员工的绩效情况",
        "expected_tables": ["employees"],
    },
    {
        "name": "复杂查询 - 客户消费",
        "question": "分析不同会员等级的客户的消费情况",
        "expected_tables": ["customers", "sales_orders"],
    },
    {
        "name": "复杂查询 - 订单详情",
        "question": "查询订单的详细信息包括客户信息和产品信息",
        "expected_tables": ["sales_orders", "customers", "order_items", "products"],
    },
]


def parse_sse_stream(response_text: str):
    """解析 SSE 流式响应"""
    events = []
    lines = response_text.strip().split('\n')
    
    for line in lines:
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])
                events.append(data)
            except json.JSONDecodeError:
                pass
    
    return events


def test_chat_stream(question: str, test_name: str):
    """测试单个对话问题"""
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"问题: {question}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # 发送请求
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/stream",
            json={"question": question, "stream": True},
            stream=True,
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
        
        # 收集响应内容
        full_response = ""
        step_count = 0
        answer = None
        has_data = False
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        
                        if data.get('type') == 'step':
                            step_count += 1
                            action = data.get('action', '')
                            status = data.get('status', '')
                            print(f"  Step {step_count}: [{status}] {action[:50]}...")
                        
                        elif data.get('type') == 'answer':
                            answer = data.get('content', '')
                            print(f"\n  答案: {answer[:200]}...")
                        
                        elif data.get('type') == 'data':
                            # 处理 data 字段，可能是列表或字典
                            query_data = data.get('data')
                            if isinstance(query_data, list):
                                print(f"  返回数据行数: {len(query_data)}")
                                has_data = True
                            elif isinstance(query_data, dict):
                                data_list = query_data.get('data', [])
                                print(f"  返回数据行数: {len(data_list)}")
                                has_data = True
                        
                        elif data.get('type') == 'done':
                            print(f"\n  ✅ 完成!")
                            
                    except json.JSONDecodeError:
                        pass
        
        elapsed_time = time.time() - start_time
        
        # 打印结果摘要
        print(f"\n  总耗时: {elapsed_time:.2f}秒")
        print(f"  步骤数: {step_count}")
        
        return {
            "success": True,
            "elapsed_time": elapsed_time,
            "step_count": step_count,
            "answer": answer,
            "has_data": has_data,
        }
        
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_health():
    """测试服务健康状态"""
    print("\n" + "="*60)
    print("测试 1: 服务健康检查")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=10)
        if response.status_code == 200:
            print("✅ 后端服务正常")
            return True
        else:
            print(f"❌ 后端服务异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到后端服务: {str(e)}")
        return False


def test_database_connection():
    """测试数据库连接"""
    print("\n" + "="*60)
    print("测试 2: 数据库连接")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/database/connect",
            json={
                "host": "localhost",
                "port": "3306",  # 端口是字符串类型
                "username": "root",
                "password": "csd123456",
                "database": "ai_sales_data"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 数据库连接成功")
            print(f"  数据库: {data.get('message', '')}")
            return True
        else:
            print(f"❌ 数据库连接失败: {response.status_code}")
            print(f"  错误信息: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False


def test_training_data():
    """测试训练数据"""
    print("\n" + "="*60)
    print("测试 3: 训练数据检查")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/training/get",
            params={"limit": 100},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            
            # 统计各类型数量
            type_counts = {}
            for item in items:
                data_type = item.get('data_type', 'unknown')
                type_counts[data_type] = type_counts.get(data_type, 0) + 1
            
            print(f"✅ 训练数据获取成功")
            print(f"  总数量: {len(items)}")
            for dtype, count in type_counts.items():
                print(f"    - {dtype}: {count}")
            return True
        else:
            print(f"❌ 训练数据获取失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False


def main():
    print("\n" + "="*60)
    print("NL2SQL 对话流程接口测试")
    print("="*60)
    
    # 1. 测试服务健康状态
    if not test_health():
        print("\n❌ 后端服务未运行，请先启动服务")
        sys.exit(1)
    
    # 2. 测试数据库连接
    if not test_database_connection():
        print("\n❌ 数据库连接失败，请检查配置")
        sys.exit(1)
    
    # 3. 测试训练数据
    if not test_training_data():
        print("\n⚠️ 训练数据可能未正确加载")
    
    # 4. 对话流程测试
    print("\n" + "="*60)
    print("测试 4: 对话流程测试")
    print("="*60)
    
    results = []
    for test_case in TEST_QUESTIONS:
        result = test_chat_stream(
            question=test_case["question"],
            test_name=test_case["name"]
        )
        results.append({
            "name": test_case["name"],
            "question": test_case["question"],
            "result": result
        })
    
    # 5. 输出测试结果汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    success_count = 0
    for r in results:
        status = "✅" if r["result"] and r["result"].get("success") else "❌"
        elapsed = r["result"].get("elapsed_time", 0) if r["result"] else 0
        print(f"{status} {r['name']} ({elapsed:.2f}秒)")
        
        if r["result"] and r["result"].get("success"):
            success_count += 1
    
    print(f"\n通过: {success_count}/{len(results)}")
    
    if success_count == len(results):
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️ 有 {len(results) - success_count} 个测试失败")
    
    return success_count == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
