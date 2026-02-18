# NL2SQL 数据分析系统部署文档

## 一、系统架构概述

SQL Agent 数据分析系统是一个基于 **大语言模型（LLM）** 和 **RAG（检索增强生成）** 技术的智能数据分析平台。系统的核心价值在于：将自然语言问题自动转换为准确的 SQL 查询，并对查询结果进行业务解读和可视化呈现。

### 技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| Agent 框架 | LangChain 1.0 | 工具调度和中间件机制 |
| 向量数据库 | Milvus | 训练数据的语义检索 |
| 嵌入模型 | Jina Embeddings v4 | 2048 维高质量多模态向量 |
| LLM | 通义千问 (Qwen-Flash) | OpenAI 兼容接口 |
| 前端 | React + Vite | 用户交互界面 |
| 后端 | FastAPI | API 服务 |

---

## 二、前后端本地部署启动

### 2.1 后端项目部署

**Step 1. 安装 Anaconda/Miniconda**

```bash
# 下载 Miniconda 安装脚本
wget https://repo.anaconda.com/archive/Anaconda3-latest-Linux-x86_64.sh

# 赋予执行权限
chmod +x Anaconda3-latest-Linux-x86_64.sh

# 运行安装脚本
bash Anaconda3-latest-Linux-x86_64.sh
# 按照提示完成安装，建议选择 yes 来初始化 conda
```

**Step 2. 验证 Conda 安装**

```bash
conda --version
# 输出示例: conda 24.x.x
```

**Step 3. 创建 Conda 虚拟环境并激活**

```bash
# 创建虚拟环境
conda create -n nl2sqlagent python=3.13.5 -y

# 激活虚拟环境
conda activate nl2sqlagent
```

**Step 4. 安装后端项目依赖**

```bash
# 进入后端目录
cd backend/vanna

# 安装所有依赖
pip install -r requirements.txt
```

**Step 5. 配置项目环境变量**

在 `backend/vanna/` 目录下创建 `.env` 文件：

```env
# OpenAI 兼容接口的 API Key
API_KEY=sk-afad3ac228864107912220d8076be356
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3-coder-plus

# LLM 生成参数（可选）
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=14000

# Agent 配置（可选）
AGENT_RECURSION_LIMIT=50

# ==================== Embedding 配置 ====================
# 嵌入模型提供商: jina | qwen | bge (默认: jina)
EMBEDDING_PROVIDER=jina
# 嵌入模型 API 地址
EMBEDDING_API_URL=http://localhost:8898/v1/embeddings

# ==================== Milvus 配置 ====================
# Milvus 服务地址
MILVUS_URI=http://localhost:19530
# 向量相似度度量方式: COSINE | L2 | IP
MILVUS_METRIC_TYPE=COSINE

# ==================== MySQL 配置 ====================
# MySQL 数据库主机
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=ai_sales_data
MYSQL_USER=root
MYSQL_PASSWORD=csd123456
```

**Step 6. 启动后端服务**

```bash
cd backend/vanna
python api_server.py
```

启动成功后显示：
```
Starting NL2SQL API service
Listening on: 0.0.0.0:8100
API docs: http://localhost:8100/docs
```

访问 `http://localhost:8100/docs` 验证后端服务接口文档。

### 2.2 后端服务检测与验证

**检查虚拟环境**

```bash
conda env list | grep nl2sqlagent
```

**检查依赖包**

```bash
conda activate nl2sqlagent
pip list | grep -E "(fastapi|langchain|milvus|pymilvus|openai|dashscope)"
```

**接口测试**

后端服务启动后，可通过以下方式测试：

```bash
# 测试 API 文档是否可访问
curl http://localhost:8100/docs

# 或使用 Python 测试
import requests

# 测试健康检查接口（如果有）
response = requests.get("http://localhost:8100/health")
print(response.json())
```

### 2.3 后端依赖中间件说明

后端服务启动前需确保以下中间件服务正常运行：

| 服务 | 默认端口 | 用途 |
|------|----------|------|
| Jina Embedding | 8898 | 文本向量化 |
| Milvus | 19530 | 向量存储与检索 |
| MySQL | 3306 | 结构化数据存储 |

**启动顺序建议：**
1. 先启动 Jina Embedding 服务
2. 再启动 Milvus 服务
3. 最后启动后端服务

---

### 2.2 前端项目部署

**前置条件：确保本地服务器已正确配置 Node.js 环境**

```bash
# 安装前端依赖
cd frontend
npm install

# 启动开发服务器
npm run dev
```

启动成功后输出类似：

```
VITE v6.3.7  ready in 250 ms

➜  Local:   http://localhost:3000/
➜  Network: http://192.168.110.131:3000/
➜  press h + enter to show help
```

在浏览器中打开 `http://localhost:3000` 即可访问系统。

---

## 三、Jina Embedding 服务安装部署

Jina Embedding 在本项目中作为独立的微服务，通过 FastAPI 框架对外提供 HTTP API 接口，负责将自然语言文本转换为高维稠密向量。

### 3.1 服务部署

**Step 1. 安装 Anaconda/Miniconda**

（如已安装，请跳过此步骤）

```bash
wget https://repo.anaconda.com/archive/Anaconda3-latest-Linux-x86_64.sh
chmod +x Anaconda3-latest-Linux-x86_64.sh
bash Anaconda3-latest-Linux-x86_64.sh
```

**Step 2. 验证 Conda 安装**

```bash
conda --version
```

**Step 3. 创建 Conda 虚拟环境并激活**

```bash
conda create -n jina_run python=3.13.5 -y
conda activate jina_run
```

**Step 4. 安装所需的 Python 包**

```bash
pip install fastapi==0.118.3 torch==2.8.0 transformers==4.56.2 Pillow==11.3.0 pydantic==2.10.3 uvicorn==0.38.0
pip install --no-cache-dir torchvision --extra-index-url https://download.pytorch.org/whl/cu121
```

**Step 5. 准备 Jina Embedding 模型**

模型文件路径：`local_embedding/jina-embeddings-v4-vllm-retrieval/`

**Step 6. 启动 Jina Embedding API**

```bash
cd local_embedding
CUDA_VISIBLE_DEVICES=0 \
MODEL_DIR=/home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/local_embedding/jina-embeddings-v4-vllm-retrieval \
python -m uvicorn app_jina_embedding_v4:app --host 0.0.0.0 --port 8898
```

参数说明：
- `CUDA_VISIBLE_DEVICES`: 指定使用的 GPU 编号（0, 1, 2...，多 GPU 用逗号分隔）
- `MODEL_DIR`: 模型文件目录路径
- `--host`: 监听地址
- `--port`: 服务端口

### 3.2 服务检测与验证

**检查虚拟环境**

```bash
conda env list | grep jina_run
```

**检查依赖包**

```bash
conda activate jina_run
pip list | grep -E "(fastapi|torch|transformers|uvicorn)"
```

**接口请求测试**

```python
import requests

url = "http://localhost:8898/v1/embeddings"

payload = {
    "inputs": [
        {"text": "人工智能正在改变世界"},
        {"text": "Machine learning is a subset of AI"}
    ],
    "normalize": True,
    "pooling": "mean"
}

response = requests.post(url, json=payload)
print(response.json())
```

成功响应将返回 2048 维的向量。

**使用 curl 测试**

```bash
curl -X POST http://localhost:8898/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"inputs": [{"text": "测试文本"}], "normalize": true, "pooling": "mean"}'
```

### 3.3 启动/停止脚本

项目提供了便捷的启动和停止脚本：

**启动脚本**

```bash
cd local_embedding
./start_jina.sh
```

启动成功后显示：
```
Jina Embedding service started successfully!
PID: xxxx
Log file: /path/to/jina_service.log
Service URL: http://0.0.0.0:8898
```

**停止脚本**

```bash
cd local_embedding
./stop_jina.sh
```

**脚本说明**

| 脚本 | 路径 | 功能 |
|------|------|------|
| start_jina.sh | local_embedding/start_jina.sh | 启动 Jina Embedding 服务 |
| stop_jina.sh | local_embedding/stop_jina.sh | 停止 Jina Embedding 服务 |

### 3.4 配置 .env 文件

在 `.env` 文件中添加：

```env
EMBEDDING_PROVIDER=jina
EMBEDDING_API_URL=http://localhost:8898/v1/embeddings
```

---

## 四、Milvus 服务配置

Milvus 是一个云原生的向量数据库，专为处理大规模向量数据而设计。

### 4.1 核心概念

| 概念 | 说明 | 类比 |
|------|------|------|
| Collection | 向量集合，类似于数据库中的表 | MySQL 的 Table |
| Field | 字段，包括向量字段和标量字段 | MySQL 的 Column |
| Entity | 实体，一条完整的数据记录 | MySQL 的 Row |
| Partition | 分区，用于数据分片和查询优化 | MySQL 的 Partition |
| Index | 索引，加速向量检索 | MySQL 的 Index |
| Metric Type | 距离度量方式（L2/IP/COSINE） | 相似度计算方法 |

### 4.2 部署步骤

**Step 1. 验证 Docker 环境**

```bash
docker --version
docker compose version
```

如未安装，可通过以下方式快速配置：

```bash
# 安装 Docker
sudo yum install -y docker

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

**Step 2. Milvus 一键启动**

```bash
cd milvus-deployment
./start.sh
```

**Step 3. 验证测试**

```bash
python test_connection.py
```

**Step 4. 配置 .env 文件**

在 `.env` 文件中添加：

```env
MILVUS_URI=http://192.168.110.131:19550
MILVUS_METRIC_TYPE=COSINE
```

---

## 六、部署架构图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   前端 React │ ──> │  FastAPI    │ ──> │   MySQL     │
│  (Port 3000) │     │ (Port 8100) │     │  数据库     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌───────────┐ ┌───────────┐ ┌───────────┐
       │ Jina      │ │  Milvus   │ │   LLM     │
       │ Embedding │ │  向量库   │ │  (通义)   │
       │ (Port8898)│ │(Port19530)│ │           │
       └───────────┘ └───────────┘ └───────────┘
```

---

## 六、附录：Node.js 安装

### Windows 安装

1. 从官网下载 LTS 版本的 .msi 安装包
2. 双击运行，勾选 "Add to PATH" 和 "Automatically install npm package manager"
3. 默认安装路径：`C:\Program Files\nodejs\`

### Ubuntu 安装

```bash
# 更新软件包索引
sudo apt update
sudo apt upgrade -y

# 安装 Node.js 和 npm
sudo apt install nodejs npm -y

# 验证安装
node -v
npm -v
```
