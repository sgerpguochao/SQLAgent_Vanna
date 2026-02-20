import { useState, useEffect, useRef } from 'react';
import { Plus, Trash2, Download, Upload, Database, RefreshCw, Search, Filter, AlertTriangle, FileArchive, Lock, X, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { toast } from 'sonner';
import { getApiUrl, API_ENDPOINTS } from '../config';
import { api } from '../services/api';

// 示例数据模板（从 nl2sql_training_data.py 提取）
const EXAMPLE_TEMPLATES = {
  documentation: `表名: dim_product
描述: 存储所有电子产品的基本信息，用于产品分析
字段:
- product_sk (BIGINT, 主键): 产品唯一标识，代理键
- product_name (VARCHAR): 产品完整名称，如"OPPO 投影仪 X4"
- brand (VARCHAR): 品牌名称，如"OPPO"、"小米"、"苹果"、"华为"
- category (VARCHAR): 产品分类，如"投影仪"、"智能手机"、"电视"、"耳机"
记录数: 800`,

  ddl: `CREATE TABLE dim_product (
    product_sk      BIGINT NOT NULL COMMENT '产品唯一标识，代理键',
    product_name    VARCHAR(255) COMMENT '产品完整名称',
    brand           VARCHAR(100) COMMENT '品牌名称',
    category        VARCHAR(100) COMMENT '产品分类',
    PRIMARY KEY (product_sk)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品维度表';`,

  sql: `SELECT
    p.brand,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.price * f.quantity), 2) AS total_gmv
FROM fact_sales_electronics f
JOIN dim_product p ON f.product_sk = p.product_sk
GROUP BY p.brand
ORDER BY total_quantity DESC
LIMIT 10`,

  plan: `客户购买行为分析：分析客户的购买频次、购买金额、购买商品类别等，用于精准营销和客户分层`
};

interface TrainingDataPanelProps {
  selectedDatabase?: string | null;
}

interface TrainingData {
  id: string;
  data_type: string;
  content: string;
  question?: string;
  db_name?: string;
  table_name?: string;
  tables?: string;
}

export function TrainingDataPanel({ selectedDatabase }: TrainingDataPanelProps) {
  const [trainingData, setTrainingData] = useState<TrainingData[]>([]);
  const [filteredData, setFilteredData] = useState<TrainingData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [filterType, setFilterType] = useState<string>('all');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<TrainingData | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [databaseList, setDatabaseList] = useState<string[]>([]);
  const [selectedDbName, setSelectedDbName] = useState<string>('');

  // 导入相关状态
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importDbName, setImportDbName] = useState<string>('');
  const [importFile, setImportFile] = useState<File | null>(null);
  const [clearBeforeImport, setClearBeforeImport] = useState<boolean>(true);
  const [isImporting, setIsImporting] = useState(false);
  const [importProgress, setImportProgress] = useState<string>('');
  const [countdown, setCountdown] = useState<number>(0);
  const [importResult, setImportResult] = useState<{success: boolean; message: string; summary?: any} | null>(null);
  const [fileError, setFileError] = useState<string>('');
  const [dbError, setDbError] = useState<string>('');

  // 添加表单状态
  const [dataType, setDataType] = useState<'documentation' | 'ddl' | 'sql' | 'plan'>('sql');
  const [content, setContent] = useState('');
  const [question, setQuestion] = useState('');
  const [tableName, setTableName] = useState('');
  const [tables, setTables] = useState('');

  // 加载训练数据（分页获取所有数据）
  const loadTrainingData = async () => {
    setIsLoading(true);
    try {
      let allData: TrainingData[] = [];
      let offset = 0;
      const batchSize = 500;
      
      // 分页获取所有数据
      while (true) {
        const response = await fetch(getApiUrl(API_ENDPOINTS.TRAINING_GET) + `?limit=${batchSize}&offset=${offset}`, {
          cache: 'no-store',  // 禁用缓存
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
          }
        });
        const data = await response.json();
        
        if (data.success && data.data && data.data.length > 0) {
          allData = [...allData, ...data.data];
          // 如果返回数据少于batchSize，说明已经获取完毕
          if (data.data.length < batchSize) {
            break;
          }
          offset += batchSize;
        } else {
          break;
        }
      }
      
      
      setTrainingData(allData);
      toast.success(`加载了 ${allData.length} 条训练数据`);
    } catch (error) {
      console.error('加载训练数据失败:', error);
      toast.error('加载训练数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 从后端获取数据库列表
  const loadDatabaseList = async () => {
    try {
      const result = await api.getConnectedDatabases();
      if (result.success && result.databases) {
        return result.databases;
      }
    } catch (e) {
      console.error('从后端获取数据库列表失败:', e);
      // 降级到从 localStorage 获取
      try {
        const configs = localStorage.getItem('dataSourceConfigs');
        if (configs) {
          const parsed = JSON.parse(configs);
          const dbList = parsed.map((c: any) => c.database).filter(Boolean);
          return [...new Set(dbList)];
        }
      } catch (e2) {
        console.error('读取数据库列表失败:', e2);
      }
    }
    return [];
  };

  // 添加训练数据
  const handleAdd = async () => {
    if (!content.trim()) {
      toast.error('请输入训练数据内容');
      return;
    }

    if (dataType === 'sql' && !question.trim()) {
      toast.error('SQL 类型需要提供对应的问题');
      return;
    }

    // 检查是否选择了数据库
    if (!selectedDbName) {
      toast.error('请选择数据库');
      return;
    }

    setIsLoading(true);
    try {
      // 构建请求参数
      const requestBody: any = {
        data_type: dataType,
        content: content,
        db_name: selectedDbName
      };

      // 根据类型添加不同字段
      if (dataType === 'sql' || dataType === 'plan') {
        requestBody.question = dataType === 'sql' ? question : content; // plan 使用 content 作为 topic
        requestBody.tables = tables || '';
      } else if (dataType === 'ddl' || dataType === 'documentation') {
        requestBody.table_name = tableName || '';
      }

      const response = await fetch(getApiUrl(API_ENDPOINTS.TRAINING_ADD), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      const data = await response.json();

      if (data.success) {
        toast.success(data.message || '添加成功');
        setContent('');
        setQuestion('');
        setTableName('');
        setTables('');
        setShowAddForm(false);
        loadTrainingData();
      } else {
        toast.error(data.message || '添加失败');
      }
    } catch (error) {
      console.error('添加训练数据失败:', error);
      toast.error('添加训练数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 打开删除确认对话框
  const openDeleteDialog = (item: TrainingData) => {
    setItemToDelete(item);
    setDeleteDialogOpen(true);
  };

  // 确认删除训练数据
  const confirmDelete = async () => {
    if (!itemToDelete) return;

    setIsLoading(true);
    try {
      const response = await fetch(getApiUrl(API_ENDPOINTS.TRAINING_DELETE), {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: itemToDelete.id })
      });

      const data = await response.json();

      if (data.success) {
        toast.success('删除成功');
        loadTrainingData();
        setDeleteDialogOpen(false);
        setItemToDelete(null);
      } else {
        toast.error(data.message || '删除失败');
      }
    } catch (error) {
      console.error('删除训练数据失败:', error);
      toast.error('删除训练数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 打开导入弹窗
  const openImportDialog = () => {
    setImportDbName(selectedDbName || (databaseList.length > 0 ? databaseList[0] : ''));
    setImportFile(null);
    setClearBeforeImport(true);
    setImportResult(null);
    setFileError('');
    setDbError('');
    setImportProgress('');
    setShowImportDialog(true);
  };

  // 验证导入表单
  const validateImportForm = (): boolean => {
    let isValid = true;
    
    // 验证数据库选择
    if (!importDbName) {
      setDbError('请选择数据库');
      isValid = false;
    } else {
      setDbError('');
    }
    
    // 验证文件选择
    if (!importFile) {
      setFileError('请选择要上传的ZIP文件');
      isValid = false;
    } else if (!importFile.name.toLowerCase().endsWith('.zip')) {
      setFileError('只支持.zip格式的文件');
      isValid = false;
    } else {
      setFileError('');
    }
    
    return isValid;
  };

  // 处理文件选择
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.zip')) {
        setFileError('只支持.zip格式的文件');
        setImportFile(null);
      } else if (file.size > 50 * 1024 * 1024) {
        setFileError('文件大小不能超过50MB');
        setImportFile(null);
      } else {
        setFileError('');
        setImportFile(file);
      }
    }
  };

  // 执行导入
  const handleImport = async () => {
    if (!validateImportForm()) {
      return;
    }

    setIsImporting(true);
    setImportProgress('正在上传并导入...');
    setImportResult(null);

    try {
      const formData = new FormData();
      formData.append('file', importFile!);
      formData.append('db_name', importDbName);
      formData.append('clear_before_import', clearBeforeImport.toString());

      const response = await fetch(getApiUrl(API_ENDPOINTS.TRAINING_IMPORT), {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setImportResult({
          success: true,
          message: data.message,
          summary: data.import_summary
        });
        setImportProgress('');
        toast.success(data.message || '导入成功');
        // 刷新数据
        loadTrainingData();
        
        // 成功后5秒自动关闭弹窗
        setCountdown(5);
        const timer = setInterval(() => {
          setCountdown(prev => {
            if (prev <= 1) {
              clearInterval(timer);
              closeImportDialog();
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      } else {
        setImportResult({
          success: false,
          message: data.detail || data.message || '导入失败'
        });
        setImportProgress('');
        toast.error(data.detail || data.message || '导入失败');
      }
    } catch (error) {
      console.error('导入失败:', error);
      setImportResult({
        success: false,
        message: '导入失败: ' + (error as Error).message
      });
      setImportProgress('');
      toast.error('导入失败');
    } finally {
      setIsImporting(false);
    }
  };

  // 关闭导入弹窗
  const closeImportDialog = () => {
    if (!isImporting) {
      setShowImportDialog(false);
      setImportFile(null);
      setImportResult(null);
      setCountdown(0);
    }
  };

  // 使用示例模板
  const useTemplate = () => {
    if (dataType === 'plan') {
      setContent(EXAMPLE_TEMPLATES.plan);
    } else {
      setContent(EXAMPLE_TEMPLATES[dataType]);
      if (dataType === 'sql') {
        setQuestion('哪个品牌销量最高？');
      }
    }
  };

  // 过滤和搜索
  useEffect(() => {
    let filtered = trainingData;

    // 按类型过滤
    if (filterType !== 'all') {
      filtered = filtered.filter(item => item.data_type === filterType);
    }

    // 按关键词搜索
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(item =>
        item.content.toLowerCase().includes(query) ||
        (item.question && item.question.toLowerCase().includes(query))
      );
    }

    setFilteredData(filtered);
  }, [trainingData, filterType, searchQuery]);

  useEffect(() => {
    loadTrainingData();
    // 加载数据库列表
    loadDatabaseList().then(dbs => {
      setDatabaseList(dbs);
    });
    // 如果传入了 selectedDatabase，使用它
    if (selectedDatabase) {
      setSelectedDbName(selectedDatabase);
    }
  }, []);

  // 当 selectedDatabase 变化时更新
  useEffect(() => {
    if (selectedDatabase) {
      setSelectedDbName(selectedDatabase);
    }
  }, [selectedDatabase]);

  // 统计各类型数量
  const stats = {
    total: trainingData.length,
    sql: trainingData.filter(item => item.data_type === 'sql').length,
    ddl: trainingData.filter(item => item.data_type === 'ddl').length,
    documentation: trainingData.filter(item => item.data_type === 'documentation').length,
    plan: trainingData.filter(item => item.data_type === 'plan').length,
  };

  return (
    <div className="flex flex-col h-full bg-[#0B0D1E]">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/5 flex-shrink-0 bg-[#0B0D1E]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-semibold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
              训练数据管理
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              管理 SQL、DDL 和表文档训练数据，提升 AI 生成准确度
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              onClick={loadTrainingData}
              disabled={isLoading}
              size="sm"
              variant="outline"
              className="border-white/10 text-gray-400 hover:text-gray-300"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
            <Button
              onClick={openImportDialog}
              size="sm"
              variant="outline"
              className="border-purple-500/30 text-purple-400 hover:bg-purple-500/10"
            >
              <FileArchive className="w-4 h-4 mr-2" />
              批量导入
            </Button>
            <Button
              onClick={() => setShowAddForm(!showAddForm)}
              size="sm"
              className="bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-600 hover:to-cyan-600 text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              添加训练数据
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-5 gap-4">
          <div className="bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border border-cyan-500/20 rounded-lg p-4">
            <div className="text-2xl font-bold text-cyan-400">{stats.total}</div>
            <div className="text-xs text-gray-400 mt-1">总数据量</div>
          </div>
          <div className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-lg p-4">
            <div className="text-2xl font-bold text-blue-400">{stats.sql}</div>
            <div className="text-xs text-gray-400 mt-1">SQL 查询</div>
          </div>
          <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20 rounded-lg p-4">
            <div className="text-2xl font-bold text-purple-400">{stats.ddl}</div>
            <div className="text-xs text-gray-400 mt-1">DDL 结构</div>
          </div>
          <div className="bg-gradient-to-br from-emerald-500/10 to-green-500/10 border border-emerald-500/20 rounded-lg p-4">
            <div className="text-2xl font-bold text-emerald-400">{stats.documentation}</div>
            <div className="text-xs text-gray-400 mt-1">表文档</div>
          </div>
          <div className="bg-gradient-to-br from-orange-500/10 to-red-500/10 border border-orange-500/20 rounded-lg p-4">
            <div className="text-2xl font-bold text-orange-400">{stats.plan}</div>
            <div className="text-xs text-gray-400 mt-1">主题规划</div>
          </div>
        </div>

        {/* Search and Filter Bar */}
        <div className="flex items-center gap-3 mt-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="搜索训练数据..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-[#13152E] border border-white/10 rounded-lg text-gray-300 text-sm focus:outline-none focus:border-emerald-500/50"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-[160px] bg-[#13152E] border-white/10 text-gray-300">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="sql">SQL 查询</SelectItem>
                <SelectItem value="ddl">DDL 结构</SelectItem>
                <SelectItem value="documentation">表文档</SelectItem>
                <SelectItem value="plan">主题规划</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto min-h-0 px-6 py-4">
        {/* 添加表单 */}
        {showAddForm && (
          <div className="bg-gradient-to-br from-[#13152E] to-[#1a1b3e] rounded-xl border border-emerald-500/30 p-6 mb-6 shadow-lg shadow-emerald-500/10">
            <h3 className="text-lg font-semibold text-emerald-400 flex items-center gap-2 mb-4">
              <Plus className="w-5 h-5" />
              添加新训练数据
            </h3>

            <div className="grid grid-cols-2 gap-4">
              {/* Left Column */}
              <div className="space-y-4">
                {/* 数据库选择 - 下拉框 */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">数据库 <span className="text-red-400">*</span></label>
                  {databaseList.length > 0 ? (
                    <Select value={selectedDbName} onValueChange={setSelectedDbName}>
                      <SelectTrigger className="bg-[#0A0B1E] border-white/10 text-gray-300">
                        <SelectValue placeholder="选择数据库" />
                      </SelectTrigger>
                      <SelectContent>
                        {databaseList.map((db) => (
                          <SelectItem key={db} value={db}>
                            {db}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                      <span className="text-red-400 text-sm">无可用数据库</span>
                    </div>
                  )}
                </div>

                {/* 数据类型选择 */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">数据类型</label>
                  <Select value={dataType} onValueChange={(value: any) => setDataType(value)}>
                    <SelectTrigger className="bg-[#0A0B1E] border-white/10 text-gray-300">
                      <SelectValue placeholder="选择数据类型" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sql">SQL (示例查询)</SelectItem>
                      <SelectItem value="ddl">DDL (表结构)</SelectItem>
                      <SelectItem value="documentation">Documentation (表文档)</SelectItem>
                      <SelectItem value="plan">Plan (主题规划)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* SQL 问题输入 */}
                {dataType === 'sql' && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-300">业务问题</label>
                    <Textarea
                      placeholder="输入对应的业务问题，如：哪个品牌销量最高？"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      className="min-h-[80px] bg-[#0A0B1E] border-white/10 text-gray-300"
                    />
                  </div>
                )}

                {/* SQL 类型：涉及的数据表 */}
                {(dataType === 'sql' || dataType === 'plan') && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-300">涉及的数据表</label>
                    <Input
                      placeholder="如: customers,orders (逗号分隔)"
                      value={tables}
                      onChange={(e) => setTables(e.target.value)}
                      className="bg-[#0A0B1E] border-white/10 text-gray-300"
                    />
                  </div>
                )}

                {/* DDL/Doc 类型：表名称 */}
                {(dataType === 'ddl' || dataType === 'documentation') && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-300">表名称</label>
                    <Input
                      placeholder="如: customers"
                      value={tableName}
                      onChange={(e) => setTableName(e.target.value)}
                      className="bg-[#0A0B1E] border-white/10 text-gray-300"
                    />
                  </div>
                )}

                {/* 示例模板按钮 */}
                <Button
                  onClick={useTemplate}
                  size="sm"
                  variant="outline"
                  className="w-full border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
                >
                  <Download className="w-4 h-4 mr-2" />
                  使用示例模板
                </Button>
              </div>

              {/* Right Column - Content Input */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">训练内容</label>
                <Textarea
                  placeholder={`输入 ${dataType} 内容...`}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="min-h-[240px] bg-[#0A0B1E] border-white/10 text-gray-300 font-mono text-xs"
                />
              </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-3 mt-4">
              <Button
                onClick={handleAdd}
                disabled={isLoading}
                className="bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-600 hover:to-cyan-600 text-white"
              >
                <Upload className="w-4 h-4 mr-2" />
                {isLoading ? '添加中...' : '添加到训练集'}
              </Button>
              <Button
                onClick={() => {
                  setShowAddForm(false);
                  setContent('');
                  setQuestion('');
                  setTableName('');
                  setTables('');
                }}
                variant="outline"
                className="border-white/10 text-gray-400"
              >
                取消
              </Button>
            </div>
          </div>
        )}

        {/* 训练数据列表 */}
        {isLoading && trainingData.length === 0 ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin mx-auto mb-3" />
              <p className="text-gray-400">加载中...</p>
            </div>
          </div>
        ) : filteredData.length === 0 ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <Database className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 mb-2">
                {searchQuery || filterType !== 'all' ? '未找到匹配的训练数据' : '暂无训练数据'}
              </p>
              <p className="text-gray-500 text-sm">
                {searchQuery || filterType !== 'all' ? '尝试调整搜索条件或过滤器' : '点击上方按钮添加训练数据'}
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {filteredData.map((item, index) => (
              <div
                key={item.id}
                className="bg-[#13152E] rounded-lg border border-white/5 p-4 hover:border-emerald-500/40 hover:shadow-lg hover:shadow-emerald-500/10 transition-all duration-200 group"
              >
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex items-center gap-3 flex-1">
                    <span className={`text-xs px-3 py-1 rounded-full font-medium ${
                      item.data_type === 'sql' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                      item.data_type === 'ddl' ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' :
                      item.data_type === 'plan' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                      'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    }`}>
                      {item.data_type.toUpperCase()}
                    </span>
                    {item.question && (
                      <div className="flex-1">
                        <span className="text-xs text-gray-500 group-hover:text-gray-400">问题:</span>
                        <span className="text-sm text-gray-300 group-hover:text-gray-100 ml-2 transition-colors">{item.question}</span>
                      </div>
                    )}
                  </div>
                  <Button
                    onClick={() => openDeleteDialog(item)}
                    size="sm"
                    variant="ghost"
                    className="text-red-400 hover:text-red-300 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition-all duration-200"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                <pre className="text-xs text-gray-400 group-hover:text-gray-300 bg-[#0A0B1E] p-3 rounded overflow-x-auto max-h-[300px] overflow-y-auto border border-white/5 font-mono transition-colors">
                  {item.content}
                </pre>
              </div>
            ))}
          </div>
        )}

        {/* Showing count */}
        {filteredData.length > 0 && (
          <div className="text-center py-4 text-xs text-gray-500">
            显示 {filteredData.length} / {trainingData.length} 条训练数据
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="bg-[#0F1123] border-red-500/30 max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-400" />
              </div>
              <DialogTitle className="text-xl text-gray-100">确定要删除训练数据？</DialogTitle>
            </div>
            <DialogDescription className="text-gray-400 text-sm leading-relaxed">
              {itemToDelete && (
                <div className="space-y-2 mt-4">
                  <div className="bg-[#13152E] rounded-lg p-3 border border-white/10">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-xs px-2 py-1 rounded ${
                        itemToDelete.data_type === 'sql' ? 'bg-blue-500/20 text-blue-400' :
                        itemToDelete.data_type === 'ddl' ? 'bg-purple-500/20 text-purple-400' :
                        itemToDelete.data_type === 'plan' ? 'bg-orange-500/20 text-orange-400' :
                        'bg-emerald-500/20 text-emerald-400'
                      }`}>
                        {itemToDelete.data_type.toUpperCase()}
                      </span>
                      {itemToDelete.data_type === 'sql' && itemToDelete.question && (
                        <span className="text-xs text-gray-400">问题: {itemToDelete.question}</span>
                      )}
                      {itemToDelete.data_type === 'plan' && itemToDelete.tables && (
                        <span className="text-xs text-gray-400">表: {itemToDelete.tables}</span>
                      )}
                    </div>
                    <pre className="text-xs text-gray-500 bg-[#0A0B1E] p-2 rounded max-h-[80px] overflow-y-auto font-mono whitespace-pre-wrap">
                      {itemToDelete.content.length > 150 ? itemToDelete.content.substring(0, 150) + '...' : itemToDelete.content}
                    </pre>
                  </div>
                  <p className="text-red-400 text-sm font-medium">
                    ⚠️ 此操作无法撤销，删除后数据将永久丢失
                  </p>
                </div>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-2">
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={isLoading}
              className="border-white/10 text-gray-300 hover:bg-white/5"
            >
              取消
            </Button>
            <Button
              onClick={confirmDelete}
              disabled={isLoading}
              className="bg-red-500 hover:bg-red-600 text-white"
            >
              {isLoading ? '删除中...' : '确认删除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Dialog */}
      <Dialog open={showImportDialog} onOpenChange={closeImportDialog}>
        <DialogContent className="bg-[#0F1123] border-purple-500/30 max-w-lg">
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 rounded-full bg-purple-500/10 border border-purple-500/30 flex items-center justify-center">
                <FileArchive className="w-6 h-6 text-purple-400" />
              </div>
              <DialogTitle className="text-xl text-gray-100">批量导入训练数据</DialogTitle>
            </div>
            <DialogDescription className="text-gray-400 text-sm">
              上传ZIP压缩包，包含 ddl.jsonl、sql_parse.jsonl、doc.jsonl、plan.jsonl 四个文件
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* 数据库选择 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">
                选择数据库 <span className="text-red-400">*</span>
              </label>
              {databaseList.length > 0 ? (
                <Select value={importDbName} onValueChange={setImportDbName} disabled={isImporting}>
                  <SelectTrigger className={`bg-[#0A0B1E] border-white/10 text-gray-300 ${dbError ? 'border-red-500' : ''}`}>
                    <SelectValue placeholder="选择数据库" />
                  </SelectTrigger>
                  <SelectContent>
                    {databaseList.map((db) => (
                      <SelectItem key={db} value={db}>
                        {db}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <span className="text-red-400 text-sm">无可用数据库，请先连接数据库</span>
                </div>
              )}
              {dbError && <p className="text-red-400 text-xs">{dbError}</p>}
            </div>

            {/* 文件上传 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">
                选择ZIP文件 <span className="text-red-400">*</span>
              </label>
              <div className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
                fileError 
                  ? 'border-red-500 bg-red-500/5' 
                  : importFile 
                    ? 'border-purple-500 bg-purple-500/5' 
                    : 'border-white/10 hover:border-purple-500/30'
              }`}>
                {importFile ? (
                  <div className="flex items-center justify-center gap-2">
                    <FileArchive className="w-5 h-5 text-purple-400" />
                    <span className="text-gray-300 text-sm">{importFile.name}</span>
                    <span className="text-gray-500 text-xs">({(importFile.size / 1024).toFixed(1)} KB)</span>
                    {!isImporting && (
                      <button
                        onClick={() => setImportFile(null)}
                        className="ml-2 text-gray-400 hover:text-gray-200"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ) : (
                  <label className="cursor-pointer">
                    <input
                      type="file"
                      accept=".zip"
                      onChange={handleFileChange}
                      disabled={isImporting}
                      className="hidden"
                    />
                    <div className="py-4">
                      <Upload className="w-8 h-8 text-gray-500 mx-auto mb-2" />
                      <p className="text-gray-400 text-sm">点击选择或拖拽ZIP文件</p>
                      <p className="text-gray-500 text-xs mt-1">支持 .zip 格式，最大 50MB</p>
                    </div>
                  </label>
                )}
              </div>
              {fileError && <p className="text-red-400 text-xs">{fileError}</p>}
            </div>

            {/* 清理选项 */}
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="clearBeforeImport"
                checked={clearBeforeImport}
                onChange={(e) => setClearBeforeImport(e.target.checked)}
                disabled={isImporting}
                className="w-4 h-4 rounded border-white/20 bg-[#0A0B1E] text-purple-500 focus:ring-purple-500"
              />
              <label htmlFor="clearBeforeImport" className="text-sm text-gray-300">
                导入前清理该数据库的现有数据
              </label>
            </div>

            {/* 导入进度/结果 */}
            {isImporting && (
              <div className="bg-[#13152E] rounded-lg p-4 border border-purple-500/20">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
                  <span className="text-purple-400 text-sm">{importProgress || '正在导入...'}</span>
                </div>
              </div>
            )}

            {importResult && (
              <div className={`rounded-lg p-4 border ${
                importResult.success 
                  ? 'bg-green-500/10 border-green-500/30' 
                  : 'bg-red-500/10 border-red-500/30'
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  {importResult.success ? (
                    <CheckCircle className="w-5 h-5 text-green-400" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-400" />
                  )}
                  <span className={importResult.success ? 'text-green-400' : 'text-red-400'}>
                    {importResult.message}
                  </span>
                </div>
                {importResult.success && importResult.summary && (
                  <div className="mt-3">
                    <div className="grid grid-cols-4 gap-2 text-xs mb-3">
                      <div className="bg-[#0A0B1E] p-2 rounded text-center">
                        <div className="text-blue-400 font-bold">{importResult.summary.vannasql?.inserted || 0}</div>
                        <div className="text-gray-500">SQL</div>
                      </div>
                      <div className="bg-[#0A0B1E] p-2 rounded text-center">
                        <div className="text-purple-400 font-bold">{importResult.summary.vannaddl?.inserted || 0}</div>
                        <div className="text-gray-500">DDL</div>
                      </div>
                      <div className="bg-[#0A0B1E] p-2 rounded text-center">
                        <div className="text-emerald-400 font-bold">{importResult.summary.vannadoc?.inserted || 0}</div>
                        <div className="text-gray-500">Doc</div>
                      </div>
                      <div className="bg-[#0A0B1E] p-2 rounded text-center">
                        <div className="text-orange-400 font-bold">{importResult.summary.vannaplan?.inserted || 0}</div>
                        <div className="text-gray-500">Plan</div>
                      </div>
                    </div>
                    {countdown > 0 && (
                      <div className="text-center text-xs text-gray-500">
                        窗口将在 <span className="text-purple-400 font-bold">{countdown}</span> 秒后自动关闭
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={closeImportDialog}
              disabled={isImporting}
              className="border-white/10 text-gray-300"
            >
              {isImporting ? '' : '取消'}
            </Button>
            <Button
              onClick={handleImport}
              disabled={isImporting || !importFile || !importDbName}
              className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white"
            >
              {isImporting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  导入中...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  开始导入
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Loading Overlay */}
      {isImporting && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-[#0F1123] border border-purple-500/30 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl shadow-purple-500/20">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-purple-500/10 border border-purple-500/30 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
              </div>
              <h3 className="text-lg font-semibold text-gray-100 mb-2">正在导入训练数据</h3>
              <p className="text-gray-400 text-sm mb-4">{importProgress || '请稍候...'}</p>
              {importDbName && (
                <div className="bg-[#13152E] rounded-lg p-3 text-sm">
                  <span className="text-gray-500">数据库: </span>
                  <span className="text-purple-400">{importDbName}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
