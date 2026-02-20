import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Database, Table2, Search, Plus, Trash2, Server, X, Check } from 'lucide-react';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { HoverCard, HoverCardContent, HoverCardTrigger } from './ui/hover-card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { api } from '../services/api';

interface TableNode {
  name: string;
  type: 'schema' | 'table' | 'column';
  children?: TableNode[];
  tableName?: string; // 实际的数据库表名
  metadata?: {
    fields?: number;
    rows?: number;
    sample?: string;
  };
}

interface DataSource {
  name: string;
  table: string;
  rows: number;
  columns: string[];
  description: string;
  source: string;
}

// 数据源配置（包含连接信息）
interface DataSourceConfig {
  id: string;
  name: string;
  host: string;
  port: string;
  username: string;
  password: string;
  database: string;
  tables?: DataSource[]; // 保存的表结构
  createdAt: number;
}

interface DataSourcePanelProps {
  onTableSelect?: (tableName: string) => void;
  onDatabaseSelect?: (dbName: string) => void;
}

export function DataSourcePanel({ onTableSelect, onDatabaseSelect }: DataSourcePanelProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set(['数据库表']));
  const [searchQuery, setSearchQuery] = useState('');
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [isDbDialogOpen, setIsDbDialogOpen] = useState(false);
  const [dbConfig, setDbConfig] = useState({
    host: 'localhost',
    port: '3306',
    username: 'root',
    password: '',
    database: '',
  });

  // 数据源列表状态
  const [dataSourceConfigs, setDataSourceConfigs] = useState<DataSourceConfig[]>([]);
  const [selectedDataSourceId, setSelectedDataSourceId] = useState<string | null>(null);
  const [dataSourceName, setDataSourceName] = useState('');

  // 数据源列表搜索
  const [dataSourceSearchQuery, setDataSourceSearchQuery] = useState('');

  // 生成唯一ID
  const generateId = () => {
    return `ds_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  // 加载数据源配置列表
  const loadDataSourceConfigs = async () => {
    try {
      setLoading(true);
      
      // 先从后端 API 获取已连接的数据库列表
      try {
        const result = await api.getConnectedDatabases();
        if (result.success && result.database_configs && result.database_configs.length > 0) {
          // 将后端返回的数据库配置转换为数据源配置
          const configs: DataSourceConfig[] = result.database_configs.map((dbConfig: any, index: number) => ({
            id: `db_${index}`,
            name: dbConfig.name,
            type: 'mysql',
            host: dbConfig.host || '',
            port: dbConfig.port || 3306,
            username: dbConfig.username || '',
            password: dbConfig.password || '',
            database: dbConfig.dbname || dbConfig.name,
          }));
          
          setDataSourceConfigs(configs);
          
          // 如果有数据库，自动选择第一个
          if (configs.length > 0 && !selectedDataSourceId) {
            setSelectedDataSourceId(configs[0].id);
            // 立即加载第一个数据库的表结构
            setTimeout(() => {
              loadDataSourceTables(configs[0]);
            }, 100);
          }
          
          setLoading(false);
          return;
        }
      } catch (apiError) {
        console.warn('从后端获取数据库列表失败:', apiError);
      }
      
      // 如果后端没有数据，回退到 localStorage
      const savedConfigs = localStorage.getItem('dataSourceConfigs');
      if (savedConfigs) {
        const configs = JSON.parse(savedConfigs);
        setDataSourceConfigs(configs);
        // 如果有保存的配置，自动选择第一个
        if (configs.length > 0 && !selectedDataSourceId) {
          setSelectedDataSourceId(configs[0].id);
        }
      }
      // 无论是否有数据，都设置 loading 为 false
      setLoading(false);
    } catch (error) {
      console.error('加载数据源配置失败:', error);
      setLoading(false);
    }
  };

  // 保存数据源配置列表
  const saveDataSourceConfigs = (configs: DataSourceConfig[]) => {
    localStorage.setItem('dataSourceConfigs', JSON.stringify(configs));
    setDataSourceConfigs(configs);
  };

  // 加载数据源表结构
  const loadDataSourceTables = async (config: DataSourceConfig) => {
    try {
      setLoading(true);
      console.log('正在连接数据库:', config.host, config.database);
      const response = await api.connectDatabase({
        host: config.host,
        port: config.port,
        username: config.username,
        password: config.password,
        database: config.database,
      });

      console.log('数据库响应:', response);

      if (response.success && response.tables) {
        const tables = response.tables.map((table: any) => ({
          name: table.name,
          table: table.name,
          rows: 0,
          columns: table.children || [],
          description: `表 ${table.name}`,
          source: 'mysql',
          children: table.children,
        }));
        console.log('加载了', tables.length, '个表');
        setDataSources(tables);

        // 更新配置中的表结构 - 从 localStorage 获取最新配置
        const savedConfigs = localStorage.getItem('dataSourceConfigs');
        const currentConfigs = savedConfigs ? JSON.parse(savedConfigs) : dataSourceConfigs;
        const updatedConfigs = currentConfigs.map((c: DataSourceConfig) =>
          c.id === config.id ? { ...c, tables } : c
        );
        saveDataSourceConfigs(updatedConfigs);
      } else {
        console.error('连接失败:', response.message);
      }
    } catch (error) {
      console.error('加载表结构失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 切换数据源
  const handleSelectDataSource = async (configId: string) => {
    setSelectedDataSourceId(configId);
    
    // 从当前 dataSourceConfigs 状态中查找配置
    const config = dataSourceConfigs.find((c: DataSourceConfig) => c.id === configId);

    if (config) {
      console.log('[DataSourcePanel] Selected config:', config.id, config.name, 'database:', config.database);
      // 传递数据库信息给父组件
      if (onDatabaseSelect) {
        console.log('[DataSourcePanel] Calling onDatabaseSelect with:', config.database);
        onDatabaseSelect(config.database);
      }

      if (config.tables && config.tables.length > 0) {
        console.log('使用缓存的表结构:', config.tables.length, '个表');
        setDataSources(config.tables);
      } else {
        console.log('从数据库加载表结构...');
        await loadDataSourceTables(config);
      }
    }
  };

  // 删除数据源
  const handleDeleteDataSource = (configId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updatedConfigs = dataSourceConfigs.filter(c => c.id !== configId);
    saveDataSourceConfigs(updatedConfigs);

    // 如果删除的是当前选中的数据源，清空表结构
    if (selectedDataSourceId === configId) {
      setSelectedDataSourceId(updatedConfigs.length > 0 ? updatedConfigs[0].id : null);
      setDataSources(updatedConfigs.length > 0 && updatedConfigs[0].tables ? updatedConfigs[0].tables : []);
    }
  };

  useEffect(() => {
    loadDataSourceConfigs();
  }, []);

  // 当数据源配置加载完成后，自动加载选中数据源的表结构
  useEffect(() => {
    const loadTables = async () => {
      // 等待 dataSourceConfigs 更新后再处理
      if (dataSourceConfigs.length > 0) {
        // 如果没有选中任何数据源，默认选中第一个
        if (!selectedDataSourceId) {
          setSelectedDataSourceId(dataSourceConfigs[0].id);
        }

        const config = dataSourceConfigs.find(c => c.id === (selectedDataSourceId || dataSourceConfigs[0].id));
        if (config) {
          if (config.tables && config.tables.length > 0) {
            setDataSources(config.tables);
            setLoading(false);
          } else {
            await loadDataSourceTables(config);
          }
        }
      } else {
        // 没有数据源时，也设置 loading 为 false
        setLoading(false);
      }
    };
    loadTables();
  }, [dataSourceConfigs]);

  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleTestConnection = async () => {
    // 先校验所有字段
    if (!validateFields()) {
      return;
    }

    try {
      setIsTestingConnection(true);
      setTestResult(null);
      console.log('测试数据库连接:', dbConfig);

      const response = await api.testDatabaseConnection(dbConfig);
      setTestResult({
        success: response.success,
        message: response.message
      });

      // 如果连接成功且有数据源名称，则可以保存
      if (response.success && dataSourceName.trim()) {
        setCanSaveDataSource(true);
      } else {
        setCanSaveDataSource(false);
      }
    } catch (error) {
      console.error('测试连接失败:', error);
      setTestResult({
        success: false,
        message: '连接失败: ' + (error as Error).message
      });
      setCanSaveDataSource(false);
    } finally {
      setIsTestingConnection(false);
    }
  };

  const [canSaveDataSource, setCanSaveDataSource] = useState(false);

  // 字段校验状态
  const [fieldErrors, setFieldErrors] = useState<{
    name?: string;
    host?: string;
    port?: string;
    username?: string;
    database?: string;
  }>({});

  // 校验所有字段
  const validateFields = (): boolean => {
    const errors: typeof fieldErrors = {};

    if (!dataSourceName.trim()) {
      errors.name = '请输入数据源名称';
    }

    if (!dbConfig.host.trim()) {
      errors.host = '请输入主机地址';
    }

    if (!dbConfig.port.trim()) {
      errors.port = '请输入端口';
    }

    if (!dbConfig.username.trim()) {
      errors.username = '请输入用户名';
    }

    if (!dbConfig.database.trim()) {
      errors.database = '请输入数据库名称';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // 单个字段校验
  const validateField = (field: keyof typeof fieldErrors, value: string) => {
    const error = !value.trim() ? `请输入${field === 'name' ? '数据源名称' : field === 'host' ? '主机地址' : field === 'port' ? '端口' : field === 'username' ? '用户名' : '数据库名称'}` : '';
    setFieldErrors(prev => ({ ...prev, [field]: error }));
  };

  // 添加数据源到列表
  const handleAddDataSource = async () => {
    if (!testResult?.success || !dataSourceName.trim()) {
      return;
    }

    try {
      // 先连接数据库获取表结构
      const response = await api.connectDatabase(dbConfig);

      let tables: DataSource[] = [];
      if (response.success && response.tables) {
        tables = response.tables.map((table: any) => ({
          name: table.name,
          table: table.name,
          rows: 0,
          columns: table.children || [],
          description: `表 ${table.name}`,
          source: 'mysql',
          children: table.children,
        }));
      }

      // 创建新的数据源配置
      const newConfig: DataSourceConfig = {
        id: generateId(),
        name: dataSourceName.trim(),
        host: dbConfig.host,
        port: dbConfig.port,
        username: dbConfig.username,
        password: dbConfig.password,
        database: dbConfig.database,
        tables,
        createdAt: Date.now(),
      };

      // 添加到列表
      const updatedConfigs = [...dataSourceConfigs, newConfig];
      saveDataSourceConfigs(updatedConfigs);

      // 选中新添加的数据源
      setSelectedDataSourceId(newConfig.id);
      setDataSources(tables);

      // 关闭对话框并重置
      setIsDbDialogOpen(false);
      setTestResult(null);
      setDataSourceName('');
      setCanSaveDataSource(false);
      setDbConfig({
        host: 'localhost',
        port: '3306',
        username: 'root',
        password: '',
        database: '',
      });

      // 如果有表，自动选中第一个
      if (tables.length > 0) {
        const firstTable = tables[0].name;
        setSelectedTable(firstTable);
        setExpandedNodes(new Set(['数据库表']));
        if (onTableSelect) {
          onTableSelect(firstTable);
        }
      }
    } catch (error) {
      console.error('添加数据源失败:', error);
      alert('添加数据源失败: ' + (error as Error).message);
    }
  };

  const toggleNode = (nodeName: string) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeName)) {
      newExpanded.delete(nodeName);
    } else {
      newExpanded.add(nodeName);
    }
    setExpandedNodes(newExpanded);
  };

  const convertToTableNodes = (sources: DataSource[], dbName?: string): TableNode[] => {
    // 获取当前选中数据源的数据库名称
    const currentDbName = dbName || (selectedDataSourceId 
      ? dataSourceConfigs.find(ds => ds.id === selectedDataSourceId)?.database 
      : '数据库表');

    // 按source分组
    const grouped = sources.reduce((acc, source) => {
      const category = source.source === 'upload' ? '上传的文件' : (currentDbName || '数据库表');
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(source);
      return acc;
    }, {} as Record<string, DataSource[]>);

    return Object.entries(grouped).map(([category, sources]) => ({
      name: category,
      type: 'schema' as const,
      children: sources.map(source => {
        // 如果source.children已经存在(来自MySQL),直接使用
        let children: TableNode[] = [];

        if (source.children && Array.isArray(source.children)) {
          // MySQL数据库表的children已经是正确的格式
          children = source.children.map((child: any) => ({
            name: `${child.name} (${child.dataType})`,
            type: 'column' as const
          }));
        } else if (Array.isArray(source.columns)) {
          // 上传文件的columns是字符串数组
          children = source.columns.map(column => ({
            name: column,
            type: 'column' as const
          }));
        }

        return {
          name: source.name,
          type: 'table' as const,
          tableName: source.table, // 实际的数据库表名
          metadata: {
            fields: children.length,
            rows: source.rows || 0,
            sample: children.slice(0, 3).map(c => c.name.split(' ')[0]).join(', ') + (children.length > 3 ? '...' : '')
          },
          children
        };
      })
    }));
  };

  // 获取当前选中数据源的数据库名称
  const currentDbName = selectedDataSourceId 
    ? dataSourceConfigs.find(ds => ds.id === selectedDataSourceId)?.database 
    : undefined;

  const filteredDataSources = convertToTableNodes(dataSources, currentDbName).filter(ds =>
    ds.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    ds.children?.some(table => table.name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const renderTreeNode = (node: TableNode, level: number = 0) => {
    const isExpanded = expandedNodes.has(node.name);
    const hasChildren = node.children && node.children.length > 0;

    const icon = node.type === 'schema' ? (
      <Database className="w-3.5 h-3.5 text-cyan-400" />
    ) : node.type === 'table' ? (
      <Table2 className="w-3.5 h-3.5 text-blue-400" />
    ) : (
      <div className="w-1.5 h-1.5 rounded-full bg-purple-400/60 ml-1" />
    );

    const handleClick = () => {
      console.log('点击节点:', node.name, '类型:', node.type, '有子节点:', hasChildren);

      // 如果是table节点，优先选择表格
      if (node.type === 'table') {
        setSelectedTable(node.name);
        console.log('选中表格:', node.name);

        if (onTableSelect) {
          // 使用实际的数据库表名
          const actualTableName = node.tableName || node.name;
          console.log('传递表名:', actualTableName);
          onTableSelect(actualTableName);
        }

        // 如果table有子节点（字段），也展开/折叠
        if (hasChildren) {
          toggleNode(node.name);
        }
      } else if (hasChildren) {
        // schema节点只展开/折叠
        toggleNode(node.name);
      }
    };

    const content = (
      <div
        key={node.name}
        style={{ paddingLeft: `${level * 12}px` }}
        className="group"
      >
        <div
          className={`flex items-center gap-2 px-2 py-1.5 hover:bg-white/5 cursor-pointer rounded-md transition-colors ${
            node.type === 'table' && selectedTable === node.name ? 'bg-cyan-500/10 border-l-2 border-cyan-500' : ''
          }`}
          onClick={handleClick}
        >
          {hasChildren && (
            isExpanded ?
              <ChevronDown className="w-3 h-3 text-gray-500 flex-shrink-0" /> :
              <ChevronRight className="w-3 h-3 text-gray-500 flex-shrink-0" />
          )}
          {!hasChildren && <div className="w-3 flex-shrink-0" />}
          {icon}
          <span className="text-gray-300 text-xs truncate">{node.name}</span>
        </div>
      </div>
    );

    if (node.type === 'table' && node.metadata) {
      return (
        <React.Fragment key={node.name}>
          <HoverCard openDelay={300}>
            <HoverCardTrigger asChild>
              {content}
            </HoverCardTrigger>
            <HoverCardContent side="right" className="w-80 bg-[#1a1b3e] border-cyan-500/30 text-gray-200">
              <div className="space-y-2">
                <p className="text-xs text-cyan-400">表详情</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-400">字段数:</span>
                    <span className="ml-2 text-white">{node.metadata.fields}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">行数:</span>
                    <span className="ml-2 text-white">{node.metadata.rows?.toLocaleString()}</span>
                  </div>
                </div>
                <div>
                  <p className="text-gray-400 text-xs">示例字段:</p>
                  <p className="text-purple-300 text-xs font-mono mt-1">{node.metadata.sample}</p>
                </div>
              </div>
            </HoverCardContent>
          </HoverCard>
          {isExpanded && node.children?.map(child => renderTreeNode(child, level + 1))}
        </React.Fragment>
      );
    }

    return (
      <React.Fragment key={node.name}>
        {content}
        {isExpanded && node.children?.map(child => renderTreeNode(child, level + 1))}
      </React.Fragment>
    );
  };

  if (loading) {
    return (
      <div className="h-full flex flex-col bg-[#0d0e23] overflow-hidden">
        <div className="px-6 py-3 border-b border-white/10">
          <h2 className="text-cyan-400">数据源</h2>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-gray-400">加载中...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-[#0B0D1E] overflow-hidden">
      {/* Top: Data Source List */}
      <div className="h-1/2 flex flex-col border-b border-white/10">
        <div className="px-3 py-3 border-b border-white/5">
          <div className="flex items-center gap-2 mb-2">
            <Server className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs text-gray-400">数据源</span>
            <button
              onClick={() => {
                setDbConfig({
                  host: 'localhost',
                  port: '3306',
                  username: 'root',
                  password: '',
                  database: '',
                });
                setDataSourceName('');
                setTestResult(null);
                setCanSaveDataSource(false);
                setFieldErrors({});
                setIsDbDialogOpen(true);
              }}
              className="ml-auto w-6 h-6 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center transition-all group"
              title="添加数据源"
            >
              <Plus className="w-3 h-3 text-gray-400 group-hover:text-cyan-400" />
            </button>
          </div>

          {/* Search Data Source */}
          <div className="relative mb-2">
            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-3 h-3 text-gray-500" />
            <Input
              placeholder="搜索数据源..."
              value={dataSourceSearchQuery}
              onChange={(e) => setDataSourceSearchQuery(e.target.value)}
              className="pl-7 h-8 bg-[#13152E] border-white/5 text-gray-300 placeholder-gray-600 text-xs rounded-lg focus:border-cyan-500/30"
            />
          </div>

          {/* Data Source List */}
          <div className="space-y-1 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 280px)' }}>
            {dataSourceConfigs
              .filter(ds => ds.name.toLowerCase().includes(dataSourceSearchQuery.toLowerCase()))
              .map(ds => (
                <div
                  key={ds.id}
                  onClick={() => handleSelectDataSource(ds.id)}
                  className={`group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all ${
                    selectedDataSourceId === ds.id
                      ? 'bg-cyan-500/20 border border-cyan-500/30'
                      : 'hover:bg-white/5 border border-transparent'
                  }`}
                >
                  {selectedDataSourceId === ds.id ? (
                    <Check className="w-3 h-3 flex-shrink-0 text-cyan-400" />
                  ) : (
                    <div className="w-3 h-3 flex-shrink-0" />
                  )}
                  <Database className={`w-3 h-3 flex-shrink-0 ${selectedDataSourceId === ds.id ? 'text-cyan-400' : 'text-gray-500'}`} />
                  <span className={`text-xs truncate flex-1 ${selectedDataSourceId === ds.id ? 'text-cyan-300' : 'text-gray-400'}`}>
                    {ds.name}
                  </span>
                  <span className="text-[10px] text-gray-600">{ds.host}</span>
                  <button
                    onClick={(e) => handleDeleteDataSource(ds.id, e)}
                    className="opacity-0 group-hover:opacity-100 w-5 h-5 rounded hover:bg-red-500/20 flex items-center justify-center transition-all"
                    title="删除数据源"
                  >
                    <Trash2 className="w-3 h-3 text-red-400" />
                  </button>
                </div>
              ))}
            {dataSourceConfigs.length === 0 && (
              <div className="text-center py-4">
                <p className="text-gray-500 text-xs">暂无数据源</p>
                <p className="text-gray-600 text-[10px]">点击 + 添加数据源</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom: Table List */}
      <div className="h-1/2 flex flex-col">
        {/* Header with Add Button */}
        <div className="px-4 py-3 border-b border-white/5 flex-shrink-0 flex items-center justify-between">
          <h2 className="text-cyan-400 font-medium text-sm">数据库表</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setDbConfig({
                  host: 'localhost',
                  port: '3306',
                  username: 'root',
                  password: '',
                  database: '',
                });
                setDataSourceName('');
                setTestResult(null);
                setCanSaveDataSource(false);
                setFieldErrors({});
                setIsDbDialogOpen(true);
              }}
              className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center transition-all group"
              title="添加数据库"
            >
              <Plus className="w-4 h-4 text-gray-400 group-hover:text-cyan-400" />
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="px-3 py-2 border-b border-white/5 flex-shrink-0">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
            <Input
              placeholder="搜索表或段..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-8 bg-[#13152E] border-white/5 text-gray-300 placeholder-gray-600 text-sm rounded-lg focus:border-cyan-500/30"
            />
          </div>
        </div>

        {/* Table Tree */}
        <div className="flex-1 overflow-y-auto px-2 py-2">
          <div className="space-y-1">
            {filteredDataSources.map(ds => renderTreeNode(ds, 0))}
          </div>
        </div>
      </div>

      {/* MySQL Connection Dialog */}
      <Dialog open={isDbDialogOpen} onOpenChange={setIsDbDialogOpen}>
        <DialogContent className="max-w-2xl bg-[#2A2D3A] border-white/10 text-gray-200 p-0 gap-0">
          {/* Header */}
          <DialogHeader className="px-6 py-4 border-b border-white/10">
            <DialogTitle className="text-lg text-white flex items-center gap-2">
              <Database className="w-5 h-5 text-cyan-400" />
              连接 MySQL 数据库
            </DialogTitle>
          </DialogHeader>

          {/* Content */}
          <div className="px-6 py-6 space-y-4 max-h-[60vh] overflow-y-auto">
            {/* Data Source Name */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">
                数据源名称 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={dataSourceName}
                onChange={(e) => {
                  setDataSourceName(e.target.value);
                  validateField('name', e.target.value);
                  // 清除之前的保存状态
                  if (testResult?.success) {
                    setCanSaveDataSource(false);
                  }
                }}
                onBlur={(e) => validateField('name', e.target.value)}
                className={`w-full bg-[#1a1d2e] border ${fieldErrors.name ? 'border-red-500' : 'border-white/10'} text-gray-200 h-10 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500/30`}
                placeholder="例如：生产数据库"
              />
              {fieldErrors.name && <p className="text-red-500 text-xs mt-1">{fieldErrors.name}</p>}
            </div>

            {/* Host */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">
                主机地址 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={dbConfig.host}
                onChange={(e) => {
                  setDbConfig({ ...dbConfig, host: e.target.value });
                  validateField('host', e.target.value);
                }}
                onBlur={(e) => validateField('host', e.target.value)}
                className={`w-full bg-[#1a1d2e] border ${fieldErrors.host ? 'border-red-500' : 'border-white/10'} text-gray-200 h-10 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500/30`}
                placeholder="localhost"
              />
              {fieldErrors.host && <p className="text-red-500 text-xs mt-1">{fieldErrors.host}</p>}
            </div>

            {/* Port */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">
                端口 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={dbConfig.port}
                onChange={(e) => {
                  setDbConfig({ ...dbConfig, port: e.target.value });
                  validateField('port', e.target.value);
                }}
                onBlur={(e) => validateField('port', e.target.value)}
                className={`w-full bg-[#1a1d2e] border ${fieldErrors.port ? 'border-red-500' : 'border-white/10'} text-gray-200 h-10 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500/30`}
                placeholder="3306"
              />
              {fieldErrors.port && <p className="text-red-500 text-xs mt-1">{fieldErrors.port}</p>}
            </div>

            {/* Username */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">
                用户名 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={dbConfig.username}
                onChange={(e) => {
                  setDbConfig({ ...dbConfig, username: e.target.value });
                  validateField('username', e.target.value);
                }}
                onBlur={(e) => validateField('username', e.target.value)}
                className={`w-full bg-[#1a1d2e] border ${fieldErrors.username ? 'border-red-500' : 'border-white/10'} text-gray-200 h-10 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500/30`}
                placeholder="root"
              />
              {fieldErrors.username && <p className="text-red-500 text-xs mt-1">{fieldErrors.username}</p>}
            </div>

            {/* Password */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">
                密码 <span className="text-red-500">*</span>
              </label>
              <input
                type="password"
                value={dbConfig.password}
                onChange={(e) => setDbConfig({ ...dbConfig, password: e.target.value })}
                className="w-full bg-[#1a1d2e] border border-white/10 text-gray-200 h-10 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500/30"
                placeholder="••••••"
              />
            </div>

            {/* Database */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">
                数据库名称 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={dbConfig.database}
                onChange={(e) => {
                  setDbConfig({ ...dbConfig, database: e.target.value });
                  validateField('database', e.target.value);
                }}
                onBlur={(e) => validateField('database', e.target.value)}
                className={`w-full bg-[#1a1d2e] border ${fieldErrors.database ? 'border-red-500' : 'border-white/10'} text-gray-200 h-10 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500/30`}
                placeholder="例如：my_database"
              />
              {fieldErrors.database && <p className="text-red-500 text-xs mt-1">{fieldErrors.database}</p>}
            </div>

            {/* Test Result */}
            {testResult && (
              <div className={`p-3 rounded-lg border ${
                testResult.success
                  ? 'bg-green-500/10 border-green-500/30'
                  : 'bg-red-500/10 border-red-500/30'
              }`}>
                <div className="flex items-start gap-2">
                  {testResult.success ? (
                    <svg className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  )}
                  <div className="flex-1">
                    <p className={`text-sm font-medium ${
                      testResult.success ? 'text-green-300' : 'text-red-300'
                    }`}>
                      {testResult.success ? '测试成功' : '测试失败'}
                    </p>
                    <p className={`text-xs mt-1 ${
                      testResult.success ? 'text-green-400/80' : 'text-red-400/80'
                    }`}>
                      {testResult.message}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer with buttons */}
          <div className="px-6 py-4 border-t border-white/10 bg-[#23252F] flex items-center justify-between">
            <Button
              onClick={handleTestConnection}
              disabled={isTestingConnection || !dataSourceName.trim() || !dbConfig.host.trim() || !dbConfig.port.trim() || !dbConfig.username.trim() || !dbConfig.database.trim()}
              variant="outline"
              className="bg-transparent border-white/20 hover:bg-white/5 text-gray-300 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isTestingConnection ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-200" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  测试中...
                </>
              ) : (
                '测试连接'
              )}
            </Button>
            <div className="flex gap-3">
              <Button
                onClick={() => {
                  setIsDbDialogOpen(false);
                  setTestResult(null);
                  setDataSourceName('');
                  setCanSaveDataSource(false);
                  setFieldErrors({});
                }}
                variant="outline"
                className="bg-transparent border-white/20 hover:bg-white/5 text-gray-300 hover:text-white"
              >
                取消
              </Button>
              <Button
                onClick={handleAddDataSource}
                disabled={!canSaveDataSource}
                className="bg-purple-600 hover:bg-purple-500 text-white border-0 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                保存到列表
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}