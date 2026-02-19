# 训练数据管理模块 - 源码分析文档

## 一、模块概述

训练数据管理模块是 NL2SQL 系统的第二层，负责管理 RAG（检索增强生成）所需的训练数据。该模块的核心是将数据存储在 **Milvus 向量数据库** 中，提供高效的相似度检索能力。

训练数据分为三种类型：
- **SQL 示例** (vannasql)：问题-SQL 对，提供历史查询示例
- **DDL** (vannaddl)：表结构定义，提供表结构上下文
- **文档** (vannadoc)：业务文档说明，提供业务语义

---

## 二、子功能模块详细分析

### 2.1 添加训练数据

#### 功能说明
向系统添加训练数据，数据会存储到 Milvus 向量数据库的对应集合中，并自动生成向量嵌入。

#### 后端实现

**文件**: `backend/vanna/api_server.py`

**代码位置**: 第 579-622 行

```python
@app.post("/api/v1/training/add", response_model=TrainingDataResponse)
async def add_training_data(request: TrainingDataRequest):
```

**核心逻辑**:
```python
# api_server.py:596-612
if request.data_type == "sql":
    ids = [vn.add_question_sql(question=request.question, sql=request.content)]
elif request.data_type == "ddl":
    ids = vn.add_ddl(request.content)
elif request.data_type == "documentation":
    ids = vn.add_documentation(request.content)
```

#### Vanna 客户端实现

**文件**: `backend/vanna/src/Improve/clients/vanna_client.py`

| 方法 | 代码位置 | 说明 |
|------|---------|------|
| `add_documentation` | 第 120-168 行 | 添加文档到 vannadoc 集合 |
| `add_ddl` | 第 170-213 行 | 添加 DDL 到 vannaddl 集合 |
| `add_question_sql` | 调用基类 | 添加 SQL 示例到 vannasql 集合 |

#### Milvus 集合字段定义

**文件**: `backend/vanna/src/vanna/milvus/milvus_vector.py`

| 集合名 | 字段 | 说明 |
|--------|------|------|
| **vannasql** | `id` (VARCHAR, 主键) | 唯一标识 |
| | `text` (VARCHAR) | 问题文本 |
| | `sql` (VARCHAR) | SQL 语句 |
| | `vector` (FLOAT_VECTOR) | 向量嵌入 |
| **vannaddl** | `id` (VARCHAR, 主键) | 唯一标识 |
| | `ddl` (VARCHAR) | DDL 语句 |
| | `vector` (FLOAT_VECTOR) | 向量嵌入 |
| **vannadoc** | `id` (VARCHAR, 主键) | 唯一标识 |
| | `doc` (VARCHAR) | 文档内容 |
| | `vector` (FLOAT_VECTOR) | 向量嵌入 |

**集合创建代码位置** (`milvus_vector.py`):
- `vannasql`: 第 88-112 行 (`_create_sql_collection`)
- `vannaddl`: 第 114-145 行 (`_create_ddl_collection`)
- `vannadoc`: 第 146-169 行 (`_create_doc_collection`)

---

### 2.2 获取训练数据列表

#### 功能说明
获取已添加的所有训练数据，支持分页和类型过滤。

#### 后端实现

**文件**: `backend/vanna/api_server.py`

**代码位置**: 第 624-688 行

```python
@app.get("/api/v1/training/get")
async def get_training_data(
    limit: int = 100,
    offset: int = 0,
    data_type: Optional[str] = None
):
```

#### Milvus 查询实现

**文件**: `backend/vanna/src/vanna/milvus/milvus_vector.py`

**代码位置**: 第 210-255 行

```python
def get_training_data(self, **kwargs) -> pd.DataFrame:
    # 从三个集合查询并合并
    sql_data = self.milvus_client.query(collection_name="vannasql", ...)
    ddl_data = self.milvus_client.query(collection_name="vannaddl", ...)
    doc_data = self.milvus_client.query(collection_name="vannadoc", ...)
    
    # 合并为 DataFrame
    df = pd.concat([df_sql, df_ddl, df_doc])
    return df
```

---

### 2.3 删除训练数据

#### 功能说明
根据 ID 删除指定的训练数据，自动识别数据所属的集合。

#### 后端实现

**文件**: `backend/vanna/api_server.py`

**代码位置**: 第 690-719 行

```python
@app.delete("/api/v1/training/delete", response_model=DeleteTrainingDataResponse)
async def delete_training_data(request: DeleteTrainingDataRequest):
```

#### Vanna 客户端删除逻辑

**文件**: `backend/vanna/src/Improve/clients/vanna_client.py`

**代码位置**: 第 300-360 行

```python
def remove_training_data(self, id: str, **kwargs) -> bool:
    # 支持 -hash 后缀：遍历三个集合查找并删除
    if id.endswith("-hash"):
        for collection_name in ["vannasql", "vannaddl", "vannadoc"]:
            result = self.milvus_client.query(...)
            if result:
                self.milvus_client.delete(collection_name=collection_name, ids=[id])
                return True
    
    # 支持 -sql/-ddl/-doc 后缀：直接删除
    elif id.endswith("-sql"):
        self.milvus_client.delete(collection_name="vannasql", ids=[id])
    elif id.endswith("-ddl"):
        self.milvus_client.delete(collection_name="vannaddl", ids=[id])
    elif id.endswith("-doc"):
        self.milvus_client.delete(collection_name="vannadoc", ids=[id])
```

---

## 三、Milvus 集合字段详情

### 3.1 vannasql 集合

用于存储问题-SQL 对，是 RAG 检索的核心数据源。

```python
# milvus_vector.py:88-112
vannasql_schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
vannasql_schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
vannasql_schema.add_field(field_name="sql", datatype=DataType.VARCHAR, max_length=65535)
vannasql_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self._embedding_dim)
```

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR | 唯一标识，使用 UUID + "-sql" 后缀 |
| text | VARCHAR | 用户问题文本 |
| sql | VARCHAR | 对应的 SQL 查询语句 |
| vector | FLOAT_VECTOR | text 字段的向量嵌入 |

---

### 3.2 vannaddl 集合

用于存储 DDL 表结构定义。

```python
# milvus_vector.py:114-145
vannaddl_schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
vannaddl_schema.add_field(field_name="ddl", datatype=DataType.VARCHAR, max_length=65535)
vannaddl_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self._embedding_dim)
```

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR | 唯一标识，使用 UUID + "-ddl" 后缀 |
| ddl | VARCHAR | CREATE TABLE 语句 |
| vector | FLOAT_VECTOR | ddl 字段的向量嵌入 |

---

### 3.3 vannadoc 集合

用于存储业务文档说明。

```python
# milvus_vector.py:146-169
vannadoc_schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
vannadoc_schema.add_field(field_name="doc", datatype=DataType.VARCHAR, max_length=65535)
vannadoc_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self._embedding_dim)
```

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR | 唯一标识，使用 UUID + "-doc" 后缀 |
| doc | VARCHAR | 文档内容（表说明、字段说明等） |
| vector | FLOAT_VECTOR | doc 字段的向量嵌入 |

---

## 四、核心代码文件汇总

| 层级 | 文件 | 作用 |
|------|------|------|
| **后端 API** | `backend/vanna/api_server.py:579-719` | 提供 REST 接口 |
| **客户端封装** | `backend/vanna/src/Improve/clients/vanna_client.py` | 批量训练、删除逻辑 |
| **向量存储** | `backend/vanna/src/vanna/milvus/milvus_vector.py` | Milvus 集合管理 |
| **前端面板** | `frontend/src/components/TrainingDataPanel.tsx` | 训练数据管理 UI |
| **前端配置** | `frontend/src/config/index.ts:48-50` | API 端点定义 |

---

## 五、增加新集合或调整字段

### 5.1 功能需求分析

如果需要：
1. **增加新集合**：例如增加 `vannarule`（规则库）或 `vannaplan`（执行计划）
2. **调整现有字段**：例如给 vannasql 增加 `description` 字段

### 5.2 需要修改的后端代码

#### 5.2.1 修改 Milvus 集合定义

**文件**: `backend/vanna/src/vanna/milvus/milvus_vector.py`

**需要修改的位置**:
- 集合创建方法：`_create_sql_collection`、`_create_ddl_collection`、`_create_doc_collection`
- 插入数据时的字段映射
- 查询数据时的字段映射
- 删除数据时的集合选择逻辑

**示例：增加 vannarule 集合**

```python
# 1. 新增集合创建方法
def _create_rule_collection(self, name: str = "vannarule"):
    if not self.milvus_client.has_collection(collection_name=name):
        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=False,
        )
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
        schema.add_field(field_name="rule", datatype=DataType.VARCHAR, max_length=65535)  # 新增字段
        schema.add_field(field_name="description", datatype=DataType.VARCHAR, max_length=65535)  # 新增字段
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self._embedding_dim)
        
        index_params = self.milvus_client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type=self.metric_type,
        )
        self.milvus_client.create_collection(
            collection_name=name,
            schema=schema,
            index_params=index_params,
        )

# 2. 在 __init__ 中调用
def __init__(self, config=None):
    # ... 现有代码 ...
    self._create_rule_collection("vannarule")  # 新增
```

#### 5.2.2 修改 Vanna 客户端

**文件**: `backend/vanna/src/Improve/clients/vanna_client.py`

**需要修改的位置**:
- `add_documentation` 方法（参考）：添加新集合的插入逻辑
- `remove_training_data` 方法：添加新集合的删除逻辑

**示例：添加 add_rule 方法**

```python
def add_rule(self, rule: Union[str, List[str]], description: str = None, **kwargs) -> Union[str, List[str]]:
    """添加规则到 vannarule 集合"""
    is_single = isinstance(rule, str)
    rules = [rule] if is_single else rule
    
    rule_ids = [self._get_content_hash(r) for r in rules]
    exists_map = self._check_exists_by_ids("vannarule", rule_ids)
    
    to_insert = []
    for r, rule_id in zip(rules, rule_ids):
        if not exists_map.get(rule_id, False):
            to_insert.append((r, rule_id, description))
    
    if to_insert:
        texts = [r for r, _, _ in to_insert]
        embeddings = self.embedding_function.encode_documents(texts)
        
        insert_data = [
            {
                "id": rule_id,
                "rule": rule,
                "description embedding.tolist()                "vector":": desc or "",
 if hasattr(embedding, 'tolist') else embedding
            }
            for (rule, rule_id, desc), embedding in zip(to_insert, embeddings)
        ]
        self.milvus_client.insert(collection_name="vannarule", data=insert_data)
    
    return rule_ids[0] if is_single else rule_ids
```

#### 5.2.3 修改 API 接口

**文件**: `backend/vanna/api_server.py`

**需要修改的位置**:
- `TrainingDataRequest` 模型：添加新数据类型
- `add_training_data` 函数：添加新数据类型的处理分支

**示例：支持 rule 类型**

```python
# 1. 添加新类型
class TrainingDataRequest(BaseModel):
    data_type: str  # 新增 "rule" 类型
    content: Any
    question: Optional[str] = None
    description: Optional[str] = None  # 新增字段

# 2. 处理新类型
elif request.data_type == "rule":
    ids = [vn.add_rule(request.content, description=request.description)]
```

---

### 5.3 需要修改的前端代码

#### 5.3.1 修改前端类型定义

**文件**: `frontend/src/components/TrainingDataPanel.tsx`

**需要修改的位置**:
- `dataType` 类型定义
- `EXAMPLE_TEMPLATES` 示例模板
- 添加表单中的字段

```typescript
// 1. 添加新类型
const [dataType, setDataType] = useState<'documentation' | 'ddl' | 'sql' | 'rule'>('sql');

// 2. 添加新模板
const EXAMPLE_TEMPLATES = {
  // ... 现有模板 ...
  rule: `规则名称: 销售额计算规则
描述: 用于计算月度销售额
逻辑: SUM(price * quantity)`,
};
```

#### 5.3.2 修改 API 调用

**文件**: `frontend/src/services/api.ts` 或 `frontend/src/config/index.ts`

如果需要新接口，添加对应的 API 方法。

---

### 5.4 工作量估算

| 模块 | 修改内容 | 预估工作量 |
|------|---------|-----------|
| **Milvus 集合** | 新增集合创建方法、修改字段定义 | 1-2 小时 |
| **Vanna 客户端** | 新增 add/remove 方法 | 1-2 小时 |
| **API 接口** | 添加新数据类型处理 | 0.5-1 小时 |
| **前端** | 类型定义、模板、UI 调整 | 1-2 小时 |
| **测试** | 手动测试增删改查 | 1 小时 |

**总计**: 约 5-8 小时

---

## 六、总结

### 模块现状

| 子功能 | 后端文件 | 前端文件 |
|--------|---------|---------|
| 添加训练数据 | `api_server.py:579-622` | `TrainingDataPanel.tsx:88-129` |
| 获取训练数据 | `api_server.py:624-688` | `TrainingDataPanel.tsx:69-86` |
| 删除训练数据 | `api_server.py:690-719` | `TrainingDataPanel.tsx:131-165` |

### 增加新集合/调整字段的修改点

| 层级 | 文件 | 修改内容 |
|------|------|---------|
| 向量存储 | `milvus_vector.py` | 集合创建方法、字段定义 |
| 客户端 | `vanna_client.py` | add/remove 方法 |
| API | `api_server.py` | 请求模型、处理逻辑 |
| 前端 | `TrainingDataPanel.tsx` | 类型、模板、UI |

### 注意事项

1. **向量维度**：所有集合的 vector 字段维度必须一致（由 embedding 模型决定）
2. **ID 格式**：建议使用 `-sql`、`-ddl`、`-doc` 后缀区分集合，便于删除时识别
3. **向后兼容**：调整字段时不影响已有数据的查询
4. **集合重建**：如果需要修改已存在集合的字段，需要重建集合并迁移数据
