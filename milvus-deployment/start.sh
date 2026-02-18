#!/bin/bash
# Milvus 启动脚本

echo "启动 Milvus 服务..."
docker compose up -d

echo ""
echo "等待服务启动..."
sleep 10

echo ""
echo "检查服务状态..."
docker compose ps

echo ""
echo "Milvus 服务信息："
echo "  - gRPC 端口: 19530"
echo "  - HTTP 端口: 9091"
echo "  - Attu 管理界面: http://localhost:8000"
echo "  - MinIO 控制台: http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo "验证连接："
echo "  curl http://localhost:9091/healthz"
echo ""
echo "运行测试："
echo "  python test_connection.py"
