#!/usr/bin/env python3
"""
Milvus 完整功能测试脚本
"""

import numpy as np
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)

# 配置参数
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
COLLECTION_NAME = "test_collection"
DIM = 768  # 向量维度

def main():
    """主测试流程"""

    print("=" * 60)
    print("Milvus 完整功能测试")
    print("=" * 60)

    try:
        # 1. 连接 Milvus
        print(f"\n🔗 连接到 Milvus ({MILVUS_HOST}:{MILVUS_PORT})...")
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
        print("✅ 连接成功！")

        # 2. 删除旧集合（如果存在）
        if utility.has_collection(COLLECTION_NAME):
            print(f"\n⚠️  集合 '{COLLECTION_NAME}' 已存在，先删除...")
            utility.drop_collection(COLLECTION_NAME)

        # 3. 创建集合
        print(f"\n📦 创建集合: {COLLECTION_NAME}")
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM)
        ]
        schema = CollectionSchema(fields=fields, description="测试集合")
        collection = Collection(name=COLLECTION_NAME, schema=schema)
        print(f"✅ 集合 '{COLLECTION_NAME}' 创建成功！")

        # 4. 插入数据
        print(f"\n📝 插入 100 条测试数据...")
        texts = [f"这是第 {i} 条测试文本" for i in range(100)]
        embeddings = np.random.rand(100, DIM).tolist()
        entities = [texts, embeddings]
        insert_result = collection.insert(entities)
        print(f"✅ 成功插入 {len(insert_result.primary_keys)} 条数据")

        # 5. 创建索引
        print(f"\n🔍 为集合创建索引...")
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        print("✅ 索引创建成功！")

        # 6. 加载集合
        print(f"\n💾 加载集合到内存...")
        collection.load()
        print("✅ 集合已加载")

        # 7. 向量检索
        print(f"\n🔎 执行向量检索（Top 5）...")
        query_vectors = np.random.rand(2, DIM).tolist()
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = collection.search(
            data=query_vectors,
            anns_field="embedding",
            param=search_params,
            limit=5,
            output_fields=["text"]
        )

        for i, result in enumerate(results):
            print(f"\n查询 {i+1} 的结果:")
            for j, hit in enumerate(result):
                print(f"  Top {j+1}: ID={hit.id}, 距离={hit.distance:.4f}, 文本={hit.entity.get('text')}")

        print(f"\n✅ 检索完成！")

        # 8. 获取统计信息
        print(f"\n📊 集合统计信息:")
        collection.flush()
        stats = collection.num_entities
        print(f"  - 实体数量: {stats}")
        print(f"  - 集合名称: {collection.name}")

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        connections.disconnect("default")
        print("\n🔌 连接已断开")

if __name__ == "__main__":
    main()
