#!/bin/bash

# NL2SQL 系统一键启动脚本
# 启动所有中间件和后端服务

set -e

PROJECT_DIR="/home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1"

echo "============================================"
echo "  NL2SQL 系统一键启动"
echo "============================================"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 函数：检查服务是否已运行
check_service() {
    local port=$1
    if lsof -i:$port > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 函数：等待服务启动
wait_for_service() {
    local port=$1
    local name=$2
    local max_attempts=30
    local attempt=1

    echo -n "等待 $name 启动..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:$port/healthz > /dev/null 2>&1 || curl -s http://localhost:$port/ > /dev/null 2>&1; then
            echo -e "${GREEN} OK${NC}"
            return 0
        fi
        sleep 1
        echo -n "."
        attempt=$((attempt + 1))
    done
    echo -e "${RED} 超时${NC}"
    return 1
}

echo ""
echo "============================================"
echo "Step 1: 启动 Jina Embedding 服务"
echo "============================================"
if check_service 8898; then
    echo -e "${YELLOW}Jina Embedding 服务已在运行 (port 8898)${NC}"
else
    echo "启动 Jina Embedding 服务..."
    cd $PROJECT_DIR/local_embedding
    source /home/ubuntu/miniconda/etc/profile.d/conda.sh
    conda activate jina_run

    nohup /home/ubuntu/miniconda/envs/jina_run/bin/python -m uvicorn app_jina_embedding_v4:app --host 0.0.0.0 --port 8898 > $PROJECT_DIR/local_embedding/jina_service.log 2>&1 &

    # 等待服务启动
    echo -n "等待 Jina Embedding 服务启动..."
    max_attempts=30
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8898/v1/embeddings -X POST -H "Content-Type: application/json" -d '{"inputs":[{"text":"test"}]}' 2>/dev/null | grep -q "200\|422"; then
            break
        fi
        sleep 1
        echo -n "."
        attempt=$((attempt + 1))
    done
    
    if check_service 8898; then
        echo -e " ${GREEN}OK${NC}"
        echo -e "${GREEN}Jina Embedding 服务启动成功 (port 8898)${NC}"
    else
        echo -e " ${RED}超时${NC}"
        echo -e "${RED}Jina Embedding 服务启动失败${NC}"
    fi
fi

echo ""
echo "============================================"
echo "Step 2: 启动 Milvus 服务"
echo "============================================"
if check_service 9091; then
    echo -e "${YELLOW}Milvus 服务已在运行 (port 9091)${NC}"
else
    echo "启动 Milvus 服务..."
    cd $PROJECT_DIR/milvus-deployment/milvus_server
    ./start_milvus.sh > /dev/null 2>&1 &
    
    # 等待 Milvus 健康检查通过
    echo -n "等待 Milvus 服务启动..."
    max_attempts=30
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:9091/healthz > /dev/null 2>&1; then
            break
        fi
        sleep 1
        echo -n "."
        attempt=$((attempt + 1))
    done
    
    if check_service 9091; then
        echo -e " ${GREEN}OK${NC}"
        echo -e "${GREEN}Milvus 服务启动成功${NC}"
    else
        echo -e " ${RED}超时${NC}"
        echo -e "${RED}Milvus 服务启动失败${NC}"
    fi
fi

echo ""
echo "============================================"
echo "Step 3: 启动后端服务"
echo "============================================"
if check_service 8100; then
    echo -e "${YELLOW}后端服务已在运行 (port 8100)${NC}"
else
    echo "启动后端服务..."
    cd $PROJECT_DIR/backend/vanna
    source /home/ubuntu/miniconda/etc/profile.d/conda.sh
    conda activate nl2sqlagent

    python api_server.py > $PROJECT_DIR/backend/vanna/backend_service.log 2>&1 &

    # 等待后端服务启动并健康检查
    echo -n "等待后端服务启动..."
    max_attempts=30
    attempt=1
    backend_ready=false
    
    while [ $attempt -le $max_attempts ]; do
        # 检查端口是否开放
        if lsof -i:8100 > /dev/null 2>&1; then
            # 尝试访问 API 文档或健康检查端点
            if curl -s http://localhost:8100/docs > /dev/null 2>&1; then
                backend_ready=true
                break
            fi
        fi
        sleep 1
        echo -n "."
        attempt=$((attempt + 1))
    done
    
    if [ "$backend_ready" = true ]; then
        echo -e " ${GREEN}OK${NC}"
        echo -e "${GREEN}后端服务启动成功 (port 8100)${NC}"
        echo "   API 文档: http://localhost:8100/docs"
    else
        echo -e " ${RED}超时${NC}"
        echo -e "${RED}后端服务启动失败${NC}"
    fi
fi

echo ""
echo "============================================"
echo "Step 4: 启动前端服务"
echo "============================================"
if check_service 3000; then
    echo -e "${YELLOW}前端服务已在运行 (port 3000)${NC}"
else
    echo "启动前端服务..."
    cd $PROJECT_DIR/frontend
    node ./node_modules/vite/bin/vite.js --host 0.0.0.0 --port 3000 > /dev/null 2>&1 &

    sleep 3
    if check_service 3000; then
        echo -e "${GREEN}前端服务启动成功 (port 3000)${NC}"
    else
        echo -e "${RED}前端服务启动失败${NC}"
    fi
fi

echo ""
echo "============================================"
echo "  所有服务启动完成！"
echo "============================================"
echo ""
echo "服务地址："
echo "  - 前端:     http://localhost:3000"
echo "  - 后端:     http://localhost:8100"
echo "  - API文档:  http://localhost:8100/docs"
echo "  - Jina:     http://localhost:8898"
echo "  - Milvus:   http://localhost:19530"
echo "  - Milvus健康检查: http://localhost:9091/healthz"
echo ""
