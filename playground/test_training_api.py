"""
训练模块接口测试脚本
用于测试 Milvus 三个集合的新增字段功能

测试内容：
1. 添加 SQL 训练数据（vannasql）
2. 添加 DDL 训练数据（vannaddl）
3. 添加文档训练数据（vannadoc）
4. 获取训练数据列表
5. 删除训练数据
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
API_BASE_URL = "http://localhost:8000"
TIMEOUT = 30

# 测试数据
TEST_DB_NAME = "ai_sales_data"
TEST_TABLE_NAME = "customers"
TEST_TABLES = "customers,sales_orders"

# 测试用的 SQL 数据
TEST_SQL_QUESTION = "查询所有客户的姓名和城市"
TEST_SQL_CONTENT = "SELECT name, city FROM customers;"

# 测试用的 DDL 数据
TEST_DDL_CONTENT = """CREATE TABLE `customers` (
  `customer_id` varchar(10) NOT NULL COMMENT '客户编号',
  `name` varchar(30) NOT NULL COMMENT '客户姓名',
  `city` varchar(50) NOT NULL COMMENT '所在城市',
  PRIMARY KEY (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户信息表'"""

# 测试用的文档数据
TEST_DOC_CONTENT = """### 表: customers
说明: customers表，包含客户基本信息
字段:
  - customer_id (VARCHAR(10)): 主键，客户编号
  - name (VARCHAR(30)): 客户姓名
  - city (VARCHAR(50)): 所在城市"""


class TrainingAPITester:
    """训练模块 API 测试类"""

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
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} - {test_name}")
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

    def test_add_sql(self) -> Optional[str]:
        """测试添加 SQL 训练数据"""
        print("\n" + "="*50)
        print("测试 1: 添加 SQL 训练数据 (vannasql)")
        print("="*50)

        payload = {
            "data_type": "sql",
            "question": TEST_SQL_QUESTION,
            "content": TEST_SQL_CONTENT,
            "db_name": TEST_DB_NAME,
            "tables": TEST_TABLES
        }

        try:
            response = self._make_request("POST", "/api/v1/training/add", json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self._log("添加SQL训练数据", True, "SQL训练数据添加成功", data)
                    return data.get("ids", [None])[0]
                else:
                    self._log("添加SQL训练数据", False, f"添加失败: {data.get('message')}")
                    return None
            else:
                self._log("添加SQL训练数据", False, f"HTTP错误: {response.status_code}", response.text)
                return None
        except Exception as e:
            self._log("添加SQL训练数据", False, f"异常: {str(e)}")
            return None

    def test_add_ddl(self) -> Optional[str]:
        """测试添加 DDL 训练数据"""
        print("\n" + "="*50)
        print("测试 2: 添加 DDL 训练数据 (vannaddl)")
        print("="*50)

        payload = {
            "data_type": "ddl",
            "content": TEST_DDL_CONTENT,
            "db_name": TEST_DB_NAME,
            "table_name": TEST_TABLE_NAME
        }

        try:
            response = self._make_request("POST", "/api/v1/training/add", json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self._log("添加DDL训练数据", True, "DDL训练数据添加成功", data)
                    return data.get("ids", [None])[0]
                else:
                    self._log("添加DDL训练数据", False, f"添加失败: {data.get('message')}")
                    return None
            else:
                self._log("添加DDL训练数据", False, f"HTTP错误: {response.status_code}", response.text)
                return None
        except Exception as e:
            self._log("添加DDL训练数据", False, f"异常: {str(e)}")
            return None

    def test_add_doc(self) -> Optional[str]:
        """测试添加文档训练数据"""
        print("\n" + "="*50)
        print("测试 3: 添加文档训练数据 (vannadoc)")
        print("="*50)

        payload = {
            "data_type": "documentation",
            "content": TEST_DOC_CONTENT,
            "db_name": TEST_DB_NAME,
            "table_name": TEST_TABLE_NAME
        }

        try:
            response = self._make_request("POST", "/api/v1/training/add", json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self._log("添加文档训练数据", True, "文档训练数据添加成功", data)
                    return data.get("ids", [None])[0]
                else:
                    self._log("添加文档训练数据", False, f"添加失败: {data.get('message')}")
                    return None
            else:
                self._log("添加文档训练数据", False, f"HTTP错误: {response.status_code}", response.text)
                return None
        except Exception as e:
            self._log("添加文档训练数据", False, f"异常: {str(e)}")
            return None

    def test_get_training_data(self):
        """测试获取训练数据列表"""
        print("\n" + "="*50)
        print("测试 4: 获取训练数据列表")
        print("="*50)

        try:
            response = self._make_request("GET", "/api/v1/training/get?limit=100")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    # 检查返回的数据是否包含新增字段
                    has_new_fields = False
                    if len(data) > 0:
                        first_item = data[0]
                        has_new_fields = "db_name" in first_item or "tables" in first_item or "table_name" in first_item

                    self._log(
                        "获取训练数据列表",
                        True,
                        f"获取到 {len(data)} 条训练数据" + ("（包含新增字段）" if has_new_fields else "（不包含新增字段）"),
                        {"count": len(data), "has_new_fields": has_new_fields}
                    )
                else:
                    self._log("获取训练数据列表", False, "返回数据格式错误", data)
            else:
                self._log("获取训练数据列表", False, f"HTTP错误: {response.status_code}", response.text)
        except Exception as e:
            self._log("获取训练数据列表", False, f"异常: {str(e)}")

    def test_delete_training_data(self, data_id: str) -> bool:
        """测试删除训练数据"""
        print("\n" + "="*50)
        print("测试 5: 删除训练数据")
        print("="*50)

        if not data_id:
            self._log("删除训练数据", False, "无有效的训练数据ID")
            return False

        payload = {
            "id": data_id
        }

        try:
            response = self._make_request("DELETE", "/api/v1/training/delete", json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self._log("删除训练数据", True, f"删除成功: {data_id}", data)
                    return True
                else:
                    self._log("删除训练数据", False, f"删除失败: {data.get('message')}")
                    return False
            else:
                self._log("删除训练数据", False, f"HTTP错误: {response.status_code}", response.text)
                return False
        except Exception as e:
            self._log("删除训练数据", False, f"异常: {str(e)}")
            return False

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("测试结果摘要")
        print("="*60)

        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed

        print(f"\n总测试数: {total}")
        print(f"通过: {passed} ✅")
        print(f"失败: {failed} ❌")
        print(f"通过率: {passed/total*100:.1f}%")

        print("\n详细结果:")
        for i, result in enumerate(self.results, 1):
            status = "✅" if result["success"] else "❌"
            print(f"  {i}. {status} {result['test_name']}: {result['message']}")

        return passed == total


def check_api_server():
    """检查 API 服务器是否运行"""
    print("检查 API 服务器状态...")
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API 服务器运行正常")
            return True
    except:
        pass

    print("❌ API 服务器未运行")
    print(f"   请先启动服务器: uvicorn backend.vanna.api_server:app --host 0.0.0.0 --port 8000 --reload")
    return False


def run_tests():
    """运行所有测试"""
    print("="*60)
    print("NL2SQL 训练模块接口测试")
    print("="*60)

    # 检查 API 服务器
    if not check_api_server():
        return False

    tester = TrainingAPITester()

    # 测试 1: 添加 SQL 训练数据
    sql_id = tester.test_add_sql()

    # 等待一下确保数据插入完成
    time.sleep(1)

    # 测试 2: 添加 DDL 训练数据
    ddl_id = tester.test_add_ddl()

    time.sleep(1)

    # 测试 3: 添加文档训练数据
    doc_id = tester.test_add_doc()

    time.sleep(1)

    # 测试 4: 获取训练数据列表
    tester.test_get_training_data()

    # 测试 5: 删除训练数据（删除添加的测试数据）
    if sql_id:
        tester.test_delete_training_data(sql_id)
    if ddl_id:
        tester.test_delete_training_data(ddl_id)
    if doc_id:
        tester.test_delete_training_data(doc_id)

    # 打印测试摘要
    all_passed = tester.print_summary()

    return all_passed


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
