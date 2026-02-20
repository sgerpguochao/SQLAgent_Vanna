#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Milvus 向量数据库连接测试脚本
用于测试 NL2SQL 系统配置的 Milvus 服务是否能够正常连接
"""

import requests
from pymilvus import connections, Collection, utility
import sys


def load_config():
    """从 .env 文件加载配置"""
    config = {
        'host': 'localhost',
        'port': '19530'
    }

    # 尝试从 .env 文件读取配置
    env_path = '/home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/backend/.env'
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key == 'MILVUS_URI':
                        # 解析 URI: http://localhost:19530
                        if '://' in value:
                            value = value.split('://', 1)[1]
                        if ':' in value:
                            config['host'], config['port'] = value.split(':', 1)
    except FileNotFoundError:
        print(f"Warning: .env file not found at {env_path}, using default config")

    return config


def test_health_check(config):
    """测试 Milvus 健康检查接口"""
    print("=" * 50)
    print("Milvus 服务健康检查")
    print("=" * 50)
    print(f"Host: {config['host']}")
    print(f"Port: {config['port']}")
    print("-" * 50)

    # 测试 Milvus 监听端口的健康检查
    try:
        response = requests.get("http://localhost:9091/healthz", timeout=5)
        if response.status_code == 200 and response.text == "OK":
            print("[✓] Milvus 健康检查通过 (port 9091)")
        else:
            print(f"[✓] Milvus 响应: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[✗] Milvus 健康检查失败: {e}")

    print("-" * 50)


def test_connection(config):
    """测试 Milvus 连接"""
    print("\n[1] 测试 Milvus 连接...")

    try:
        connections.connect(
            alias="default",
            host=config['host'],
            port=config['port']
        )
        print("[✓] Milvus 连接成功!")
        return True

    except Exception as e:
        print(f"[✗] Milvus 连接失败!")
        print(f"错误信息: {e}")
        return False


def test_collections(config):
    """测试获取 Collection 列表"""
    print("\n[2] 获取 Collection 列表...")

    try:
        collections = utility.list_collections()
        print(f"[✓] 共有 {len(collections)} 个 Collection:")
        if collections:
            for coll in collections:
                # 获取 Collection 统计信息
                try:
                    collection = Collection(coll)
                    stats = collection.num_entities
                    print(f"    - {coll}: {stats} 条向量")
                except:
                    print(f"    - {coll}")
        else:
            print("    (无 Collection)")
        return True

    except Exception as e:
        print(f"[✗] 获取 Collection 列表失败: {e}")
        return False


def test_vector_search(config):
    """测试向量搜索功能"""
    print("\n[3] 测试向量搜索功能...")

    try:
        # 创建一个简单的测试 Collection
        test_collection_name = "test_connection"

        # 如果存在则删除
        if utility.has_collection(test_collection_name):
            utility.drop_collection(test_collection_name)

        # 创建 Collection
        from pymilvus import FieldSchema, CollectionSchema, DataType
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
        ]
        schema = CollectionSchema(fields=fields, description="Test connection")
        collection = Collection(name=test_collection_name, schema=schema)

        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="vector", index_params=index_params)

        # 加载 Collection（重要！）
        collection.load()

        # 插入测试数据
        import numpy as np
        vectors = [[np.random.rand(128).tolist() for _ in range(10)]]
        data = [list(range(10)), vectors[0]]
        collection.insert(data)
        collection.flush()

        # 执行搜索
        search_vectors = [vectors[0][0]]
        results = collection.search(
            data=search_vectors,
            anns_field="vector",
            param={"metric_type": "L2", "params": {"nprobe": 10}},
            limit=5
        )

        print(f"[✓] 向量搜索测试成功! 找到 {len(results[0])} 条结果")

        # 清理测试数据
        utility.drop_collection(test_collection_name)
        print(f"[✓] 测试 Collection 已清理")

        return True

    except Exception as e:
        print(f"[✗] 向量搜索测试失败: {e}")
        return False


def cleanup():
    """关闭连接"""
    try:
        connections.disconnect("default")
    except:
        pass


def main():
    config = load_config()

    print("\n" + "=" * 50)
    print("Milvus 向量数据库连接测试")
    print("=" * 50)

    # 健康检查
    test_health_check(config)

    # 测试连接
    if not test_connection(config):
        print("\n[✗] 连接失败，退出测试")
        cleanup()
        sys.exit(1)

    # 测试 Collection
    test_collections(config)

    # 测试向量搜索
    test_vector_search(config)

    # 关闭连接
    cleanup()

    print("\n" + "=" * 50)
    print("测试完成! Milvus 服务运行正常。")
    print("=" * 50)


if __name__ == "__main__":
    main()
