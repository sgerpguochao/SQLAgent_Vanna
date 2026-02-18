# SQL Agent 数据分析系统

基于 LangChain 1.0 和 RAG 技术的自然语言转 SQL 智能数据分析系统。

## 功能特性

- 🤖 **AI 驱动的 SQL 生成**：通过自然语言问题自动生成 SQL 查询
- 📊 **数据可视化**：自动生成图表展示查询结果
- 🎓 **RAG 训练数据管理**：支持 SQL 示例、DDL 结构、表文档的增删查改
- 💬 **智能对话**：支持多轮对话，理解上下文
- 🔍 **实时查询**：即时执行 SQL 并展示结果
- 📈 **数据分析报告**：自动生成数据洞察和分析建议

## 技术栈

### 后端
- **框架**: FastAPI
- **LLM**: OpenAI API (兼容格式)
- **向量数据库**: Milvus
- **嵌入模型**: Jina Embeddings
- **数据库**: MySQL
- **Agent**: LangChain 1.0 + LangGraph

### 前端
- **框架**: React + TypeScript
- **构建工具**: Vite
- **UI 组件**: shadcn/ui + Tailwind CSS
- **图表**: Chart.js
- **路由**: React Router

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Milvus 2.3+

### 后端配置

1. 进入后端目录：
```bash
cd backend/vanna
```

2. 创建并配置 `.env` 文件（参考 `.env.example`）

3. 安装依赖：
```bash
conda create -n vanna python=3.11
conda activate vanna
pip install -r requirements.txt
```

4. 启动后端服务：
```bash
python api_server.py
```

### 前端配置

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```

4. 访问 http://localhost:3000

## 项目结构

```
06_LangChainSqlAgent/
├── backend/
│   └── vanna/
│       ├── api_server.py          # FastAPI 服务入口
│       ├── react_agent.py         # Agent 主程序
│       └── src/
│           └── Improve/
│               ├── agent/         # Agent 核心逻辑
│               ├── clients/       # 客户端（Vanna, Embedding）
│               └── middleware/    # 日志和追踪中间件
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Dashboard.tsx      # 主面板
│       │   ├── ChatPanel.tsx      # AI 对话面板
│       │   ├── QueryPanel.tsx     # SQL 编辑器
│       │   ├── ResultsPanel.tsx   # 结果展示
│       │   └── TrainingDataPanel.tsx  # 训练数据管理
│       └── pages/
│           └── Home.tsx           # 首页
└── README.md
```

## 使用说明

### 1. 数据源配置

在左侧"数据源"标签中查看已连接的数据库表。

### 2. 训练数据管理

切换到"训练数据"标签：
- 添加 SQL 查询示例（问题 + SQL 语句）
- 添加 DDL 表结构定义
- 添加表文档说明

### 3. AI 对话查询

在右侧对话面板中：
1. 输入自然语言问题
2. AI 自动生成并执行 SQL
3. 查看查询结果和可视化图表
4. 获取数据分析报告

### 4. SQL 手动编辑

在中间 SQL 编辑器中：
- 手动编写或修改 SQL
- 点击执行按钮查询
- 查看结果表格

## 核心功能

### RAG 增强

系统使用 RAG（检索增强生成）技术：
- 从向量数据库检索相似的 SQL 示例
- 检索相关的表结构和文档
- 提升 SQL 生成的准确度

### Agent 工作流

1. 用户提问
2. 检索相关训练数据（RAG）
3. 理解问题意图
4. 生成 SQL 查询
5. 验证 SQL 语法
6. 执行查询
7. 分析结果
8. 生成可视化图表
9. 返回分析报告

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 开源协议

**非商业使用许可证**
版权所有 (c) 2026 sgerpguochao

本项目仅限个人学习、研究和教育目的使用，禁止用于任何商业用途。

详细内容请查看 [LICENSE](./LICENSE) 文件。

## 联系方式

- GitHub: https://github.com/sgerpguochao/SQLAgent_Vanna
