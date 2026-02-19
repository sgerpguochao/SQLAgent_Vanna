"""
通过 API 初始化 Milvus 集合
触发集合自动创建并验证
"""

import requests
import json

API_BASE_URL = "http://localhost:8100"

def init_collections_via_api():
    """通过添加训练数据触发集合创建"""
    
    print("="*60)
    print("通过 API 初始化 Milvus 集合")
    print("="*60)
    
    test_cases = [
        {
            "name": "添加 SQL 训练数据 (vannasql)",
            "payload": {
                "data_type": "sql",
                "question": "查询所有客户的姓名和城市",
                "content": "SELECT name, city FROM customers;",
                "db_name": "ai_sales_data",
                "tables": "customers"
            }
        },
        {
            "name": "添加 DDL 训练数据 (vannaddl)",
            "payload": {
                "data_type": "ddl",
                "content": "CREATE TABLE customers (id INT, name VARCHAR(50));",
                "db_name": "ai_sales_data",
                "table_name": "customers"
            }
        },
        {
            "name": "添加文档训练数据 (vannadoc)",
            "payload": {
                "data_type": "documentation",
                "content": "客户信息表，包含客户姓名和城市",
                "db_name": "ai_sales_data",
                "table_name": "customers"
            }
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n测试: {test['name']}")
        print(f"请求: {json.dumps(test['payload'], ensure_ascii=False)}")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/v1/training/add",
                json=test['payload'],
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"响应: {json.dumps(data, ensure_ascii=False)}")
                if data.get("success"):
                    print("成功")
                    results.append({"name": test['name'], "success": True, "data": data})
                else:
                    msg = data.get('message', 'unknown error')
                    print(f"失败: {msg}")
                    results.append({"name": test['name'], "success": False, "error": msg})
            else:
                err = f"HTTP {response.status_code}"
                print(err)
                print(f"响应: {response.text[:200]}")
                results.append({"name": test['name'], "success": False, "error": err})
        except Exception as e:
            print(f"异常: {str(e)}")
            results.append({"name": test['name'], "success": False, "error": str(e)})
    
    return results


def verify_collections():
    """验证集合"""
    print("\n" + "="*60)
    print("验证训练数据")
    print("="*60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/training/get?limit=100", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n获取到 {len(data)} 条训练数据")
            
            if len(data) > 0:
                print("\n数据结构示例:")
                print(json.dumps(data[0], indent=2, ensure_ascii=False))
                
                first_item = data[0]
                new_fields = []
                if "db_name" in first_item and first_item.get("db_name"):
                    new_fields.append("db_name")
                if "tables" in first_item and first_item.get("tables"):
                    new_fields.append("tables")
                if "table_name" in first_item and first_item.get("table_name"):
                    new_fields.append("table_name")
                
                print(f"\n新增字段: {new_fields if new_fields else '无'}")
                return True
            return False
        else:
            print(f"获取失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"异常: {str(e)}")
        return False


if __name__ == "__main__":
    results = init_collections_via_api()
    verify_collections()
    
    print("\n" + "="*60)
    print("初始化结果")
    print("="*60)
    
    success_count = sum(1 for r in results if r.get("success"))
    total_count = len(results)
    
    print(f"\n总测试数: {total_count}")
    print(f"成功: {success_count}")
    print(f"失败: {total_count - success_count}")
    
    for r in results:
        status = "OK" if r.get("success") else "FAIL"
        print(f"  [{status}] {r['name']}")
