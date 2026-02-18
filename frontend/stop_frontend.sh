#!/bin/bash

# 前端服务停止脚本

FRONTEND_DIR="/home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/frontend"
PID_FILE="$FRONTEND_DIR/frontend_service.pid"
PORT=3000

if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping frontend service (PID: $PID)..."
        kill $PID
        rm -f $PID_FILE
        echo "Frontend service stopped successfully!"
    else
        echo "Process $PID not running, removing stale PID file..."
        rm -f $PID_FILE
    fi
else
    echo "PID file not found, checking for running process..."

    # 尝试通过端口查找进程
    PID=$(lsof -ti:$PORT 2>/dev/null || netstat -tlnp 2>/dev/null | grep :$PORT | awk '{print $7}' | cut -d'/' -f1)

    if [ -n "$PID" ]; then
        echo "Found process $PID, stopping..."
        kill $PID 2>/dev/null
        echo "Frontend service stopped successfully!"
    else
        echo "No running frontend service found."
    fi
fi
