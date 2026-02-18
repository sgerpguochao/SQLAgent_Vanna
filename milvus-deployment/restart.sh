#!/bin/bash
# Milvus 重启脚本

echo "🔄 重启 Milvus 服务..."
docker compose restart

echo "✅ 服务已重启"
echo ""
echo "💡 查看日志："
echo "  docker compose logs -f"
