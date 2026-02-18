---
description: "NL2SQL 项目服务启动规范"
alwaysApply: false
---

# NL2SQL 数据分析系统

## 项目架构

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

## 服务启动命令

### 一键启停（推荐）

```bash
# 启动所有服务
./start_all.sh

# 停止所有服务
./stop_all.sh
```

### 手动启动

**1. Jina Embedding 服务**
```bash
cd /home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/local_embedding
source /home/ubuntu/miniconda/etc/profile.d/conda.sh
conda activate jina_run
MODEL_DIR=./jina-embeddings-v4-vllm-retrieval python -m uvicorn app_jina_embedding_v4:app --host 0.0.0.0 --port 8898
```

**2. Milvus 服务**
```bash
cd /home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/milvus-deployment/milvus_server
./start_milvus.sh
```

**3. 后端服务**
```bash
cd /home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/backend/vanna
source /home/ubuntu/miniconda/etc/profile.d/conda.sh
conda activate nl2sqlagent
python api_server.py
```

**4. 前端服务**
```bash
cd /home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/frontend
node ./node_modules/vite/bin/vite.js --host 0.0.0.0 --port 3000
```

## 服务地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8100 |
| API 文档 | http://localhost:8100/docs |
| Jina Embedding | http://localhost:8898 |
| Milvus | http://localhost:19530 |
| Milvus 健康检查 | http://localhost:9091/healthz |

## 环境要求

- Python 3.13.5
- Node.js
- Docker & Docker Compose
- MySQL 8.0
- Conda (miniconda/anaconda)
