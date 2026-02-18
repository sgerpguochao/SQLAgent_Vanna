import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Database, Table2, Search, Plus } from 'lucide-react';
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

interface DataSourcePanelProps {
  onTableSelect?: (tableName: string) => void;
}

export function DataSourcePanel({ onTableSelect }: DataSourcePanelProps) {
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

  useEffect(() => {
    loadDataSources();
  }, []);

  const loadDataSources = async () => {
    try {
      setLoading(true);
      // 从localStorage加载之前保存的数据源
      const savedSources = localStorage.getItem('dataSources');
      if (savedSources) {
        setDataSources(JSON.parse(savedSources));
      } else {
        setDataSources([]);
      }
    } catch (error) {
      console.error('加载数据源失败:', error);
      setDataSources([]);
    } finally {
      setLoading(false);
    }
  };

  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleTestConnection = async () => {
    try {
      setIsTestingConnection(true);
      setTestResult(null);
      console.log('测试数据库连接:', dbConfig);

      const response = await api.testDatabaseConnection(dbConfig);
      setTestResult({
        success: response.success,
        message: response.message
      });
    } catch (error) {
      console.error('测试连接失败:', error);
      setTestResult({
        success: false,
        message: '连接失败: ' + (error as Error).message
      });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleConnectDatabase = async () => {
    try {
      console.log('连接数据库配置:', dbConfig);
      const response = await api.connectDatabase(dbConfig);

      if (response.success) {
        console.log('数据库连接响应:', response);

        // 将数据库表添加到数据源列表
        if (response.tables && response.tables.length > 0) {
          const newDataSources = response.tables.map((table: any) => ({
            name: table.name,
            table: table.name,
            rows: 0, // 可以从后端获取
            columns: table.children || [],
            description: `表 ${table.name}`,
            source: 'mysql',
            children: table.children // 保留原始children数据
          }));

          console.log('转换后的数据源:', newDataSources);

          // 替换数据源（清除之前的连接）
          setDataSources(newDataSources);

          // 保存到localStorage
          localStorage.setItem('dataSources', JSON.stringify(newDataSources));
        }

        setIsDbDialogOpen(false);
        setTestResult(null);

        // 如果有表,自动选中第一个表并展开
        if (response.tables && response.tables.length > 0) {
          const firstTable = response.tables[0].name;
          setSelectedTable(firstTable);

          // 展开"数据库表"节点
          setExpandedNodes(new Set(['数据库表']));

          if (onTableSelect) {
            onTableSelect(firstTable);
          }
        }
      } else {
        alert('连接失败: ' + response.message);
      }
    } catch (error) {
      console.error('连接数据库失败:', error);
      alert('连接失败: ' + (error as Error).message);
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

  const convertToTableNodes = (sources: DataSource[]): TableNode[] => {
    // 按source分组
    const grouped = sources.reduce((acc, source) => {
      const category = source.source === 'upload' ? '上传的文件' : '数据库表';
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

  const filteredDataSources = convertToTableNodes(dataSources).filter(ds =>
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
      {/* Header with Add Button */}
      <div className="px-4 py-3 border-b border-white/5 flex-shrink-0 flex items-center justify-between">
        <h2 className="text-cyan-400 font-medium text-sm">数据库</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsDbDialogOpen(true)}
            className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center transition-all group"
            title="添加数据库"
          >
            <Plus className="w-4 h-4 text-gray-400 group-hover:text-cyan-400" />
          </button>
          <button
            className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center transition-all group"
            title="更多选项"
          >
            <svg className="w-4 h-4 text-gray-400 group-hover:text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="px-3 py-3 border-b border-white/5">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
          <Input
            placeholder="搜索表或段..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9 bg-[#13152E] border-white/5 text-gray-300 placeholder-gray-600 text-sm rounded-lg focus:border-cyan-500/30"
          />
        </div>
      </div>

      {/* Data Sources List */}
      <div className="flex-1 overflow-y-auto min-h-0 px-2 py-2">
        {/* Table Tree */}
        <div className="space-y-1">
          {filteredDataSources.map(ds => renderTreeNode(ds, 0))}
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
            {/* Host */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">主机地址</label>
              <input
                type="text"
                value={dbConfig.host}
                onChange={(e) => setDbConfig({ ...dbConfig, host: e.target.value })}
                className="w-full bg-[#1a1d2e] border border-white/10 text-gray-200 h-10 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500/30"
                placeholder="localhost"
              />
            </div>

            {/* Port */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">端口</label>
              <input
                type="text"
                value={dbConfig.port}
                onChange={(e) => setDbConfig({ ...dbConfig, port: e.target.value })}
                className="w-full bg-[#1a1d2e] border border-white/10 text-gray-200 h-10 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500/30"
                placeholder="3306"
              />
            </div>

            {/* Username */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">用户名</label>
              <input
                type="text"
                value={dbConfig.username}
                onChange={(e) => setDbConfig({ ...dbConfig, username: e.target.value })}
                className="w-full bg-[#1a1d2e] border border-white/10 text-gray-200 h-10 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500/30"
                placeholder="root"
              />
            </div>

            {/* Password */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">密码</label>
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
              <label className="text-sm text-gray-400 mb-2 block">数据库名称（可选）</label>
              <input
                type="text"
                value={dbConfig.database}
                onChange={(e) => setDbConfig({ ...dbConfig, database: e.target.value })}
                className="w-full bg-[#1a1d2e] border border-white/10 text-gray-200 h-10 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500/30"
                placeholder="留空则显示所有数据库"
              />
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
              disabled={isTestingConnection}
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
                }}
                variant="outline"
                className="bg-transparent border-white/20 hover:bg-white/5 text-gray-300 hover:text-white"
              >
                取消
              </Button>
              <Button
                onClick={handleConnectDatabase}
                className="bg-purple-600 hover:bg-purple-500 text-white border-0"
              >
                保存
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}