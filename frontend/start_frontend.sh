#!/bin/bash

# 前端服务启动脚本

# 配置参数
FRONTEND_DIR="/home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/frontend"
HOST="0.0.0.0"
PORT="3000"
LOG_FILE="/home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/frontend/frontend_service.log"

# 切换到前端目录
cd $FRONTEND_DIR

# 检查 node_modules 是否存在
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# 启动前端服务
echo "Starting frontend service..."
node ./node_modules/vite/bin/vite.js --host $HOST --port $PORT > $LOG_FILE 2>&1 &

# 获取进程 PID
PID=$!
echo $PID > $FRONTEND_DIR/frontend_service.pid

echo "Frontend service started successfully!"
echo "PID: $PID"
echo "Log file: $LOG_FILE"
echo "Service URL: http://localhost:$PORT"
echo "Network URL: http://<your-ip>:$PORT"
