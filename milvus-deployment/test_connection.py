#!/usr/bin/env python3
"""
Milvus 连接测试脚本
"""

from pymilvus import connections, utility

def test_milvus_connection():
    """测试 Milvus 连接"""

    print("正在连接 Milvus...")

    try:
        # 连接到 Milvus
        connections.connect(
            alias="default",
            host="localhost",
            port="19530"
        )

        print("Milvus 连接成功！")

        # 获取 Milvus 版本信息
        version = utility.get_server_version()
        print(f"Milvus 版本: {version}")

        # 列出所有集合
        collections = utility.list_collections()
        print(f"当前集合数量: {len(collections)}")

        if collections:
            print("集合列表:")
            for col in collections:
                print(f"  - {col}")
        else:
            print("暂无集合")

        return True

    except Exception as e:
        print(f"连接失败: {e}")
        return False

    finally:
        # 断开连接
        connections.disconnect("default")
        print("连接已断开")

if __name__ == "__main__":
    test_milvus_connection()
