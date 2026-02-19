"""
Milvus 集合初始化脚本
用于重新创建 vannasql、vannaddl、vannadoc 三个集合（带新字段）
"""

import os
import sys

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, "vanna/src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from pymilvus import MilvusClient, DataType
from pymilvus.model import DefaultEmbeddingFunction

# 配置
MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
METRIC_TYPE = os.getenv("MILVUS_METRIC_TYPE", "COSINE").upper()

print(f"Connecting to Milvus: {MILVUS_URI}")
print(f"Metric type: {METRIC_TYPE}")

# 创建 embedding function 获取维度
print("Initializing embedding function...")
embedding_function = DefaultEmbeddingFunction()
test_embedding = embedding_function.encode_documents(["test"])[0]
embedding_dim = len(test_embedding)
print(f"Embedding dimension: {embedding_dim}")

# 创建 Milvus 客户端
milvus_client = MilvusClient(uri=MILVUS_URI)


def create_collections():
    """创建三个集合"""
    
    # 1. vannasql 集合
    if milvus_client.has_collection("vannasql"):
        print("Dropping existing collection: vannasql")
        milvus_client.drop_collection("vannasql")
    
    vannasql_schema = MilvusClient.create_schema(
        auto_id=False,
        enable_dynamic_field=False,
    )
    vannasql_schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
    vannasql_schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
    vannasql_schema.add_field(field_name="sql", datatype=DataType.VARCHAR, max_length=65535)
    vannasql_schema.add_field(field_name="db_name", datatype=DataType.VARCHAR, max_length=255)
    vannasql_schema.add_field(field_name="tables", datatype=DataType.VARCHAR, max_length=65535)
    vannasql_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=embedding_dim)

    vannasql_index_params = milvus_client.prepare_index_params()
    vannasql_index_params.add_index(
        field_name="vector",
        index_name="vector",
        index_type="AUTOINDEX",
        metric_type=METRIC_TYPE,
    )
    milvus_client.create_collection(
        collection_name="vannasql",
        schema=vannasql_schema,
        index_params=vannasql_index_params,
        consistency_level="Strong"
    )
    print("✅ Created collection: vannasql")

    # 2. vannaddl 集合
    if milvus_client.has_collection("vannaddl"):
        print("Dropping existing collection: vannaddl")
        milvus_client.drop_collection("vannaddl")
    
    vannaddl_schema = MilvusClient.create_schema(
        auto_id=False,
        enable_dynamic_field=False,
    )
    vannaddl_schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
    vannaddl_schema.add_field(field_name="ddl", datatype=DataType.VARCHAR, max_length=65535)
    vannaddl_schema.add_field(field_name="db_name", datatype=DataType.VARCHAR, max_length=255)
    vannaddl_schema.add_field(field_name="table_name", datatype=DataType.VARCHAR, max_length=255)
    vannaddl_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=embedding_dim)

    vannaddl_index_params = milvus_client.prepare_index_params()
    vannaddl_index_params.add_index(
        field_name="vector",
        index_name="vector",
        index_type="AUTOINDEX",
        metric_type=METRIC_TYPE,
    )
    milvus_client.create_collection(
        collection_name="vannaddl",
        schema=vannaddl_schema,
        index_params=vannaddl_index_params,
        consistency_level="Strong"
    )
    print("✅ Created collection: vannaddl")

    # 3. vannadoc 集合
    if milvus_client.has_collection("vannadoc"):
        print("Dropping existing collection: vannadoc")
        milvus_client.drop_collection("vannadoc")
    
    vannadoc_schema = MilvusClient.create_schema(
        auto_id=False,
        enable_dynamic_field=False,
    )
    vannadoc_schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
    vannadoc_schema.add_field(field_name="doc", datatype=DataType.VARCHAR, max_length=65535)
    vannadoc_schema.add_field(field_name="db_name", datatype=DataType.VARCHAR, max_length=255)
    vannadoc_schema.add_field(field_name="table_name", datatype=DataType.VARCHAR, max_length=255)
    vannadoc_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=embedding_dim)

    vannadoc_index_params = milvus_client.prepare_index_params()
    vannadoc_index_params.add_index(
        field_name="vector",
        index_name="vector",
        index_type="AUTOINDEX",
        metric_type=METRIC_TYPE,
    )
    milvus_client.create_collection(
        collection_name="vannadoc",
        schema=vannadoc_schema,
        index_params=vannadoc_index_params,
        consistency_level="Strong"
    )
    print("✅ Created collection: vannadoc")

    print("\n" + "="*50)
    print("✅ All collections created successfully!")
    print("="*50)


def verify_collections():
    """验证集合是否创建成功"""
    print("\n验证集合:")
    for name in ["vannasql", "vannaddl", "vannadoc"]:
        exists = milvus_client.has_collection(name)
        print(f"  - {name}: {'✅ exists' if exists else '❌ not found'}")
        
        if exists:
            info = milvus_client.describe_collection(name)
            fields = [f['name'] for f in info['fields']]
            print(f"    Fields: {fields}")


if __name__ == "__main__":
    create_collections()
    verify_collections()
