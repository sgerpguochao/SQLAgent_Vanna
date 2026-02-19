# ddl_mysql 数据文件 Schema 定义

本文档记录 `ddl_mysql` 文件夹下各 jsonl 文件的字段结构。

---

## 1. ddl.jsonl

**用途**: DDL 建表语句

```
columns: [db_name, table_name, ddl_doc]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| db_name | string | 数据库名称 |
| table_name | string | 表名称 |
| ddl_doc | string | CREATE TABLE DDL 语句 |

---

## 2. sql_parse.jsonl

**用途**: 自然语言问题-SQL 对

```
columns: [db_name, question, sql, tables]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| db_name | string | 数据库名称 |
| question | string | 自然语言问题 |
| sql | string | 对应的 SQL 语句 |
| tables | array[string] | 涉及的数据表 |

---

## 3. doc.jsonl

**用途**: 表结构文档说明

```
columns: [db_name, table_name, document]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| db_name | string | 数据库名称 |
| table_name | string | 表名称 |
| document | string | 表结构文档说明（包含字段、类型、注释） |

---

## 4. plan.jsonl

**用途**: 业务分析主题

```
columns: [dialect, db_name, topic, tables]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| dialect | string | 数据库方言（mysql） |
| db_name | string | 数据库名称 |
| topic | string | 业务分析主题描述 |
| tables | array[string] | 关联的数据表 |

---

## 数据内容汇总

### 数据库

- **db_name**: `ai_sales_data`

### 包含的表

| 表名 | 说明 |
|------|------|
| customers | 客户信息表 |
| employees | 员工基本信息表 |
| order_items | 订单明细表 |
| products | 产品目录表 |
| sales_orders | 销售订单主表 |
| sales_order_details | 订单详情表（宽表） |

### 记录数统计

| 文件 | 记录数 |
|------|--------|
| ddl.jsonl | 5 条 |
| sql_parse.jsonl | 81 条 |
| doc.jsonl | 6 条 |
| plan.jsonl | 5 条 |

---

## jsonl 字段与 Milvus 集合字段映射

### 现有 Milvus 集合字段定义（phase2_train.md）

| 集合 | 现有字段 |
|------|---------|
| **vannasql** | id, text, sql, vector |
| **vannaddl** | id, ddl, vector |
| **vannadoc** | id, doc, vector |

---

### 1. vannasql 集合 ↔ sql_parse.jsonl

| 现有字段 | sql_parse.jsonl 字段 | 映射说明 |
|----------|---------------------|---------|
| id | - | 需新增 |
| text | question | ✅ 已映射 |
| sql | sql | ✅ 已映射 |
| vector | - | 需新增（向量） |
| - | db_name | ❌ **需新增** |
| - | tables | ❌ **需新增** |

**新增字段**:
- `db_name` - 数据库名称
- `tables` - 涉及的数据表（可存为逗号分隔字符串）

---

### 2. vannaddl 集合 ↔ ddl.jsonl

| 现有字段 | ddl.jsonl 字段 | 映射说明 |
|----------|---------------|---------|
| id | - | 需新增 |
| ddl | ddl_doc | ✅ 已映射 |
| vector | - | 需新增（向量） |
| - | db_name | ❌ **需新增** |
| - | table_name | ❌ **需新增** |

**新增字段**:
- `db_name` - 数据库名称
- `table_name` - 表名称

---

### 3. vannadoc 集合 ↔ doc.jsonl

| 现有字段 | doc.jsonl 字段 | 映射说明 |
|----------|---------------|---------|
| id | - | 需新增 |
| doc | document | ✅ 已映射 |
| vector | - | 需新增（向量） |
| - | db_name | ❌ **需新增** |
| - | table_name | ❌ **需新增** |

**新增字段**:
- `db_name` - 数据库名称
- `table_name` - 表名称 |

---

## 总结：需要新增的字段

| 集合 | 新增字段 | 类型 | 说明 |
|------|---------|------|------|
| **vannasql** | db_name | VARCHAR | 数据库名称 |
| | tables | VARCHAR | 涉及的数据表（逗号分隔） |
| **vannaddl** | db_name | VARCHAR | 数据库名称 |
| | table_name | VARCHAR | 表名称 |
| **vannadoc** | db_name | VARCHAR | 数据库名称 |
| | table_name | VARCHAR | 表名称 |
| **vannaplan** (新增) | db_name | VARCHAR | 数据库名称 |
| | topic | VARCHAR | 业务分析主题描述 |
| | tables | VARCHAR | 关联的数据表（逗号分隔） |

---

## 字段映射图

```
┌─────────────────┬─────────────────────────────────────────────────┐
│  jsonl 文件      │              Milvus 集合字段映射                │
├─────────────────┼─────────────────────────────────────────────────┤
│ sql_parse.jsonl │                                                 │
│  - db_name    ──┼──▶ vannasql.db_name (新增)                    │
│  - question   ──┼──▶ vannasql.text                               │
│  - sql        ──┼──▶ vannasql.sql                                │
│  - tables     ──┼──▶ vannasql.tables (新增)                      │
├─────────────────┼─────────────────────────────────────────────────┤
│ ddl.jsonl       │                                                 │
│  - db_name    ──┼──▶ vannaddl.db_name (新增)                    │
│  - table_name ──┼──▶ vannaddl.table_name (新增)                  │
│  - ddl_doc    ──┼──▶ vannaddl.ddl                                │
├─────────────────┼─────────────────────────────────────────────────┤
│ doc.jsonl       │                                                 │
│  - db_name    ──┼──▶ vannadoc.db_name (新增)                    │
│  - table_name ──┼──▶ vannadoc.table_name (新增)                  │
│  - document   ──┼──▶ vannadoc.doc                                │
├─────────────────┼─────────────────────────────────────────────────┤
│ plan.jsonl      │                                                 │
│  - db_name    ──┼──▶ vannaplan.db_name (新增)                   │
│  - topic      ──┼──▶ vannaplan.topic                             │
│  - tables     ──┼──▶ vannaplan.tables (新增)                     │
└─────────────────┴─────────────────────────────────────────────────┘
```

---

## vannaplan 集合（新增）

### 用途
业务分析主题，用于存储业务分析场景的描述信息，支持 RAG 检索。

### 字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR | 唯一标识，使用 UUID + "-plan" 后缀 |
| topic | VARCHAR | 业务分析主题描述 |
| db_name | VARCHAR | 数据库名称 |
| tables | VARCHAR | 关联的数据表（逗号分隔） |
| vector | FLOAT_VECTOR | topic 字段的向量嵌入 |

### 与 plan.jsonl 映射

| plan.jsonl 字段 | vannaplan 字段 | 映射说明 |
|-----------------|----------------|---------|
| db_name | db_name | ✅ 已映射 |
| topic | topic | ✅ 已映射 |
| tables | tables | ✅ 已映射（array 转字符串） |
| dialect | - | 暂未存储 |

---

## 建议

1. **统一新增字段**: 三个集合都建议新增 `db_name` 字段，便于多数据库场景下的数据隔离和检索
2. **tables 字段处理**: vannasql 的 `tables` 字段可以存储为逗号分隔的字符串（如 `"customers,sales_orders"`）
3. **向后兼容**: 修改集合字段定义时，建议新建集合或做好数据迁移方案
