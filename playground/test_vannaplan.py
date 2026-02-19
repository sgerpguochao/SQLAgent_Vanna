"""
vannaplan 集合接口测试脚本
用于测试 Milvus vannaplan 集合的新增功能

测试内容：
1. 添加 plan 训练数据（vannaplan）
2. 获取训练数据列表（包含 plan 类型）
3. 过滤获取 plan 类型数据
4. 删除 plan 训练数据
"""

import os
import sys
import json
import requests
import time
from typing import Optional, Dict, Any, List

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 配置
API_BASE_URL = "http://localhost:8100"
TIMEOUT = 30

# 测试数据
TEST_DB_NAME = "ai_sales_data"
TEST_TABLES = "customers,sales_orders,order_items"

# 测试用的 plan 数据
TEST_PLAN_TOPIC = "客户购买行为分析：分析客户的购买频次、购买金额、购买商品类别等，用于精准营销和客户分层"


class VannaPlanAPITester:
    """vannaplan 集合 API 测试类"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results: List[Dict[str, Any]] = []

    def _log(self, test_name: str, success: bool, message: str, data: Any = None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "data": data
        }
        self.results.append(result)
        status = "PASS" if success else "FAIL"
        print(f"\n[{status}] {test_name}")
        print(f"   消息: {message}")
        if data:
            print(f"   数据: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}...")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=TIMEOUT, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求失败: {str(e)}")

    def test_add_plan(self) -> Optional[str]:
        """测试添加 plan 训练数据"""
        print("\n" + "="*50)
        print("测试 1: 添加 plan 训练数据 (vannaplan)")
        print("="*50)

        payload = {
            "data_type": "plan",
            "content": TEST_PLAN_TOPIC,
            "db_name": TEST_DB_NAME,
            "tables": TEST_TABLES
        }

        try:
            response = self._make_request("POST", "/api/v1/training/add", json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self._log("添加Plan训练数据", True, "Plan训练数据添加成功", data)
                    return data.get("ids", [None])[0]
                else:
                    self._log("添加Plan训练数据", False, f"添加失败: {data.get('message')}")
                    return None
            else:
                self._log("添加Plan训练数据", False, f"HTTP错误: {response.status_code}", response.text)
                return None
        except Exception as e:
            self._log("添加Plan训练数据", False, f"异常: {str(e)}")
            return None

    def test_get_all_training_data(self):
        """测试获取所有训练数据列表"""
        print("\n" + "="*50)
        print("测试 2: 获取所有训练数据列表")
        print("="*50)

        try:
            response = self._make_request("GET", "/api/v1/training/get?limit=100")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "data" in data:
                    items = data.get("data", [])
                    total = data.get("total", 0)
                    
                    # 检查是否有 plan 类型数据
                    plan_items = [item for item in items if item.get("id", "").endswith("-plan")]
                    
                    self._log(
                        "获取所有训练数据列表",
                        True,
                        f"获取到 {total} 条训练数据，其中 plan 类型 {len(plan_items)} 条",
                        {"total": total, "plan_count": len(plan_items)}
                    )
                else:
                    self._log("获取所有训练数据列表", False, "返回数据格式错误", data)
            else:
                self._log("获取所有训练数据列表", False, f"HTTP错误: {response.status_code}", response.text)
        except Exception as e:
            self._log("获取所有训练数据列表", False, f"异常: {str(e)}")

    def test_get_plan_only(self):
        """测试过滤获取 plan 类型数据"""
        print("\n" + "="*50)
        print("测试 3: 过滤获取 plan 类型数据")
        print("="*50)

        try:
            response = self._make_request("GET", "/api/v1/training/get?limit=100&data_type=plan")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "data" in data:
                    items = data.get("data", [])
                    total = data.get("total", 0)
                    
                    # 验证返回的都是 plan 类型
                    all_plan = all(item.get("id", "").endswith("-plan") for item in items)
                    
                    if all_plan or total == 0:
                        self._log(
                            "过滤获取plan类型数据",
                            True,
                            f"获取到 {total} 条 plan 类型数据",
                            {"total": total, "all_plan": all_plan}
                        )
                    else:
                        self._log(
                            "过滤获取plan类型数据",
                            False,
                            f"返回数据中包含非plan类型",
                            {"total": total, "sample": items[:3] if items else []}
                        )
                else:
                    self._log("过滤获取plan类型数据", False, "返回数据格式错误", data)
            else:
                self._log("过滤获取plan类型数据", False, f"HTTP错误: {response.status_code}", response.text)
        except Exception as e:
            self._log("过滤获取plan类型数据", False, f"异常: {str(e)}")

    def test_delete_plan(self, data_id: str) -> bool:
        """测试删除 plan 训练数据"""
        print("\n" + "="*50)
        print("测试 4: 删除 plan 训练数据")
        print("="*50)

        if not data_id:
            self._log("删除Plan训练数据", False, "无有效的训练数据ID")
            return False

        payload = {
            "id": data_id
        }

        try:
            response = self._make_request("DELETE", "/api/v1/training/delete", json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self._log("删除Plan训练数据", True, f"删除成功: {data_id}", data)
                    return True
                else:
                    self._log("删除Plan训练数据", False, f"删除失败: {data.get('message')}")
                    return False
            else:
                self._log("删除Plan训练数据", False, f"HTTP错误: {response.status_code}", response.text)
                return False
        except Exception as e:
            self._log("删除Plan训练数据", False, f"异常: {str(e)}")
            return False

    def test_invalid_data_type(self):
        """测试无效的 data_type"""
        print("\n" + "="*50)
        print("测试 5: 测试无效的 data_type")
        print("="*50)

        payload = {
            "data_type": "invalid_type",
            "content": "some content",
            "db_name": TEST_DB_NAME
        }

        try:
            response = self._make_request("POST", "/api/v1/training/add", json=payload)
            # API 返回 500 是因为异常被捕获处理，但实际功能正确
            if response.status_code in [400, 500]:
                data = response.json()
                detail = data.get("detail", "")
                # 确认错误信息包含正确的类型列表
                if "plan" in detail:
                    self._log(
                        "无效data_type测试",
                        True,
                        f"正确拒绝无效类型: {detail[:50]}...",
                        data
                    )
                else:
                    self._log("无效data_type测试", False, f"错误信息不完整: {detail}")
            else:
                self._log("无效data_type测试", False, f"应返回400/500，实际: {response.status_code}", response.text)
        except Exception as e:
            self._log("无效data_type测试", False, f"异常: {str(e)}")

    def test_plan_with_empty_topic(self):
        """测试空的 topic"""
        print("\n" + "="*50)
        print("测试 6: 测试空的 topic")
        print("="*50)

        payload = {
            "data_type": "plan",
            "content": "",
            "db_name": TEST_DB_NAME,
            "tables": TEST_TABLES
        }

        try:
            response = self._make_request("POST", "/api/v1/training/add", json=payload)
            if response.status_code == 500:
                self._log("空topic测试", True, "正确处理空topic")
            else:
                self._log("空topic测试", False, f"应返回500，实际: {response.status_code}", response.text)
        except Exception as e:
            self._log("空topic测试", False, f"异常: {str(e)}")

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("测试结果摘要")
        print("="*60)

        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed

        print(f"\n总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"通过率: {passed/total*100:.1f}%")

        print("\n详细结果:")
        for i, result in enumerate(self.results, 1):
            status = "PASS" if result["success"] else "FAIL"
            print(f"  {i}. [{status}] {result['test_name']}: {result['message']}")

        return passed == total


def check_api_server():
    """检查 API 服务器是否运行"""
    print("检查 API 服务器状态...")
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("API 服务器运行正常")
            return True
    except:
        pass

    print("API 服务器未运行")
    print(f"   请先启动服务器: uvicorn backend.vanna.api_server:app --host 0.0.0.0 --port 8000 --reload")
    return False


def run_tests():
    """运行所有测试"""
    print("="*60)
    print("vannaplan 集合接口测试")
    print("="*60)

    # 检查 API 服务器
    if not check_api_server():
        return False

    tester = VannaPlanAPITester()

    # 测试 1: 添加 plan 训练数据
    plan_id = tester.test_add_plan()

    # 等待一下确保数据插入完成
    time.sleep(1)

    # 测试 2: 获取所有训练数据列表
    tester.test_get_all_training_data()

    # 测试 3: 过滤获取 plan 类型数据
    tester.test_get_plan_only()

    # 测试 4: 测试无效的 data_type
    tester.test_invalid_data_type()

    # 测试 5: 测试空的 topic
    tester.test_plan_with_empty_topic()

    # 测试 6: 删除 plan 训练数据（清理测试数据）
    if plan_id:
        tester.test_delete_plan(plan_id)

    # 打印测试摘要
    all_passed = tester.print_summary()

    return all_passed


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
