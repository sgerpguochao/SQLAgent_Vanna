import React, { useState } from 'react';
import { Plus, RotateCw, Undo, Search, ChevronRight, Database, X } from 'lucide-react';
import { Input } from './ui/input';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';

interface DatabaseType {
  id: string;
  name: string;
  icon: string;
  color: string;
}

const databaseTypes: DatabaseType[] = [
  { id: 'mysql', name: 'MySQL', icon: '🐬', color: 'text-blue-400' },
  { id: 'oracle', name: 'Oracle', icon: '🔴', color: 'text-red-400' },
  { id: 'postgresql', name: 'PostgreSql', icon: '🐘', color: 'text-blue-300' },
  { id: 'sqlserver', name: 'SQLServer', icon: '🟥', color: 'text-red-500' },
  { id: 'mariadb', name: 'Mariadb', icon: '🌊', color: 'text-cyan-400' },
  { id: 'clickhouse', name: 'ClickHouse', icon: '⚡', color: 'text-yellow-400' },
  { id: 'dm', name: 'DM', icon: '💎', color: 'text-pink-400' },
  { id: 'presto', name: 'Presto', icon: '🔷', color: 'text-blue-500' },
  { id: 'db2', name: 'DB2', icon: '🟢', color: 'text-green-600' },
  { id: 'oceanbase', name: 'OceanBase', icon: '🌊', color: 'text-cyan-500' },
  { id: 'oceanbase-oracle', name: 'OceanBase Oracle', icon: '🌊', color: 'text-cyan-600' },
  { id: 'sqlite', name: 'SQLite', icon: '💾', color: 'text-blue-400' },
  { id: 'h2', name: 'H2', icon: '💧', color: 'text-blue-500' },
  { id: 'hive', name: 'Hive', icon: '🐝', color: 'text-yellow-500' },
  { id: 'kingbase', name: 'Kingbase', icon: '👑', color: 'text-purple-500' },
];

interface DatabaseConnectionPanelProps {
  onTableSelect?: (tableName: string) => void;
}

export function DatabaseConnectionPanel({ onTableSelect }: DatabaseConnectionPanelProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [isConnectionDialogOpen, setIsConnectionDialogOpen] = useState(false);
  const [selectedDbType, setSelectedDbType] = useState<string | null>(null);
  const [connectionForm, setConnectionForm] = useState({
    name: '@localhost',
    environment: 'TEST',
    storage: 'CLOUD',
    host: 'localhost',
    port: '3306',
    authMethod: 'User&Password',
    username: 'root',
    password: '',
    database: '',
    url: 'jdbc:mysql://localhost:3306',
    driver: 'mysql-connector-java-8.0.30.jar',
    driverClass: 'com.mysql.cj.jdbc.Driver',
  });

  const filteredDatabases = databaseTypes.filter(db =>
    db.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDatabaseTypeClick = (dbType: DatabaseType) => {
    setSelectedDbType(dbType.id);
    setIsConnectionDialogOpen(true);
    // 根据数据库类型设置默认值
    if (dbType.id === 'mysql') {
      setConnectionForm(prev => ({
        ...prev,
        port: '3306',
        url: 'jdbc:mysql://localhost:3306',
        driver: 'mysql-connector-java-8.0.30.jar',
        driverClass: 'com.mysql.cj.jdbc.Driver',
      }));
    } else if (dbType.id === 'postgresql') {
      setConnectionForm(prev => ({
        ...prev,
        port: '5432',
        url: 'jdbc:postgresql://localhost:5432',
        driver: 'postgresql-42.5.0.jar',
        driverClass: 'org.postgresql.Driver',
      }));
    }
    // 可以为其他数据库类型添加更多默认配置
  };

  const handleTestConnection = () => {
    // TODO: 实现测试连接逻辑
    console.log('测试连接:', connectionForm);
  };

  const handleSaveConnection = () => {
    // TODO: 实现保存连接逻辑
    console.log('保存连接:', connectionForm);
    setIsConnectionDialogOpen(false);
  };

  return (
    <div className="h-full flex flex-col bg-[#0B0D1E] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="text-cyan-400 font-medium text-sm">数据库</h2>
          <div className="flex gap-1">
            <button
              onClick={() => setIsConnectionDialogOpen(true)}
              className="p-1 hover:bg-white/5 rounded transition-colors"
              title="新建组"
            >
              <Plus className="w-4 h-4 text-gray-400" />
            </button>
            <button className="p-1 hover:bg-white/5 rounded transition-colors" title="刷新">
              <RotateCw className="w-4 h-4 text-gray-400" />
            </button>
            <button className="p-1 hover:bg-white/5 rounded transition-colors" title="撤销">
              <Undo className="w-4 h-4 text-gray-400" />
            </button>
            <button className="p-1 hover:bg-white/5 rounded transition-colors">
              <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 16 16">
                <circle cx="8" cy="4" r="1.5"/>
                <circle cx="8" cy="8" r="1.5"/>
                <circle cx="8" cy="12" r="1.5"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="px-3 py-3 border-b border-white/5">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
          <Input
            placeholder="搜索"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-8 bg-[#13152E] border-white/5 text-gray-300 placeholder-gray-600 text-xs rounded-lg focus:border-cyan-500/30"
          />
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-xs text-gray-600">
            ⌘F
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="px-3 py-2 space-y-2">
        <button
          onClick={() => setIsConnectionDialogOpen(true)}
          className="w-full flex items-center gap-2 px-3 py-2 bg-[#13152E] hover:bg-white/5 rounded-lg border border-white/5 transition-colors text-left"
        >
          <Plus className="w-4 h-4 text-cyan-400" />
          <span className="text-xs text-gray-300">新建组</span>
        </button>
        <button className="w-full flex items-center gap-2 px-3 py-2 bg-[#13152E] hover:bg-white/5 rounded-lg border border-white/5 transition-colors text-left">
          <Database className="w-4 h-4 text-blue-400" />
          <span className="text-xs text-gray-300">新建连接</span>
          <ChevronRight className="w-3 h-3 text-gray-500 ml-auto" />
        </button>
        <button className="w-full flex items-center gap-2 px-3 py-2 bg-[#13152E] hover:bg-white/5 rounded-lg border border-white/5 transition-colors text-left">
          <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <span className="text-xs text-gray-300">导入连接</span>
        </button>
      </div>

      {/* Database List - Empty State */}
      <div className="flex-1 overflow-y-auto px-3 py-8">
        <div className="flex flex-col items-center justify-center text-center">
          <div className="w-24 h-24 mb-4 opacity-20">
            <svg viewBox="0 0 100 100" className="text-gray-500">
              <path fill="currentColor" d="M50 10 L50 30 M30 25 L50 10 L70 25 M20 30 Q20 35 30 35 L70 35 Q80 35 80 30 M20 30 L20 50 M80 30 L80 50 M20 50 Q20 55 30 55 L70 55 Q80 55 80 50 M20 50 L20 70 M80 50 L80 70 M20 70 Q20 75 30 75 L70 75 Q80 75 80 70" stroke="currentColor" strokeWidth="2" fill="none"/>
            </svg>
          </div>
          <p className="text-gray-500 text-xs">你还没有创建连接</p>
        </div>
      </div>

      {/* Connection Dialog */}
      <Dialog open={isConnectionDialogOpen} onOpenChange={setIsConnectionDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] bg-[#1a1d3e] border-white/10 text-gray-200 overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle className="text-xl text-white flex items-center gap-2">
                {selectedDbType && (
                  <>
                    <span className="text-2xl">
                      {databaseTypes.find(db => db.id === selectedDbType)?.icon}
                    </span>
                    <span>{databaseTypes.find(db => db.id === selectedDbType)?.name}</span>
                  </>
                )}
                {!selectedDbType && '选择数据库类型'}
              </DialogTitle>
              <button
                onClick={() => setIsConnectionDialogOpen(false)}
                className="p-1 hover:bg-white/10 rounded transition-colors"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
          </DialogHeader>

          {!selectedDbType ? (
            /* Database Type Selection */
            <div className="mt-4">
              <div className="grid grid-cols-4 gap-3">
                {filteredDatabases.map((db) => (
                  <button
                    key={db.id}
                    onClick={() => handleDatabaseTypeClick(db)}
                    className="flex flex-col items-center gap-2 p-4 bg-[#13152E] hover:bg-white/5 rounded-lg border border-white/5 hover:border-cyan-500/30 transition-all"
                  >
                    <span className="text-3xl">{db.icon}</span>
                    <span className={`text-sm ${db.color}`}>{db.name}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Connection Form */
            <div className="mt-4 space-y-4 overflow-y-auto pr-2" style={{ maxHeight: 'calc(90vh - 120px)' }}>
              {/* Name */}
              <div>
                <label className="text-sm text-gray-400 mb-2 block">名称</label>
                <Input
                  value={connectionForm.name}
                  onChange={(e) => setConnectionForm({ ...connectionForm, name: e.target.value })}
                  className="bg-[#13152E] border-white/10 text-gray-200"
                  placeholder="@localhost"
                />
              </div>

              {/* Environment and Storage */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-400 mb-2 block">环境</label>
                  <select
                    value={connectionForm.environment}
                    onChange={(e) => setConnectionForm({ ...connectionForm, environment: e.target.value })}
                    className="w-full h-10 px-3 bg-[#13152E] border border-white/10 rounded-md text-gray-200 text-sm"
                  >
                    <option value="TEST">TEST</option>
                    <option value="DEV">DEV</option>
                    <option value="PROD">PROD</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-gray-400 mb-2 block">存储</label>
                  <select
                    value={connectionForm.storage}
                    onChange={(e) => setConnectionForm({ ...connectionForm, storage: e.target.value })}
                    className="w-full h-10 px-3 bg-[#13152E] border border-white/10 rounded-md text-gray-200 text-sm"
                  >
                    <option value="CLOUD">CLOUD</option>
                    <option value="LOCAL">LOCAL</option>
                  </select>
                </div>
              </div>

              {/* Host and Port */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-400 mb-2 block">主机</label>
                  <Input
                    value={connectionForm.host}
                    onChange={(e) => setConnectionForm({ ...connectionForm, host: e.target.value })}
                    className="bg-[#13152E] border-white/10 text-gray-200"
                    placeholder="localhost"
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400 mb-2 block">端口</label>
                  <Input
                    value={connectionForm.port}
                    onChange={(e) => setConnectionForm({ ...connectionForm, port: e.target.value })}
                    className="bg-[#13152E] border-white/10 text-gray-200"
                    placeholder="3306"
                  />
                </div>
              </div>

              {/* Authentication Method */}
              <div>
                <label className="text-sm text-gray-400 mb-2 block">身份验证</label>
                <select
                  value={connectionForm.authMethod}
                  onChange={(e) => setConnectionForm({ ...connectionForm, authMethod: e.target.value })}
                  className="w-full h-10 px-3 bg-[#13152E] border border-white/10 rounded-md text-gray-200 text-sm"
                >
                  <option value="User&Password">User&Password</option>
                  <option value="None">None</option>
                </select>
              </div>

              {/* Username and Password */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-400 mb-2 block">用户名</label>
                  <Input
                    value={connectionForm.username}
                    onChange={(e) => setConnectionForm({ ...connectionForm, username: e.target.value })}
                    className="bg-[#13152E] border-white/10 text-gray-200"
                    placeholder="root"
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400 mb-2 block">密码</label>
                  <Input
                    type="password"
                    value={connectionForm.password}
                    onChange={(e) => setConnectionForm({ ...connectionForm, password: e.target.value })}
                    className="bg-[#13152E] border-white/10 text-gray-200"
                    placeholder="••••••"
                  />
                </div>
              </div>

              {/* Database */}
              <div>
                <label className="text-sm text-gray-400 mb-2 block">数据库</label>
                <Input
                  value={connectionForm.database}
                  onChange={(e) => setConnectionForm({ ...connectionForm, database: e.target.value })}
                  className="bg-[#13152E] border-white/10 text-gray-200"
                  placeholder="数据库名称（可选）"
                />
              </div>

              {/* URL */}
              <div>
                <label className="text-sm text-gray-400 mb-2 block">URL</label>
                <Input
                  value={connectionForm.url}
                  onChange={(e) => setConnectionForm({ ...connectionForm, url: e.target.value })}
                  className="bg-[#13152E] border-white/10 text-gray-200"
                  placeholder="jdbc:mysql://localhost:3306"
                />
              </div>

              {/* Driver Section */}
              <div className="border border-white/10 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm text-gray-300">驱动</span>
                  <button className="text-xs text-cyan-400 hover:text-cyan-300">展开</button>
                </div>

                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">驱动</label>
                    <select
                      value={connectionForm.driver}
                      onChange={(e) => setConnectionForm({ ...connectionForm, driver: e.target.value })}
                      className="w-full h-9 px-3 bg-[#13152E] border border-white/10 rounded-md text-gray-200 text-xs"
                    >
                      <option value="mysql-connector-java-8.0.30.jar">mysql-connector-java-8.0.30.jar</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">Class</label>
                    <Input
                      value={connectionForm.driverClass}
                      onChange={(e) => setConnectionForm({ ...connectionForm, driverClass: e.target.value })}
                      className="bg-[#13152E] border-white/10 text-gray-200 h-9 text-xs"
                      placeholder="com.mysql.cj.jdbc.Driver"
                    />
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4 sticky bottom-0 bg-[#1a1d3e] pb-2">
                <Button
                  onClick={handleTestConnection}
                  variant="outline"
                  className="flex-1 bg-white/5 border-white/10 hover:bg-white/10 text-gray-200"
                >
                  测试连接
                </Button>
                <Button
                  onClick={handleSaveConnection}
                  className="flex-1 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white"
                >
                  保存
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
