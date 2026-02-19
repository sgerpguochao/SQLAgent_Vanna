// 真实API服务
import axios from 'axios';
import { config, getApiUrl } from '../config';

// 配置axios基础URL
const API_BASE_URL = config.apiBaseUrl;

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: config.apiTimeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// 类型定义
export interface FileUploadResponse {
  success: boolean;
  file_id?: string;
  message: string;
  headers?: string[];
  column_info?: Array<{
    name: string;
    type: string;
    nullable: boolean;
    unique_values: number;
    sample_values: any[];
  }>;
  total_columns?: number;
  estimated_rows?: number;
}

export interface QueryRequest {
  query?: string;
  sql?: string;
  table_name?: string;
  file_id?: string;
  limit?: number;
  db_name?: string;
}

export interface QueryResponse {
  success: boolean;
  data?: any[];
  answer?: string;
  sql?: string;
  total_rows?: number;
  returned_rows?: number;
  columns?: string[];
  error?: string;
  visualization?: string;
}

export interface VisualizationRequest {
  file_id?: string;
  chart_type: 'bar' | 'line' | 'pie' | 'scatter' | 'histogram' | 'box' | 'heatmap';
  x_column?: string;
  y_column?: string;
  group_by?: string;
  title?: string;
  limit?: number;
}

export interface VisualizationResponse {
  success: boolean;
  chart_url?: string;
  chart_html?: string;
  error?: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  file_id?: string;
  table_name?: string;
}

export interface ChatResponse {
  success: boolean;
  message: string;
  session_id: string;
  data?: any[];
  visualization?: string;
  error?: string;
}

export interface FileInfo {
  file_id: string;
  filename: string;
  file_type: string;
  total_columns: number;
  estimated_rows: number;
}

export interface DatabaseConnectionConfig {
  host: string;
  port: string;
  username: string;
  password: string;
  database?: string;
}

export interface DatabaseConnectionResponse {
  success: boolean;
  message: string;
  databases?: string[];
  tables?: Array<{
    name: string;
    type: string;
    children?: Array<{
      name: string;
      type: string;
      dataType: string;
      nullable: boolean;
      key: string;
      default: any;
      extra: string;
    }>;
  }>;
}

// API服务
export const api = {
  // 获取数据源列表
  async getDataSources(): Promise<{ success: boolean; sources: any[] }> {
    const response = await apiClient.get('/api/datasources');
    return response;
  },

  // 上传文件
  async uploadFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  // 查询数据
  async queryData(request: QueryRequest): Promise<QueryResponse> {
    console.log('API.queryData - 请求参数:', request);
    console.log('API.queryData - baseURL:', API_BASE_URL);
    console.log('API.queryData - 完整URL:', `${API_BASE_URL}/api/query`);
    const response = await apiClient.post('/api/query', request);
    console.log('API.queryData - 响应:', response);
    return response;
  },

  // 创建可视化
  async createVisualization(request: VisualizationRequest): Promise<VisualizationResponse> {
    const response = await apiClient.post('/api/visualize', request);
    return response;
  },

  // 聊天对话
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await apiClient.post('/api/v1/chat', request);
    return response;
  },

  // 获取文件列表
  async getFiles(): Promise<{ files: FileInfo[] }> {
    const response = await apiClient.get('/api/files');
    return response;
  },

  // 删除文件
  async deleteFile(fileId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete(`/api/files/${fileId}`);
    return response;
  },

  // 健康检查
  async healthCheck(): Promise<{
    status: string;
    files_loaded: number;
    active_agents: number;
    active_sessions: number;
  }> {
    const response = await apiClient.get('/health');
    return response;
  },

  // 测试数据库连接
  async testDatabaseConnection(config: DatabaseConnectionConfig): Promise<DatabaseConnectionResponse> {
    const response = await apiClient.post('/api/v1/database/test', config);
    return response;
  },

  // 连接数据库并获取表结构
  async connectDatabase(config: DatabaseConnectionConfig): Promise<DatabaseConnectionResponse> {
    const response = await apiClient.post('/api/v1/database/connect', config);
    return response;
  }
};

// 导出文件上传辅助函数
export const uploadFileHelper = async (file: File) => {
  try {
    const result = await api.uploadFile(file);
    if (result.success) {
      return {
        success: true,
        fileId: result.file_id!,
        filename: file.name,
        headers: result.headers!,
        columnInfo: result.column_info!,
        totalColumns: result.total_columns!,
        estimatedRows: result.estimated_rows!
      };
    } else {
      throw new Error(result.message || '上传失败');
    }
  } catch (error: any) {
    console.error('Upload error:', error);
    return {
      success: false,
      error: error.response?.data?.detail || error.message || '上传文件失败'
    };
  }
};

// 导出查询辅助函数
export const queryDataHelper = async (query: string, fileId?: string) => {
  try {
    if (!fileId) {
      throw new Error('请先上传文件');
    }

    const result = await api.queryData({
      query,
      file_id: fileId,
      limit: 100
    });

    if (result.success) {
      return {
        success: true,
        data: result.data || [],
        answer: result.answer || '',
        columns: result.columns || [],
        totalRows: result.total_rows || 0,
        returnedRows: result.returned_rows || 0
      };
    } else {
      throw new Error(result.error || '查询失败');
    }
  } catch (error: any) {
    console.error('Query error:', error);
    return {
      success: false,
      error: error.response?.data?.detail || error.message || '查询数据失败'
    };
  }
};

// 导出可视化辅助函数
export const createVisualizationHelper = async (
  chartType: string,
  fileId?: string,
  xColumn?: string,
  yColumn?: string,
  title?: string
) => {
  try {
    if (!fileId) {
      throw new Error('请先上传文件');
    }

    const result = await api.createVisualization({
      file_id: fileId,
      chart_type: chartType as any,
      x_column: xColumn,
      y_column: yColumn,
      title: title,
      limit: 100
    });

    if (result.success) {
      return {
        success: true,
        chartHtml: result.chart_html!
      };
    } else {
      throw new Error(result.error || '创建可视化失败');
    }
  } catch (error: any) {
    console.error('Visualization error:', error);
    return {
      success: false,
      error: error.response?.data?.detail || error.message || '创建可视化失败'
    };
  }
};

// 导出聊天辅助函数
export const chatHelper = async (
  message: string,
  fileId?: string,
  sessionId?: string,
  tableName?: string
) => {
  try {
    // 如果没有fileId但有tableName，使用tableName查询
    if (!fileId && !tableName) {
      throw new Error('请先上传文件或选择数据源');
    }

    const result = await api.chat({
      message,
      file_id: fileId,
      table_name: tableName,
      session_id: sessionId
    });

    if (result.success) {
      return {
        success: true,
        message: result.message,
        sessionId: result.session_id,
        data: result.data || []
      };
    } else {
      throw new Error(result.error || '对话失败');
    }
  } catch (error: any) {
    console.error('Chat error:', error);
    return {
      success: false,
      error: error.response?.data?.detail || error.message || '发送消息失败'
    };
  }
};