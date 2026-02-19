/**
 * 应用配置管理
 * 统一管理所有环境变量和配置项
 */

interface AppConfig {
  apiBaseUrl: string;
  apiTimeout: number;
  isDevelopment: boolean;
  isProduction: boolean;
}

// 获取环境变量，提供默认值
const getEnvVar = (key: string, defaultValue: string): string => {
  return import.meta.env[key] || defaultValue;
};

// 应用配置
export const config: AppConfig = {
  // API 基础地址
  apiBaseUrl: getEnvVar('VITE_API_BASE_URL', 'http://117.50.174.50:8100'),

  // API 请求超时时间（毫秒）
  apiTimeout: parseInt(getEnvVar('VITE_API_TIMEOUT', '30000'), 10),

  // 环境判断
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
};

// 导出 API 端点构建函数
export const getApiUrl = (path: string): string => {
  // 确保 path 以 / 开头
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${config.apiBaseUrl}${normalizedPath}`;
};

// 常用 API 端点
export const API_ENDPOINTS = {
  // 聊天相关
  CHAT_STREAM: '/api/v1/chat/stream',

  // 数据库相关
  DATABASE_TEST: '/api/v1/database/test',
  DATABASE_CONNECT: '/api/v1/database/connect',

  // 训练数据相关
  TRAINING_GET: '/api/v1/training/get',
  TRAINING_ADD: '/api/v1/training/add',
  TRAINING_DELETE: '/api/v1/training/delete',
  TRAINING_IMPORT: '/api/v1/training/import',

  // 数据源相关（测试用）
  DATASOURCES: '/datasources',
};

export default config;
