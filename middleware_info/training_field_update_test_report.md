# 训练模块字段新增测试报告

## 一、测试概述

### 1.1 测试目的

验证 Milvus 四个集合（vannasql、vannaddl、vannadoc、vannaplan）的功能是否正常。

### 1.2 新增字段说明

| 集合 | 新增字段 | 类型 | 说明 |
|------|---------|------|------|
| **vannasql** | db_name | VARCHAR(255) | 数据库名称 |
| | tables | VARCHAR(65535) | 涉及的数据表（逗号分隔） |
| **vannaddl** | db_name | VARCHAR(255) | 数据库名称 |
| | table_name | VARCHAR(255) | 表名称 |
| **vannadoc** | db_name | VARCHAR(255) | 数据库名称 |
| | table_name | VARCHAR(255) | 表名称 |
| **vannaplan** (新增) | db_name | VARCHAR(255) | 数据库名称 |
| | topic | VARCHAR(65535) | 业务分析主题描述 |
| | tables | VARCHAR(65535) | 关联的数据表（逗号分隔） |

---

## 二、代码修改记录

### 2.1 修改的文件

| 文件 | 修改内容 |
|------|---------|
| `backend/vanna/src/vanna/milvus/milvus_vector.py` | 集合初始化、添加方法、获取方法、删除方法 |
| `backend/vanna/src/Improve/clients/vanna_client.py` | 添加方法支持新参数、删除方法支持 |
| `backend/vanna/api_server.py` | API接口支持新字段和plan类型 |

### 2.2 详细修改

#### 2.2.1 milvus_vector.py

**集合初始化修改**：

```python
# vannasql 集合新增字段
vannasql_schema.add_field(field_name="db_name", datatype=DataType.VARCHAR, max_length=255)
vannasql_schema.add_field(field_name="tables", datatype=DataType.VARCHAR, max_length=65535)

# vannaddl 集合新增字段
vannaddl_schema.add_field(field_name="db_name", datatype=DataType.VARCHAR, max_length=255)
vannaddl_schema.add_field(field_name="table_name", datatype=DataType.VARCHAR, max_length=255)

# vannadoc 集合新增字段
vannadoc_schema.add_field(field_name="db_name", datatype=DataType.VARCHAR, max_length=255)
vannadoc_schema.add_field(field_name="table_name", datatype=DataType.VARCHAR, max_length=255)

# vannaplan 集合（新增）
vannaplan_schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
vannaplan_schema.add_field(field_name="topic", datatype=DataType.VARCHAR, max_length=65535)
vannaplan_schema.add_field(field_name="db_name", datatype=DataType.VARCHAR, max_length=255)
vannaplan_schema.add_field(field_name="tables", datatype=DataType.VARCHAR, max_length=65535)
vannaplan_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self._embedding_dim)
```

**添加方法修改**：

- `add_question_sql()`: 新增 `db_name` 和 `tables` 参数
- `add_ddl()`: 新增 `db_name` 和 `table_name` 参数
- `add_documentation()`: 新增 `db_name` 和 `table_name` 参数
- `add_plan()`: **新增** - 添加业务分析主题到 vannaplan 集合

```python
def add_plan(self, topic: str, **kwargs) -> str:
    """添加业务分析主题到 vannaplan集合"""
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
```

**获取方法修改**：

- `get_training_data()`: 返回新增字段 `db_name`、`tables`、`table_name`，新增 vannaplan 集合查询

**删除方法修改**：

- `remove_training_data()`: 新增 `-plan` 后缀支持，删除 vannaplan 集合数据

#### 2.2.2 vanna_client.py

**添加方法修改**：

- `add_documentation()`: 新增 `db_name` 和 `table_name` 参数
- `add_ddl()`: 新增 `db_name` 和 `table_name` 参数
- `add_plan()`: **新增** - 批量添加业务分析主题

```python
def add_plan(self, topic: Union[str, List[str]], **kwargs) -> Union[str, List[str]]:
    """添加业务分析主题到 vannaplan 集合"""
    is_single = isinstance(topic, str)
    topics = [topic] if is_single else topic

    db_name = kwargs.get("db_name", "")
    tables = kwargs.get("tables", "")

    plan_ids = [self._get_content_hash(t) for t in topics]
    # ... 批量插入逻辑
    return plan_ids[0] if is_single else plan_ids
```

**删除方法修改**：

- `remove_training_data()`: 新增 vannaplan 集合遍历和 `-plan` 后缀支持

```python
# -hash 后缀遍历时添加 vannaplan
for collection_name in ["vannasql", "vannaddl", "vannadoc", "vannaplan"]:

# 兼容原版后缀
elif id.endswith("-plan"):
    self.milvus_client.delete(collection_name="vannaplan", ids=[id])
```

**train 方法修改**：

```python
def train(
    self,
    question: str = None,
    sql: str = None,
    ddl: Union[str, List[str]] = None,
    documentation: Union[str, List[str]] = None,
    plan: TrainingPlan = None,
    db_name: str = "",           # 新增
    table_name: str = "",        # 新增
    tables: str = "",            # 新增
) -> Union[str, List[str], None]:
```

#### 2.2.3 api_server.py

**请求模型修改**：

```python
class TrainingDataRequest(BaseModel):
    data_type: str
    content: Any
    question: Optional[str] = None
    db_name: Optional[str] = Field("", description="数据库名称")
    table_name: Optional[str] = Field("", description="表名称，ddl/doc类型使用")
    tables: Optional[str] = Field("", description="涉及的数据表，sql/plan类型使用，逗号分隔")
```

**处理逻辑修改**：

在 `add_training_data` 函数中，新增 `plan` 类型处理分支：

```python
elif request.data_type == "plan":
    ids = vn.add_plan(
        request.content,
        db_name=request.db_name,
        tables=request.tables
    )
    if isinstance(ids, str):
        ids = [ids]
```

**获取接口修改**：

在 `get_training_data` 函数中，新增 `plan` 类型过滤支持：

```python
suffix_map = {
    'sql': '-sql',
    'ddl': '-ddl',
    'doc': '-doc',
    'documentation': '-doc',
    'plan': '-plan'  # 新增
}

---

## 三、接口文档

### 3.1 添加训练数据接口

**接口地址**: `POST /api/v1/training/add`

**请求参数 (TrainingDataRequest)**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| data_type | string | 是 | 数据类型：`sql`、`ddl`、`documentation`、`plan` |
| content | string/array | 是 | 训练数据内容 |
| question | string | 否 | 问题（仅 SQL 类型需要） |
| db_name | string | 否 | 数据库名称 |
| table_name | string | 否 | 表名称，ddl/doc类型使用 |
| tables | string | 否 | 涉及的数据表，sql/plan类型使用，逗号分隔 |

**响应参数 (TrainingDataResponse)**:

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否成功 |
| message | string | 消息 |
| ids | array | 插入的数据ID列表 |

**请求示例**:
```json
{
    "data_type": "sql",
    "question": "查询所有客户的姓名",
    "content": "SELECT name FROM customers;",
    "db_name": "ai_sales_data",
    "tables": "customers"
}
```

**响应示例**:
```json
{
    "success": true,
    "message": "Successfully added 1 sql training data",
    "ids": ["86593ee8-de5b-4cd2-bee5-8d35dfe8a6d4-sql"]
}
```

---

### 3.2 获取训练数据列表接口

**接口地址**: `GET /api/v1/training/get`

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | integer | 否 | 返回数量限制，默认100 |
| offset | integer | 否 | 偏移量，默认0 |
| data_type | string | 否 | 数据类型过滤：`sql`、`ddl`、`doc`、`plan` |

**响应参数**:

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否成功 |
| total | integer | 总记录数 |
| limit | integer | 返回数量限制 |
| offset | integer | 偏移量 |
| data | array | 训练数据列表 |

**data 数组中的字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 数据ID |
| question | string/null | 问题（SQL类型） |
| content | string | 数据内容 |
| db_name | string | 数据库名称（新增） |
| tables | string/null | 涉及的数据表（SQL类型新增） |
| table_name | string/null | 表名称（DDL/Doc类型新增） |
| data_type | string | 数据类型 |

**响应示例**:
```json
{
    "success": true,
    "total": 3,
    "limit": 10,
    "offset": 0,
    "data": [
        {
            "id": "86593ee8-de5b-4cd2-bee5-8d35dfe8a6d4-sql",
            "question": "test",
            "content": "SELECT 1;",
            "db_name": "test",
            "tables": "test",
            "table_name": null,
            "data_type": "sql"
        }
    ]
}
```

---

### 3.3 删除训练数据接口

**接口地址**: `DELETE /api/v1/training/delete`

**请求参数 (DeleteTrainingDataRequest)**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 训练数据ID |

**响应参数 (DeleteTrainingDataResponse)**:

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否成功 |
| message | string | 消息 |

**请求示例**:
```json
{
    "id": "86593ee8-de5b-4cd2-bee5-8d35dfe8a6d4-sql"
}
```

**响应示例**:
```json
{
    "success": true,
    "message": "Successfully deleted training data"
}
```

---

### 3.4 执行查询接口

**接口地址**: `POST /api/query`

**请求参数 (QueryRequest)**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sql | string | 否 | SQL查询语句 |
| query | string | 否 | 自然语言查询 |
| table_name | string | 否 | 表名 |
| file_id | string | 否 | 文件ID |
| limit | integer | 否 | 结果数量限制，默认100 |
| db_name | string | 否 | 数据库名称（新增，用于指定查询的数据库） |

**响应参数 (QueryResponse)**:

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否成功 |
| data | array | 查询结果数据 |
| columns | array | 列名列表 |
| sql | string | 执行的SQL语句 |
| answer | string | 自然语言答案 |
| total_rows | integer | 总行数 |
| returned_rows | integer | 返回行数 |

---

## 四、测试用例

### 4.1 测试用例列表

| 编号 | 测试用例 | 测试数据 | 预期结果 |
|------|---------|---------|---------|
| TC-001 | 添加 SQL 训练数据 | db_name="ai_sales_data", tables="customers,sales_orders" | 成功添加，返回ID |
| TC-002 | 添加 DDL 训练数据 | db_name="ai_sales_data", table_name="customers" | 成功添加，返回ID |
| TC-003 | 添加文档训练数据 | db_name="ai_sales_data", table_name="customers" | 成功添加，返回ID |
| TC-004 | 添加 Plan 训练数据 | db_name="ai_sales_data", tables="customers,sales_orders" | 成功添加，返回ID |
| TC-005 | 获取训练数据列表 | - | 返回包含新字段的数据 |
| TC-006 | 过滤获取 plan 类型数据 | data_type="plan" | 仅返回 plan 类型数据 |
| TC-007 | 删除 SQL 训练数据 | - | 成功删除 |
| TC-008 | 删除 Plan 训练数据 | - | 成功删除 |

### 4.2 测试脚本

测试脚本位置: `playground/test_training_api.py`

**使用方法**：

```bash
# 1. 启动 API 服务器
cd backend
source .env
uvicorn vanna.api_server:app --host 0.0.0.0 --port 8000

# 2. 运行测试脚本
cd playground
python test_training_api.py
```

---

## 五、测试结果

### 5.1 执行状态

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 代码修改 | ✅ 完成 | 三个集合的新增字段已完成 |
| 测试脚本 | ✅ 完成 | 包含7个测试用例 |
| 实际执行 | ✅ 完成 | 2026-02-19 执行通过 |

### 5.2 实际测试结果（vannaplan 集合）

**测试时间**: 2026-02-19
**测试脚本**: `playground/test_vannaplan.py`

**测试结果**:

| 编号 | 测试用例 | 测试数据 | 状态 | 返回ID |
|------|---------|---------|------|--------|
| TC-001 | 添加 Plan 训练数据 | topic="客户购买行为分析...", db_name="ai_sales_data", tables="customers,sales_orders,order_items" | ✅ 通过 | ca017e4a2d5a2323975b76cd4827c55c-hash |
| TC-002 | 获取所有训练数据列表 | - | ✅ 通过 | 返回4条记录，包含plan数据 |
| TC-003 | 过滤获取 plan 类型数据 | data_type="plan" | ✅ 通过 | 返回plan类型数据 |
| TC-004 | 测试无效的 data_type | data_type="invalid" | ✅ 通过 | 正确拒绝 |
| TC-005 | 测试空的 topic | topic="" | ✅ 通过 | 正确处理 |
| TC-006 | 删除 Plan 训练数据 | - | ✅ 通过 | 成功删除 |

**测试通过率**: 100% (6/6)

### 5.3 验证数据示例

**添加 Plan 请求**:
```json
{
    "data_type": "plan",
    "content": "客户购买行为分析：分析客户的购买频次、购买金额、购买商品类别等",
    "db_name": "ai_sales_data",
    "tables": "customers,sales_orders,order_items"
}
```

**添加 Plan 响应**:
```json
{
    "success": true,
    "message": "Successfully added 1 plan training data",
    "ids": ["ca017e4a2d5a2323975b76cd4827c55c-hash"]
}
```

**验证结论**: vannaplan 集合功能正常，新增字段 `db_name`、`tables` 均能正常存储和返回。

### 5.4 问题修复

测试过程中发现并修复的问题：

1. **NaN 值 JSON 序列化错误**: `get_training_data` 返回的 DataFrame 包含 NaN 值导致 JSON 序列化失败
   - 修复方案: 在 `api_server.py` 中将 pd.NA 转换为 None

2. **集合未自动创建**: 后端重启后需要先添加数据才能触发集合创建
   - 解决方案: 先通过 API 添加数据触发集合创建

---

## 六、注意事项

1. **新集合创建**: 如果 Milvus 中已存在旧版本的集合，需要删除后重新创建，或进行数据迁移
2. **向后兼容**: 新字段有默认值（空字符串），旧数据可以正常读取
3. **API 调用示例**:

```python
# 添加 SQL 训练数据
requests.post("http://localhost:8100/api/v1/training/add", json={
    "data_type": "sql",
    "question": "查询所有客户的姓名和城市",
    "content": "SELECT name, city FROM customers;",
    "db_name": "ai_sales_data",
    "tables": "customers,sales_orders"
})

# 添加 DDL 训练数据
requests.post("http://localhost:8100/api/v1/training/add", json={
    "data_type": "ddl",
    "content": "CREATE TABLE customers (...)",
    "db_name": "ai_sales_data",
    "table_name": "customers"
})

# 添加文档训练数据
requests.post("http://localhost:8100/api/v1/training/add", json={
    "data_type": "documentation",
    "content": "### 表: customers\n...",
    "db_name": "ai_sales_data",
    "table_name": "customers"
})

# 添加 Plan 训练数据（新增）
requests.post("http://localhost:8100/api/v1/training/add", json={
    "data_type": "plan",
    "content": "客户购买行为分析：分析客户的购买频次、购买金额、购买商品类别等",
    "db_name": "ai_sales_data",
    "tables": "customers,sales_orders,order_items"
})

# 获取所有训练数据
requests.get("http://localhost:8100/api/v1/training/get?limit=100")

# 仅获取 plan 类型数据（新增）
requests.get("http://localhost:8100/api/v1/training/get?limit=100&data_type=plan")

# 删除 Plan 训练数据（新增）
requests.delete("http://localhost:8100/api/v1/training/delete", json={
    "id": "ca017e4a2d5a2323975b76cd4827c55c-hash"
})
```

---

## 六、前端修改

### 6.1 修改的文件

| 文件 | 修改内容 |
|------|---------|
| `frontend/src/components/Dashboard.tsx` | 向 TrainingDataPanel 传递 selectedDatabase |
| `frontend/src/components/TrainingDataPanel.tsx` | 接收 selectedDatabase，添加表单字段，传递新字段到后端 |

### 6.2 前端表单字段

| 字段 | 类型 | 说明 |
|------|------|------|
| db_name | string | 数据库名称（下拉框选择，从localStorage读取数据源配置） |
| tables | string | 涉及的数据表（SQL类型使用） |
| table_name | string | 表名称（DDL/Doc类型使用） |

### 6.3 功能特点

- 数据库选择改为下拉框形式，无需先在左侧选择
- 自动从 localStorage 读取已配置的数据源列表
- 支持默认值：如果从 Dashboard 传入 selectedDatabase，会自动选中

### 6.4 前端测试验证

后端API测试结果：
- 添加 SQL 训练数据：✅ 成功，返回 ID
- 添加 DDL 训练数据：✅ 成功，返回 ID  
- 添加文档训练数据：✅ 成功，返回 ID
- 获取训练数据列表：✅ 成功，返回包含新字段的数据

返回数据示例：
```json
{
    "id": "cb7e39b1-c2ef-43fd-8ce8-07bad9b50e57-sql",
    "question": "测试问题",
    "content": "SELECT * FROM test;",
    "db_name": "ai_sales_data",
    "tables": "customers,orders",
    "table_name": null,
    "data_type": "sql"
}
```

---

## 七、总结

本次修改为 Milvus 三个集合新增了元数据字段，使训练数据能够关联数据库名称和表名称，便于：

1. **多数据库支持**: 通过 db_name 区分不同数据库的训练数据
2. **数据筛选**: 通过 tables/table_name 字段快速筛选特定表的数据
3. **数据管理**: 更方便地进行数据分类和检索

### 7.1 vannaplan 集合（新增）

vannaplan 集合用于存储业务分析主题，支持 RAG 检索。

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR | 唯一标识，使用 UUID + "-plan" 后缀 |
| topic | VARCHAR | 业务分析主题描述 |
| db_name | VARCHAR | 数据库名称 |
| tables | VARCHAR | 关联的数据表（逗号分隔） |
| vector | FLOAT_VECTOR | topic 字段的向量嵌入 |

**与 plan.jsonl 映射**:

| plan.jsonl 字段 | vannaplan 字段 |
|-----------------|----------------|
| db_name | db_name |
| topic | topic |
| tables | tables |

### 7.2 测试脚本

- 三个集合测试脚本: `playground/test_training_api.py`
- vannaplan 集合测试脚本: `playground/test_vannaplan.py`
- 初始化脚本: `playground/init_via_api.py`
