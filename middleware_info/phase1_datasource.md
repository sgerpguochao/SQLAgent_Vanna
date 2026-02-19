# 数据源管理模块 - 源码分析文档

## 一、模块概述

数据源管理模块是 NL2SQL 系统的第一层，负责管理数据库连接和表结构。该模块主要围绕 MySQL 数据库展开，包含以下核心功能：

- 数据库连接测试
- 数据库连接与表结构获取
- 表结构树形展示
- 数据源配置持久化

---

## 二、子功能模块详细分析

### 2.1 数据库连接测试

#### 功能说明
在正式连接数据库之前，先测试连接配置是否正确，避免无效连接占用资源。

#### 后端实现

**文件**: `backend/vanna/api_server.py`

**代码位置**: 第 721-757 行

```python
@app.post("/api/v1/database/test", response_model=DatabaseConnectionResponse)
async def test_database_connection(request: DatabaseConnectionRequest):
```

**核心逻辑**:
1. 使用 `pymysql.connect()` 尝试建立连接
2. 设置 5 秒超时时间 (`connect_timeout=5`)
3. 连接成功后立即关闭连接
4. 返回连接是否成功

**关键代码**:
```python
connection = pymysql.connect(
    host=request.host,
    port=int(request.port),
    user=request.username,
    password=request.password,
    database=request.database if request.database else None,
    connect_timeout=5
)
connection.close()
```

#### 前端实现

**文件**: `frontend/src/components/DataSourcePanel.tsx`

**代码位置**: 第 74-94 行

**核心函数**: `handleTestConnection`

```typescript
const handleTestConnection = async () => {
  const response = await api.testDatabaseConnection(dbConfig);
  setTestResult({
    success: response.success,
    message: response.message
  });
};
```

**API 封装**: `frontend/src/services/api.ts` 第 212-214 行

```typescript
async testDatabaseConnection(config: DatabaseConnectionConfig): Promise<DatabaseConnectionResponse> {
  const response = await apiClient.post('/api/v1/database/test', config);
  return response;
}
```

---

### 2.2 数据库连接与表结构获取

#### 功能说明
连接数据库并获取表结构信息，包括：
- 所有表名
- 每个表的列信息（列名、数据类型、是否可空、主键等）

#### 后端实现

**文件**: `backend/vanna/api_server.py`

**代码位置**: 第 759-861 行

**接口**: `POST /api/v1/database/connect`

**核心逻辑**:

1. **连接 MySQL 服务器**（不指定数据库）
2. **两种模式**:
   - **指定数据库**: 连接后获取表结构和列信息
   - **未指定数据库**: 返回所有数据库列表

3. **表结构获取**:
   ```python
   # 获取所有表
   cursor.execute("SHOW TABLES")
   
   # 获取每个表的列信息
   cursor.execute(f"DESCRIBE `{table_name}`")
   ```

4. **返回数据结构**:
   ```python
   table_info = {
       "name": table_name,
       "type": "table",
       "children": [
           {
               "name": col[0],        # 列名
               "type": "column",
               "dataType": col[1],    # 数据类型
               "nullable": col[2] == "YES",
               "key": col[3],         # 主键信息
               "default": col[4],
               "extra": col[5]
           }
       ]
   }
   ```

5. **更新 Vanna 客户端连接**:
   ```python
   vn.connect_to_mysql(
       host=request.host,
       dbname=request.database,
       user=request.username,
       password=request.password,
       port=int(request.port)
   )
   ```

#### 前端实现

**文件**: `frontend/src/components/DataSourcePanel.tsx`

**代码位置**: 第 96-147 行

**核心函数**: `handleConnectDatabase`

```typescript
const handleConnectDatabase = async () => {
  const response = await api.connectDatabase(dbConfig);
  
  if (response.success) {
    // 将表转换为数据源格式
    const newDataSources = response.tables.map((table) => ({
      name: table.name,
      table: table.name,
      rows: 0,
      columns: table.children || [],
      description: `表 ${table.name}`,
      source: 'mysql',
      children: table.children
    }));
    
    setDataSources(newDataSources);
    localStorage.setItem('dataSources', JSON.stringify(newDataSources));
  }
};
```

**API 封装**: `frontend/src/services/api.ts` 第 218-220 行

---

### 2.3 表结构树形展示

#### 功能说明
以树形结构展示数据库→表→列的层级关系，支持展开/折叠。

#### 前端实现

**文件**: `frontend/src/components/DataSourcePanel.tsx`

**核心数据结构**:

```typescript
interface TableNode {
  name: string;
  type: 'schema' | 'table' | 'column';
  children?: TableNode[];
  tableName?: string;
  metadata?: {
    fields?: number;
    rows?: number;
    sample?: string;
  };
}
```

**关键函数**:

1. **`convertToTableNodes`** (第 159-204 行): 将数据源转换为树形节点
2. **`renderTreeNode`** (第 211-310 行): 递归渲染树形节点
3. **`toggleNode`** (第 149-157 行): 处理展开/折叠

**树形结构**:
```
├── 数据库表 (schema)
│   ├── users (table)
│   │   ├── id (INT)
│   │   ├── username (VARCHAR)
│   │   └── email (VARCHAR)
│   └── orders (table)
│       ├── id (INT)
│       ├── user_id (INT)
│       └── amount (DECIMAL)
```

**交互功能**:
- 点击表节点：选中表并触发 `onTableSelect` 回调
- Hover 显示表详情（字段数、行数、示例字段）
- 搜索过滤表和列

---

### 2.4 数据源配置持久化

#### 功能说明
保存数据源配置到 localStorage，实现页面刷新后数据源不丢失。

#### 前端实现

**文件**: `frontend/src/components/DataSourcePanel.tsx`

**存储键**: `dataSources`

**加载逻辑** (第 53-69 行):
```typescript
const loadDataSources = async () => {
  const savedSources = localStorage.getItem('dataSources');
  if (savedSources) {
    setDataSources(JSON.parse(savedSources));
  } else {
    setDataSources([]);
  }
};
```

**保存逻辑** (第 121-122 行):
```typescript
localStorage.setItem('dataSources', JSON.stringify(newDataSources));
```

**注意**: 当前实现只保存了表结构信息，**未保存数据库连接配置**（host、port、username、password）。

---

## 三、数据类型定义

### 后端请求/响应模型

**文件**: `backend/vanna/api_server.py` 第 91-105 行

```python
class DatabaseConnectionRequest(BaseModel):
    host: str
    port: str = "3306"
    username: str
    password: str
    database: Optional[str] = None

class DatabaseConnectionResponse(BaseModel):
    success: bool
    message: str
    databases: Optional[List[str]] = None
    tables: Optional[List[Dict[str, Any]]] = None
```

### 前端类型定义

**文件**: `frontend/src/services/api.ts` 第 117-142 行

```typescript
export interface DatabaseConnectionConfig {
  host: string;
  port: string;
  username: string;
  password: string;
  database?: string;
}

export interface DatabaseConnectionResponse {
  success: boolean;
  message: string;
  databases?: string[];
  tables?: Array<{
    name: string;
    type: string;
    children?: Array<{
      name: string;
      type: string;
      dataType: string;
      nullable: boolean;
      key: string;
      default: any;
      extra: string;
    }>;
  }>;
}
```

---

## 四、现有代码流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           前端 (DataSourcePanel)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  用户点击"添加数据库" → 打开连接对话框                                   │
│           ↓                                                              │
│  用户填写配置 (host, port, username, password, database)               │
│           ↓                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 点击"测试连接"                                                    │   │
│  │   → api.testDatabaseConnection(config)                         │   │
│  │   → POST /api/v1/database/test                                 │   │
│  │   → pymysql.connect() 测试连接                                  │   │
│  │   ← 返回 success: true/false                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           ↓                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 点击"保存"                                                        │   │
│  │   → api.connectDatabase(config)                                 │   │
│  │   → POST /api/v1/database/connect                              │   │
│  │   → 获取表结构 + 更新 vn 客户端连接                             │   │
│  │   ← 返回 tables: [{name, children: [...]}]                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           ↓                                                              │
│  转换为 DataSource 对象数组                                             │
│           ↓                                                              │
│  保存到 localStorage                                                    │
│           ↓                                                              │
│  渲染树形结构                                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 五、增加数据源列表展示功能

### 5.1 功能需求分析

如果需要增加**数据源列表展示**功能（即保存多个数据库连接配置，并可以切换），需要考虑以下点：

#### 当前实现 vs 目标实现

| 功能 | 当前实现 | 目标实现 |
|------|---------|---------|
| 连接数量 | 单个（覆盖式） | 多个（列表） |
| 连接配置保存 | 仅表结构 | 连接配置 + 表结构 |
| 连接切换 | 不支持 | 支持切换不同数据源 |
| 持久化 | localStorage | localStorage（不变） |

### 5.2 需要修改的后端代码

#### 5.2.1 新增接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `GET /api/v1/datasources` | GET | 获取数据源列表 |
| `POST /api/v1/datasources` | POST | 添加数据源 |
| `DELETE /api/v1/datasources/{id}` | DELETE | 删除数据源 |
| `PUT /api/v1/datasources/{id}` | PUT | 更新数据源 |

#### 5.2.2 后端修改文件

**无需修改后端代码** - 直接复用现有的接口即可：
- `POST /api/v1/database/test` - 测试连接
- `POST /api/v1/database/connect` - 连接并获取表结构

### 5.3 需要修改的前端代码

#### 5.3.1 前端修改文件

| 文件 | 修改内容 |
|------|---------|
| `frontend/src/services/api.ts` | 新增数据源列表相关 API 方法 |
| `frontend/src/components/DataSourcePanel.tsx` | 改造为支持多数据源列表展示 |
| 或新增 `frontend/src/components/DataSourceList.tsx` | 独立的数据源列表组件 |

#### 5.3.2 前端新增 API

```typescript
// frontend/src/services/api.ts

// 获取数据源列表
async function getDataSources(): Promise<DataSource[]> {
  const response = await apiClient.get('/api/v1/datasources');
  return response.data;
}

// 添加数据源
async function addDataSource(config: DatabaseConnectionConfig & { name: string }): Promise<DataSource> {
  const response = await apiClient.post('/api/v1/datasources', config);
  return response.data;
}

// 删除数据源
async function deleteDataSource(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/datasources/${id}`);
}

// 切换数据源（连接并获取表结构）
async function switchDataSource(id: string): Promise<DatabaseConnectionResponse> {
  const response = await apiClient.post(`/api/v1/datasources/${id}/connect`);
  return response.data;
}
```

#### 5.3.3 前端组件改造思路

**方案 A: 改造现有 DataSourcePanel**

1. 顶部新增数据源下拉选择器
2. 右侧保留表结构树
3. 点击"+"改为保存当前配置到列表

**方案 B: 新增独立页面**

1. 数据源管理页面（列表展示）
2. 点击数据源 → 跳转主页面并加载该数据源

---

## 六、总结

### 模块现状

| 子功能 | 后端文件 | 前端文件 |
|--------|---------|---------|
| 数据库连接测试 | `api_server.py:721-757` | `DataSourcePanel.tsx:74-94` |
| 数据库连接与表结构获取 | `api_server.py:759-861` | `DataSourcePanel.tsx:96-147` |
| 表结构树形展示 | - | `DataSourcePanel.tsx:159-310` |
| 数据源配置持久化 | - | `DataSourcePanel.tsx:53-69, 121-122` |

### 增加数据源列表功能的工作量估算

| 模块 | 工作内容 | 预估工作量 |
|------|---------|-----------|
| 后端 | 无需修改（复用自己的接口） | 0 小时 |
| 前端 | API 封装 + 组件改造 | 2-3 小时 |
| 测试 | UI 测试 | 0.5 小时 |

---

## 七、附录：相关文件路径汇总

### 后端
- `backend/vanna/api_server.py` - 主 API 服务

### 前端
- `frontend/src/components/DataSourcePanel.tsx` - 数据源面板组件
- `frontend/src/services/api.ts` - API 封装
- `frontend/src/components/ui/` - UI 组件库
