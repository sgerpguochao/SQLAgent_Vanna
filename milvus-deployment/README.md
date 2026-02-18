# Milvus 部署包

本目录包含 Milvus 向量数据库的完整部署配置，开箱即用。

## 快速开始

### 1. 启动服务

```bash
chmod +x *.sh
./start.sh
```

### 2. 验证连接

```bash
python test_connection.py
```

### 3. 运行完整测试

```bash
python test_full.py
```

## 文件说明

- `docker-compose.yml` - Docker 服务编排配置
- `.env` - 环境变量配置
- `start.sh` - 启动脚本
- `stop.sh` - 停止脚本
- `restart.sh` - 重启脚本
- `test_connection.py` - 连接测试脚本
- `test_full.py` - 完整功能测试脚本

## 端口说明

- `19530` - Milvus gRPC（Python 客户端连接）
- `9091` - Milvus HTTP（健康检查）
- `9000` - MinIO API
- `9001` - MinIO 控制台
- `8000` - Attu 管理界面

## 管理界面

- Attu: http://localhost:8000
- MinIO: http://localhost:9001 (minioadmin/minioadmin)

## 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 停止服务
./stop.sh

# 重启服务
./restart.sh
```
