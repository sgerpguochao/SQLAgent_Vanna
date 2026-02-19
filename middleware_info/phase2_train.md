# 训练数据管理模块 - 源码分析文档

## 一、模块概述

训练数据管理模块是 NL2SQL 系统的第二层，负责管理 RAG（检索增强生成）所需的训练数据。该模块的核心是将数据存储在 **Milvus 向量数据库** 中，提供高效的相似度检索能力。

训练数据分为四种类型：
- **SQL 示例** (vannasql)：问题-SQL 对，提供历史查询示例
- **DDL** (vannaddl)：表结构定义，提供表结构上下文
- **文档** (vannadoc)：业务文档说明，提供业务语义
- **主题规划** (vannaplan)：业务分析主题，提供业务划分及关联表信息

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
elif request.data_type == "plan":
    ids = vn.add_plan(request.content)
```

#### Vanna 客户端实现

**文件**: `backend/vanna/src/Improve/clients/vanna_client.py`

| 方法 | 说明 |
|------|------|
| `add_documentation` | 添加文档到 vannadoc 集合 |
| `add_ddl` | 添加 DDL 到 vannaddl 集合 |
| `add_question_sql` | 添加 SQL 示例到 vannasql 集合 |
| `add_plan` | 添加主题规划到 vannaplan 集合 |

#### Milvus 集合字段定义

**文件**: `backend/vanna/src/vanna/milvus/milvus_vector.py`

| 集合名 | 字段 | 说明 |
|--------|------|------|
| **vannasql** | `id` (VARCHAR, 主键) | 唯一标识 |
| | `text` (VARCHAR) | 问题文本 |
| | `sql` (VARCHAR) | SQL 语句 |
| | `db_name` (VARCHAR) | 数据库名称（新增） |
| | `tables` (VARCHAR) | 涉及的数据表（新增） |
| | `vector` (FLOAT_VECTOR) | 向量嵌入 |
| **vannaddl** | `id` (VARCHAR, 主键) | 唯一标识 |
| | `ddl` (VARCHAR) | DDL 语句 |
| | `db_name` (VARCHAR) | 数据库名称（新增） |
| | `table_name` (VARCHAR) | 表名称（新增） |
| | `vector` (FLOAT_VECTOR) | 向量嵌入 |
| **vannadoc** | `id` (VARCHAR, 主键) | 唯一标识 |
| | `doc` (VARCHAR) | 文档内容 |
| | `db_name` (VARCHAR) | 数据库名称（新增） |
| | `table_name` (VARCHAR) | 表名称（新增） |
| | `vector` (FLOAT_VECTOR) | 向量嵌入 |
| **vannaplan** | `id` (VARCHAR, 主键) | 唯一标识 |
| | `topic` (VARCHAR) | 业务分析主题 |
| | `db_name` (VARCHAR) | 数据库名称 |
| | `tables` (VARCHAR) | 关联的数据表 |
| | `vector` (FLOAT_VECTOR) | 向量嵌入 |

---

### 2.2 获取训练数据列表

#### 功能说明
获取已添加的所有训练数据，支持分页和类型过滤。

#### 后端实现

**文件**: `backend/vanna/api_server.py`

**代码位置**: 第 669-731 行

```python
@app.get("/api/v1/training/get")
async def get_training_data(
    limit: int = 100,
    offset: int = 0,
    data_type: Optional[str] = None
):
```

#### 数据类型判断逻辑

**重要修复**：根据 ID 后缀判断数据类型，确保前后端数据一致

```python
def extract_data_type(row):
    id_value = str(row.get('id', ''))
    if id_value.endswith('-sql'):
        return 'sql'
    elif id_value.endswith('-ddl'):
        return 'ddl'
    elif id_value.endswith('-doc'):
        return 'documentation'
    elif id_value.endswith('-plan'):
        return 'plan'
    # 备用判断逻辑...
```

#### Milvus 查询实现

**文件**: `backend/vanna/src/vanna/milvus/milvus_vector.py`

从四个集合查询并合并：
- vannasql（SQL查询）
- vannaddl（DDL结构）
- vannadoc（文档）
- vannaplan（主题规划）

---

### 2.3 删除训练数据

#### 功能说明
根据 ID 删除指定的训练数据，自动识别数据所属的集合。

#### 后端实现

**文件**: `backend/vanna/api_server.py`

```python
@app.delete("/api/v1/training/delete", response_model=DeleteTrainingDataResponse)
async def delete_training_data(request: DeleteTrainingDataRequest):
```

#### Vanna 客户端删除逻辑

支持以下 ID 后缀：
- `-sql` → vannasql
- `-ddl` → vannaddl
- `-doc` → vannadoc
- `-plan` → vannaplan
- `-hash` → 遍历所有集合查找并删除

---

### 2.4 批量导入训练数据（新增）

#### 功能说明
从ZIP压缩包批量导入训练数据，支持一次性导入四种类型的训练数据。

#### 后端实现

**文件**: `backend/vanna/api_server.py`

**接口地址**: `POST /api/v1/training/import`

**请求参数 (multipart/form-data)**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | ZIP压缩包文件 |
| db_name | string | 是 | 数据库名称 |
| clear_before_import | boolean | 否 | 导入前是否清理现有数据，默认true |

**ZIP文件格式要求**:
- 必须包含四个jsonl文件：`ddl.jsonl`, `sql_parse.jsonl`, `doc.jsonl`, `plan.jsonl`
- 支持JSON数组格式和标准jsonl格式

**字段映射规则**:

| jsonl文件 | Milvus集合 | 字段映射 |
|-----------|-----------|---------|
| ddl.jsonl | vannaddl | db_name→db_name, table_name→table_name, ddl_doc→ddl |
| sql_parse.jsonl | vannasql | db_name→db_name, question→text, sql→sql, tables→tables |
| doc.jsonl | vannadoc | db_name→db_name, table_name→table_name, document→doc |
| plan.jsonl | vannaplan | db_name→db_name, topic→topic, tables→tables |

**响应参数**:

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否成功 |
| message | string | 消息 |
| import_summary | object | 导入摘要（各集合插入数量） |

**核心特性**:
1. 支持JSON数组格式和标准jsonl格式
2. 导入前按db_name清理现有数据（分页删除，支持大数据量）
3. 并行异步处理四个文件
4. 自动生成向量嵌入
5. 导入完成后自动清理临时文件

---

## 三、Milvus 集合字段详情

### 3.1 vannasql 集合

用于存储问题-SQL 对，是 RAG 检索的核心数据源。

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR | 唯一标识，使用 MD5哈希 + "-sql" 后缀 |
| text | VARCHAR | 用户问题文本 |
| sql | VARCHAR | 对应的 SQL 查询语句 |
| db_name | VARCHAR | 数据库名称（新增） |
| tables | VARCHAR | 涉及的数据表（逗号分隔，新增） |
| vector | FLOAT_VECTOR | text 字段的向量嵌入 |

---

### 3.2 vannaddl 集合

用于存储 DDL 表结构定义。

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR | 唯一标识，使用 MD5哈希 + "-ddl" 后缀 |
| ddl | VARCHAR | CREATE TABLE 语句 |
| db_name | VARCHAR | 数据库名称（新增） |
| table_name | VARCHAR | 表名称（新增） |
| vector | FLOAT_VECTOR | ddl 字段的向量嵌入 |

---

### 3.3 vannadoc 集合

用于存储业务文档说明。

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR | 唯一标识，使用 MD5哈希 + "-doc" 后缀 |
| doc | VARCHAR | 文档内容（表说明、字段说明等） |
| db_name | VARCHAR | 数据库名称（新增） |
| table_name | VARCHAR | 表名称（新增） |
| vector | FLOAT_VECTOR | doc 字段的向量嵌入 |

---

### 3.4 vannaplan 集合

用于存储业务分析主题，提供业务划分及关联表信息。

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR | 唯一标识，使用 MD5哈希 + "-plan" 后缀 |
| topic | VARCHAR | 业务分析主题描述 |
| db_name | VARCHAR | 数据库名称 |
| tables | VARCHAR | 关联的数据表（逗号分隔） |
| vector | FLOAT_VECTOR | topic 字段的向量嵌入 |

---

## 四、核心代码文件汇总

| 层级 | 文件 | 作用 |
|------|------|------|
| **后端 API** | `backend/vanna/api_server.py` | 提供 REST 接口（添加/获取/删除/导入） |
| **客户端封装** | `backend/vanna/src/Improve/clients/vanna_client.py` | 批量训练、删除逻辑 |
| **向量存储** | `backend/vanna/src/vanna/milvus/milvus_vector.py` | Milvus 集合管理 |
| **前端面板** | `frontend/src/components/TrainingDataPanel.tsx` | 训练数据管理 UI |
| **前端配置** | `frontend/src/config/index.ts` | API 端点定义 |

---

## 五、前端实现

### 5.1 TrainingDataPanel 组件

**文件**: `frontend/src/components/TrainingDataPanel.tsx`

#### 功能列表
1. **添加训练数据** - 支持四种类型的单条添加
2. **获取训练数据** - 分页加载，支持过滤和搜索
3. **删除训练数据** - 带确认对话框
4. **批量导入** - ZIP压缩包导入（新增）

#### 批量导入功能（新增）

1. **导入按钮** - 紫色主题，位于刷新按钮旁边
2. **导入弹窗**:
   - 数据库选择（下拉框）
   - ZIP文件上传（支持拖拽）
   - 清理选项开关
   - 前端校验（文件格式、大小）
3. **导入过程**:
   - 全屏锁定遮罩
   - 进度提示
4. **导入结果**:
   - 显示各类型插入数量
   - 成功后5秒自动关闭弹窗

### 5.2 示例数据模板

```typescript
const EXAMPLE_TEMPLATES = {
  documentation: `表名: dim_product
描述: 存储所有电子产品的基本信息
字段:
- product_sk (BIGINT): 产品唯一标识
- product_name (VARCHAR): 产品名称
- brand (VARCHAR): 品牌名称`,
  ddl: `CREATE TABLE dim_product (
  product_sk BIGINT PRIMARY KEY,
  product_name VARCHAR(255)
) ENGINE=InnoDB;`,
  sql: `SELECT brand, SUM(quantity) as total 
FROM sales GROUP BY brand`,
  plan: `客户购买行为分析：分析客户的购买频次、购买金额等，用于精准营销`
};
```

---

## 六、批量导入数据文件格式

### 6.1 ddl.jsonl

```json
[
  {"db_name": "ai_sales_data", "table_name": "customers", "ddl_doc": "CREATE TABLE `customers` (...)"}
]
```

字段：db_name, table_name, ddl_doc

### 6.2 sql_parse.jsonl

```json
[
  {"db_name": "ai_sales_data", "question": "查询所有客户", "sql": "SELECT * FROM customers", "tables": ["customers"]}
]
```

字段：db_name, question, sql, tables

### 6.3 doc.jsonl

```json
[
  {"db_name": "ai_sales_data", "table_name": "customers", "document": "客户信息表..."}
]
```

字段：db_name, table_name, document

### 6.4 plan.jsonl

```json
[
  {"dialect": "mysql", "db_name": "ai_sales_data", "topic": "客户订单分析", "tables": ["customers", "orders"]}
]
```

字段：dialect, db_name, topic, tables

---

## 七、注意事项

1. **向量维度**：所有集合的 vector 字段维度必须一致（由 embedding 模型决定）
2. **ID 格式**：使用 MD5哈希 + 后缀（-sql/-ddl/-doc/-plan）区分集合
3. **数据一致性**：根据ID后缀判断data_type，确保前后端统计一致
4. **分页处理**：获取数据时使用分页加载，避免数据截断
5. **清理逻辑**：导入前清理使用分页查询，支持大数据量（limit最大16384）
6. **文件格式**：支持JSON数组格式和标准jsonl格式

---

## 八、测试验证结果

```
Milvus集合统计:
- vannasql: 98条
- vannaddl: 5条
- vannadoc: 6条
- vannaplan: 7条
总计: 116条

前端统计:
- sql: 98条
- ddl: 5条
- documentation: 6条
- plan: 7条
总计: 116条

✅ 数据一致
```

---

## 九、相关测试脚本

| 脚本 | 说明 |
|------|------|
| `backend/playgroud/test_training_api.py` | 训练数据管理API测试 |
| `backend/playgroud/test_vannaplan.py` | 主题规划功能测试 |
| `backend/playgroud/test_import_api.py` | 批量导入功能测试 |
| `backend/playgroud/init_via_api.py` | 初始化脚本 |
