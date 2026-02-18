# 前端环境变量配置说明

## 概述

本项目已将所有硬编码的 `localhost:xxx` API 地址统一改为通过环境变量管理，支持灵活部署到本地开发环境和云服务器。

## 配置文件说明

### 1. `.env.development` - 开发环境配置
```bash
# 开发环境配置
VITE_API_BASE_URL=http://117.50.174.50:8100
VITE_API_TIMEOUT=30000
```

**用途**：本地开发时使用，指向本地后端服务

### 2. `.env.production` - 生产环境配置
```bash
# 生产环境配置
VITE_API_BASE_URL=http://your-server-ip:8000
VITE_API_TIMEOUT=30000
```

**用途**：打包生产版本时使用，需要修改为实际的云服务器地址

### 3. `.env.example` - 配置示例
模板文件，用于团队共享配置格式

### 4. `.env.local` - 本地覆盖配置（可选）
如果需要临时修改配置而不影响版本控制，可以创建此文件

## 🔧 配置项说明

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `VITE_API_BASE_URL` | 后端 API 基础地址 | `http://117.50.174.50:8100` | `http://192.168.1.100:8000` 或 `https://api.example.com` |
| `VITE_API_TIMEOUT` | API 请求超时时间（毫秒） | `30000` | `60000`（1分钟） |

## 部署到云服务器

### 步骤 1: 修改生产环境配置

编辑 `frontend/.env.production` 文件：

```bash
# 将 your-server-ip 替换为实际的服务器 IP 或域名
VITE_API_BASE_URL=http://47.xxx.xxx.xxx:8000
# 或使用域名
VITE_API_BASE_URL=https://api.yourdomain.com
```

### 步骤 2: 构建生产版本

```bash
cd frontend
npm run build
```

构建过程会自动读取 `.env.production` 中的配置。

### 步骤 3: 部署到服务器

将 `frontend/dist/` 目录下的所有文件上传到服务器的 Web 目录。

## 🛠️ 开发模式

### 本地开发
```bash
cd frontend
npm run dev
```

自动读取 `.env.development` 配置，连接到本地后端 `http://117.50.174.50:8100`

### 连接到远程后端开发
如果需要在本地开发时连接到远程后端，创建 `.env.local`：

```bash
# .env.local（优先级最高）
VITE_API_BASE_URL=http://47.xxx.xxx.xxx:8000
VITE_API_TIMEOUT=30000
```

## 代码结构

### 配置管理模块
**文件位置**：`frontend/src/config/index.ts`

```typescript
// 应用配置
export const config = {
  apiBaseUrl: getEnvVar('VITE_API_BASE_URL', 'http://117.50.174.50:8100'),
  apiTimeout: parseInt(getEnvVar('VITE_API_TIMEOUT', '30000'), 10),
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
};

// API 端点
export const API_ENDPOINTS = {
  CHAT_STREAM: '/api/v1/chat/stream',
  DATABASE_TEST: '/api/v1/database/test',
  DATABASE_CONNECT: '/api/v1/database/connect',
  TRAINING_GET: '/api/v1/training/get',
  TRAINING_ADD: '/api/v1/training/add',
  TRAINING_DELETE: '/api/v1/training/delete',
};

// 构建完整 URL
export const getApiUrl = (path: string): string => {
  return `${config.apiBaseUrl}${path}`;
};
```

### 使用示例

```typescript
// 在组件中使用
import { getApiUrl, API_ENDPOINTS } from '../config';

// 发起请求
const response = await fetch(getApiUrl(API_ENDPOINTS.CHAT_STREAM), {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: '...' })
});
```