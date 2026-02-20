import uuid
from typing import List

import pandas as pd
from pymilvus import DataType, MilvusClient, model

from ..base import VannaBase
import logging
logger = logging.getLogger(__name__)

# Setting the URI as a local file, e.g.`./milvus.db`,
# is the most convenient method, as it automatically utilizes Milvus Lite
# to store all data in this file.
#
# If you have large scale of data such as more than a million docs, we
# recommend setting up a more performant Milvus server on docker or kubernetes.
# When using this setup, please use the server URI,
# e.g.`http://localhost:19530`, as your URI.

DEFAULT_MILVUS_URI = "./milvus.db"
# DEFAULT_MILVUS_URI = "http://localhost:19530"

MAX_LIMIT_SIZE = 10_000


class Milvus_VectorStore(VannaBase):
    """
    Vectorstore implementation using Milvus - https://milvus.io/docs/quickstart.md

    Args:
        - config (dict, optional): Dictionary of `Milvus_VectorStore config` options. Defaults to `None`.
            - milvus_client: A `pymilvus.MilvusClient` instance.
            - embedding_function:
                A `milvus_model.base.BaseEmbeddingFunction` instance. Defaults to `DefaultEmbeddingFunction()`.
                For more models, please refer to:
                https://milvus.io/docs/embeddings.md
            - metric_type: Vector similarity metric type. Options: 'L2', 'COSINE', 'IP'. Defaults to 'L2'.
    """
    def __init__(self, config=None):
        VannaBase.__init__(self, config=config)

        if "milvus_client" in config:
            self.milvus_client = config["milvus_client"]
        else:
            self.milvus_client = MilvusClient(uri=DEFAULT_MILVUS_URI)

        if "embedding_function" in config:
            self.embedding_function = config.get("embedding_function")
        else:
            self.embedding_function = model.DefaultEmbeddingFunction()
        
        # 优化: 支持配置 metric_type
        self.metric_type = config.get("metric_type", "L2").upper()
        
        # L2：计算两个向量之间的欧几里得距离：
        # 特点：考虑向量的长度和方向，距离越小，相似度越高
        # 在用量化特征（如“某用户购买次数”、“某属性计数”）时，数值的差异具有实际意义，就适合用 L2 距离
        
        # IP：计算两个向量的点积：
        # 特点：值越大，相似度越高，对向量长度敏感
        # 推荐系统中，用户向量可能代表用户的偏好强度，如果一个用户偏好多、另一用户偏好少，虽然方向可能类似，模大小不同也就是强度不同，用内积就能体现“强偏好 vs 弱偏好”的差别。

        # COSINE：计算两个向量夹角的余弦值
        # 特点：只关注方向，不关注长度，对向量长度不敏感
        # 语义检索、文档／文章相似度比较、文本聚类／主题分群等

        # 验证 metric_type 合法性
        valid_metrics = ["L2", "IP", "COSINE"]
        if self.metric_type not in valid_metrics:
            raise ValueError(f"Invalid metric_type: {self.metric_type}. Must be one of {valid_metrics}")
        
        logger.info(f"Vector similarity metric type: {self.metric_type}")
        
        self._embedding_dim = self.embedding_function.encode_documents(["foo"])[0].shape[0]
        self._create_collections()
        self.n_results = config.get("n_results", 10)

    def _create_collections(self):
        self._create_sql_collection("vannasql")
        self._create_ddl_collection("vannaddl")
        self._create_doc_collection("vannadoc")
        self._create_plan_collection("vannaplan")


    def generate_embedding(self, data: str, **kwargs) -> List[float]:
        return self.embedding_function.encode_documents(data).tolist()


    def _create_sql_collection(self, name: str):
        if not self.milvus_client.has_collection(collection_name=name):
            vannasql_schema = MilvusClient.create_schema(
                auto_id=False,
                enable_dynamic_field=False,
            )
            vannasql_schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
            vannasql_schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
            vannasql_schema.add_field(field_name="sql", datatype=DataType.VARCHAR, max_length=65535)
            vannasql_schema.add_field(field_name="db_name", datatype=DataType.VARCHAR, max_length=255)
            vannasql_schema.add_field(field_name="tables", datatype=DataType.VARCHAR, max_length=65535)
            vannasql_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self._embedding_dim)

            vannasql_index_params = self.milvus_client.prepare_index_params()
            vannasql_index_params.add_index(
                field_name="vector",
                index_name="vector",
                index_type="AUTOINDEX",
                metric_type=self.metric_type,  # 使用配置的 metric_type
            )
            self.milvus_client.create_collection(
                collection_name=name,
                schema=vannasql_schema,
                index_params=vannasql_index_params,
                consistency_level="Strong"
            )
            logger.info(f"Created collection: {name}（metric_type={self.metric_type}）")

    def _create_ddl_collection(self, name: str):
        if not self.milvus_client.has_collection(collection_name=name):
            vannaddl_schema = MilvusClient.create_schema(
                auto_id=False,
                enable_dynamic_field=False,
            )
            vannaddl_schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
            vannaddl_schema.add_field(field_name="ddl", datatype=DataType.VARCHAR, max_length=65535)
            vannaddl_schema.add_field(field_name="db_name", datatype=DataType.VARCHAR, max_length=255)
            vannaddl_schema.add_field(field_name="table_name", datatype=DataType.VARCHAR, max_length=255)
            vannaddl_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self._embedding_dim)

            vannaddl_index_params = self.milvus_client.prepare_index_params()
            vannaddl_index_params.add_index(
                field_name="vector",
                index_name="vector",
                index_type="AUTOINDEX",
                metric_type=self.metric_type,  # 使用配置的 metric_type
            )
            self.milvus_client.create_collection(
                collection_name=name,
                schema=vannaddl_schema,
                index_params=vannaddl_index_params,
                consistency_level="Strong"
            )
            logger.info(f"Created collection: {name}（metric_type={self.metric_type}）")

    def _create_doc_collection(self, name: str):
        if not self.milvus_client.has_collection(collection_name=name):
            vannadoc_schema = MilvusClient.create_schema(
                auto_id=False,
                enable_dynamic_field=False,
            )
            vannadoc_schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
            vannadoc_schema.add_field(field_name="doc", datatype=DataType.VARCHAR, max_length=65535)
            vannadoc_schema.add_field(field_name="db_name", datatype=DataType.VARCHAR, max_length=255)
            vannadoc_schema.add_field(field_name="table_name", datatype=DataType.VARCHAR, max_length=255)
            vannadoc_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self._embedding_dim)

            vannadoc_index_params = self.milvus_client.prepare_index_params()
            vannadoc_index_params.add_index(
                field_name="vector",
                index_name="vector",
                index_type="AUTOINDEX",
                metric_type=self.metric_type,  # 使用配置的 metric_type
            )
            self.milvus_client.create_collection(
                collection_name=name,
                schema=vannadoc_schema,
                index_params=vannadoc_index_params,
                consistency_level="Strong"
            )
            logger.info(f"Created collection: {name}（metric_type={self.metric_type}）")

    def _create_plan_collection(self, name: str):
        if not self.milvus_client.has_collection(collection_name=name):
            vannaplan_schema = MilvusClient.create_schema(
                auto_id=False,
                enable_dynamic_field=False,
            )
            vannaplan_schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
            vannaplan_schema.add_field(field_name="topic", datatype=DataType.VARCHAR, max_length=65535)
            vannaplan_schema.add_field(field_name="db_name", datatype=DataType.VARCHAR, max_length=255)
            vannaplan_schema.add_field(field_name="tables", datatype=DataType.VARCHAR, max_length=65535)
            vannaplan_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self._embedding_dim)

            vannaplan_index_params = self.milvus_client.prepare_index_params()
            vannaplan_index_params.add_index(
                field_name="vector",
                index_name="vector",
                index_type="AUTOINDEX",
                metric_type=self.metric_type,
            )
            self.milvus_client.create_collection(
                collection_name=name,
                schema=vannaplan_schema,
                index_params=vannaplan_index_params,
                consistency_level="Strong"
            )
            logger.info(f"Created collection: {name}（metric_type={self.metric_type}）")

    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        if len(question) == 0 or len(sql) == 0:
            raise Exception("pair of question and sql can not be null")
        _id = str(uuid.uuid4()) + "-sql"
        embedding = self.embedding_function.encode_documents([question])[0]
        db_name = kwargs.get("db_name", "")
        tables = kwargs.get("tables", "")
        self.milvus_client.insert(
            collection_name="vannasql",
            data={
                "id": _id,
                "text": question,
                "sql": sql,
                "db_name": db_name,
                "tables": tables,
                "vector": embedding
            }
        )
        return _id

    def add_ddl(self, ddl: str, **kwargs) -> str:
        if len(ddl) == 0:
            raise Exception("ddl can not be null")
        _id = str(uuid.uuid4()) + "-ddl"
        embedding = self.embedding_function.encode_documents([ddl])[0]
        db_name = kwargs.get("db_name", "")
        table_name = kwargs.get("table_name", "")
        self.milvus_client.insert(
            collection_name="vannaddl",
            data={
                "id": _id,
                "ddl": ddl,
                "db_name": db_name,
                "table_name": table_name,
                "vector": embedding
            }
        )
        return _id

    def add_documentation(self, documentation: str, **kwargs) -> str:
        if len(documentation) == 0:
            raise Exception("documentation can not be null")
        _id = str(uuid.uuid4()) + "-doc"
        embedding = self.embedding_function.encode_documents([documentation])[0]
        db_name = kwargs.get("db_name", "")
        table_name = kwargs.get("table_name", "")
        self.milvus_client.insert(
            collection_name="vannadoc",
            data={
                "id": _id,
                "doc": documentation,
                "db_name": db_name,
                "table_name": table_name,
                "vector": embedding
            }
        )
        return _id

    def add_plan(self, topic: str, **kwargs) -> str:
        """添加业务分析主题到 vannaplan 集合"""
        if len(topic) == 0:
            raise Exception("topic can not be null")
        _id = str(uuid.uuid4()) + "-plan"
        embedding = self.embedding_function.encode_documents([topic])[0]
        db_name = kwargs.get("db_name", "")
        tables = kwargs.get("tables", "")
        self.milvus_client.insert(
            collection_name="vannaplan",
            data={
                "id": _id,
                "topic": topic,
                "db_name": db_name,
                "tables": tables,
                "vector": embedding
            }
        )
        return _id

    def get_training_data(self, **kwargs) -> pd.DataFrame:
        sql_data = self.milvus_client.query(
            collection_name="vannasql",
            output_fields=["*"],
            limit=MAX_LIMIT_SIZE,
        )
        df = pd.DataFrame()
        df_sql = pd.DataFrame(
            {
                "id": [doc["id"] for doc in sql_data],
                "question": [doc["text"] for doc in sql_data],
                "content": [doc["sql"] for doc in sql_data],
                "db_name": [doc.get("db_name", "") for doc in sql_data],
                "tables": [doc.get("tables", "") for doc in sql_data],
            }
        )
        df = pd.concat([df, df_sql])

        ddl_data = self.milvus_client.query(
            collection_name="vannaddl",
            output_fields=["*"],
            limit=MAX_LIMIT_SIZE,
        )

        df_ddl = pd.DataFrame(
            {
                "id": [doc["id"] for doc in ddl_data],
                "question": [None for doc in ddl_data],
                "content": [doc["ddl"] for doc in ddl_data],
                "db_name": [doc.get("db_name", "") for doc in ddl_data],
                "table_name": [doc.get("table_name", "") for doc in ddl_data],
            }
        )
        df = pd.concat([df, df_ddl])

        doc_data = self.milvus_client.query(
            collection_name="vannadoc",
            output_fields=["*"],
            limit=MAX_LIMIT_SIZE,
        )

        df_doc = pd.DataFrame(
            {
                "id": [doc["id"] for doc in doc_data],
                "question": [None for doc in doc_data],
                "content": [doc["doc"] for doc in doc_data],
                "db_name": [doc.get("db_name", "") for doc in doc_data],
                "table_name": [doc.get("table_name", "") for doc in doc_data],
            }
        )
        df = pd.concat([df, df_doc])

        plan_data = self.milvus_client.query(
            collection_name="vannaplan",
            output_fields=["*"],
            limit=MAX_LIMIT_SIZE,
        )

        df_plan = pd.DataFrame(
            {
                "id": [doc["id"] for doc in plan_data],
                "question": [None for doc in plan_data],
                "content": [doc["topic"] for doc in plan_data],
                "db_name": [doc.get("db_name", "") for doc in plan_data],
                "tables": [doc.get("tables", "") for doc in plan_data],
            }
        )
        df = pd.concat([df, df_plan])
        return df

    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        search_params = {
            "metric_type": self.metric_type,  # 使用配置的 metric_type
            "params": {"nprobe": 128},
        }
        embeddings = self.embedding_function.encode_queries([question])
        res = self.milvus_client.search(
            collection_name="vannasql",
            anns_field="vector",
            data=embeddings,
            limit=self.n_results,
            output_fields=["text", "sql"],
            search_params=search_params
        )
        res = res[0]

        list_sql = []
        for doc in res:
            dict = {}
            dict["question"] = doc["entity"]["text"]
            dict["sql"] = doc["entity"]["sql"]
            list_sql.append(dict)
        return list_sql

    def get_related_ddl(self, question: str, **kwargs) -> list:
        """
        DDL 是 Data Definition Language（数据定义语言） 的缩写，用来定义和管理数据库对象的结构，比如数据库本身、表（table）、索引（index）、视图（view）等。
        通过 DDL 语句，可以创建、修改、删除数据库中的各种对象，从而实现对数据库的结构化管理。
        """
        search_params = {
            "metric_type": self.metric_type,  # 使用配置的 metric_type
            "params": {"nprobe": 128},
        }
        embeddings = self.embedding_function.encode_queries([question])
        res = self.milvus_client.search(
            collection_name="vannaddl",
            anns_field="vector",
            data=embeddings,
            limit=self.n_results,
            output_fields=["ddl"],
            search_params=search_params
        )
        res = res[0]

        list_ddl = []
        for doc in res:
            list_ddl.append(doc["entity"]["ddl"])
        return list_ddl

    def get_related_documentation(self, question: str, **kwargs) -> list:
        search_params = {
            "metric_type": self.metric_type,  # 使用配置的 metric_type
            "params": {"nprobe": 128},
        }
        embeddings = self.embedding_function.encode_queries([question])
        res = self.milvus_client.search(
            collection_name="vannadoc",
            anns_field="vector",
            data=embeddings,
            limit=self.n_results,
            output_fields=["doc"],
            search_params=search_params
        )
        res = res[0]

        list_doc = []
        for doc in res:
            list_doc.append(doc["entity"]["doc"])
        return list_doc

    def get_related_plan_tables(self, question: str, db_name: str, **kwargs) -> list:
        """
        从 vannaplan 集合中检索与问题相关的表名

        Args:
            question: 用户问题
            db_name: 数据库名称
            threshold: 相似度阈值，默认 0.75（高于此阈值认为相关）
            top_k: 返回数量，默认 5

        Returns:
            list: 相关的表名列表（去重，按大小写不敏感）
        """
        threshold = kwargs.get("threshold", 0.75)
        top_k = kwargs.get("top_k", 5)

        search_params = {
            "metric_type": self.metric_type,
            "params": {"nprobe": 128},
        }
        embeddings = self.embedding_function.encode_queries([question])

        # 先按 db_name 过滤，再进行向量搜索
        filter_expr = f'db_name == "{db_name}"'

        res = self.milvus_client.search(
            collection_name="vannaplan",
            anns_field="vector",
            data=embeddings,
            filter=filter_expr,
            limit=top_k,
            output_fields=["topic", "tables", "db_name"],
            search_params=search_params
        )

        res = res[0]

        # 用于存储去重后的表名（按小写去重，保持原始大小写）
        tables_set = {}

        for doc in res:
            # 获取相似度分数（distance 对于 COSINE 是 0-1，越接近 1 越相似）
            distance = doc.get("distance", 0)

            # 只返回达到阈值的结果
            if distance >= threshold:
                tables_str = doc["entity"].get("tables", "")
                if tables_str:
                    # 按逗号分割表名
                    table_list = [t.strip() for t in tables_str.split(",") if t.strip()]
                    for table in table_list:
                        # 按小写去重，保留第一个遇到的大小写形式
                        table_lower = table.lower()
                        if table_lower not in tables_set:
                            tables_set[table_lower] = table

        # 如果没有达到阈值的记录，返回空列表（让关键字过滤作为备选）
        if not tables_set:
            logger.info(f"没有达到阈值 {threshold} 的记录，将使用关键字过滤")

        # 返回去重后的表名列表（保持原始大小写）
        return list(tables_set.values())

    def remove_training_data(self, id: str, **kwargs) -> bool:
        if id.endswith("-sql"):
            self.milvus_client.delete(collection_name="vannasql", ids=[id])
            return True
        elif id.endswith("-ddl"):
            self.milvus_client.delete(collection_name="vannaddl", ids=[id])
            return True
        elif id.endswith("-doc"):
            self.milvus_client.delete(collection_name="vannadoc", ids=[id])
            return True
        elif id.endswith("-plan"):
            self.milvus_client.delete(collection_name="vannaplan", ids=[id])
            return True
        else:
            return False
