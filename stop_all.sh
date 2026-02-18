#!/bin/bash

# NL2SQL 系统一键停止脚本
# 停止所有服务

echo "============================================"
echo "  NL2SQL 系统一键停止"
echo "============================================"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_DIR="/home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1"

# 函数：停止指定端口的服务
stop_port() {
    local port=$1
    local name=$2

    # 尝试通过 lsof 查找进程
    local pid=$(lsof -ti:$port 2>/dev/null)

    if [ -n "$pid" ]; then
        echo "停止 $name (PID: $pid)..."
        kill $pid 2>/dev/null
        sleep 1

        # 检查是否成功停止
        if lsof -i:$port > /dev/null 2>&1; then
            echo -e "${YELLOW}  强制停止...${NC}"
            kill -9 $pid 2>/dev/null
        fi
        echo -e "${GREEN}  $name 已停止${NC}"
    else
        echo -e "${YELLOW}$name 未运行${NC}"
    fi
}

echo ""
echo "============================================"
echo "Step 1: 停止前端服务 (port 3000)"
echo "============================================"
stop_port 3000 "前端服务"

echo ""
echo "============================================"
echo "Step 2: 停止后端服务 (port 8100)"
echo "============================================"
stop_port 8100 "后端服务"

echo ""
echo "============================================"
echo "Step 3: 停止 Jina Embedding 服务 (port 8898)"
echo "============================================"
stop_port 8898 "Jina Embedding 服务"

echo ""
echo "============================================"
echo "Step 4: 停止 Milvus 服务"
echo "============================================"
cd $PROJECT_DIR/milvus-deployment/milvus_server
if docker compose ps > /dev/null 2>&1; then
    echo "停止 Milvus 服务..."
    docker compose down > /dev/null 2>&1
    echo -e "${GREEN}Milvus 服务已停止${NC}"
else
    echo -e "${YELLOW}Milvus 服务未运行${NC}"
fi

echo ""
echo "============================================"
echo "  注意: MySQL 服务需要手动停止"
echo "============================================"
echo "  如需停止 MySQL: sudo systemctl stop mysql"
echo ""

echo -e "${GREEN}所有服务已停止！${NC}"
