import React, { useState } from 'react';
import { DataSourcePanel } from './DataSourcePanel';
import { TrainingDataPanel } from './TrainingDataPanel';
import { QueryPanel } from './QueryPanel';
import { ResultsPanel } from './ResultsPanel';
import { ChatPanel } from './ChatPanel';
import { Toaster } from './ui/sonner';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { Database, BookOpen } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [selectedDatabase, setSelectedDatabase] = useState<string | null>(null);
  const [queryResult, setQueryResult] = useState<any>(null);
  const [leftPanelTab, setLeftPanelTab] = useState<'datasource' | 'training'>('datasource');

  const handleTableSelect = (tableName: string) => {
    setSelectedTable(tableName);
    console.log('选中表:', tableName);
  };

  const handleDatabaseSelect = (dbName: string) => {
    setSelectedDatabase(dbName);
    console.log('选中数据库:', dbName);
  };

  const handleQueryResult = (result: any) => {
    setQueryResult(result);
    if (result.success) {
      toast.success('查询执行成功', {
        description: `返回 ${result.returned_rows || result.data?.length || 0} 条结果`,
      });
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[#0B0D1E] text-gray-100">
      {/* Header */}
      <div className="h-16 border-b border-white/5 bg-[#0B0D1E] flex items-center px-6 flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 hover:scale-105 transition-transform cursor-pointer"
          >
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </button>
          <h1 className="text-lg font-semibold">
            <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
              SQL Agent 数据分析系统
            </span>
          </h1>
        </div>
        <div className="ml-auto flex items-center gap-4">
          {selectedDatabase && (
            <div className="text-sm text-gray-400">
              当前数据库: <span className="text-cyan-400">{selectedDatabase}</span>
            </div>
          )}
          <button className="px-5 py-2 rounded-lg bg-gradient-to-r from-cyan-500/20 to-blue-600/20 hover:from-cyan-500/30 hover:to-blue-600/30 border border-cyan-500/30 transition-all text-cyan-300 font-medium text-sm">
            系统设置
          </button>
        </div>
      </div>

      {/* Main Content - Three Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Data Sources / Training Data */}
        <div className="w-[280px] flex-shrink-0 border-r border-white/5 bg-[#0B0D1E] flex flex-col">
          {/* Tab Switcher */}
          <div className="flex border-b border-white/5 bg-[#0B0D1E]">
            <button
              onClick={() => setLeftPanelTab('datasource')}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                leftPanelTab === 'datasource'
                  ? 'text-cyan-400 border-b-2 border-cyan-400 bg-[#13152E]'
                  : 'text-gray-400 hover:text-gray-300 hover:bg-[#13152E]'
              }`}
            >
              <Database className="w-4 h-4" />
              数据源
            </button>
            <button
              onClick={() => setLeftPanelTab('training')}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                leftPanelTab === 'training'
                  ? 'text-emerald-400 border-b-2 border-emerald-400 bg-[#13152E]'
                  : 'text-gray-400 hover:text-gray-300 hover:bg-[#13152E]'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              训练数据
            </button>
          </div>

          {/* Panel Content */}
          <div className="flex-1 min-h-0 overflow-hidden">
            {leftPanelTab === 'datasource' ? (
              <DataSourcePanel onTableSelect={handleTableSelect} onDatabaseSelect={handleDatabaseSelect} />
            ) : (
              /* Training Data Quick Info Panel */
              <div className="p-4 space-y-4">
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-emerald-400">快速指南</h3>

                  <div className="space-y-2 text-xs text-gray-400">
                    <div className="bg-[#13152E] rounded-lg p-3 border border-emerald-500/20">
                      <div className="font-medium text-emerald-400 mb-2">📘 什么是训练数据？</div>
                      <p className="leading-relaxed">
                        训练数据用于提升 AI 生成 SQL 的准确度，包括示例查询、表结构定义和表文档。
                      </p>
                    </div>

                    <div className="bg-[#13152E] rounded-lg p-3 border border-blue-500/20">
                      <div className="font-medium text-blue-400 mb-2">🔵 SQL 查询</div>
                      <p className="leading-relaxed">
                        提供业务问题和对应的 SQL 语句，帮助 AI 学习如何将自然语言转换为 SQL。
                      </p>
                    </div>

                    <div className="bg-[#13152E] rounded-lg p-3 border border-purple-500/20">
                      <div className="font-medium text-purple-400 mb-2">🟣 DDL 结构</div>
                      <p className="leading-relaxed">
                        提供 CREATE TABLE 语句，让 AI 了解表的结构、字段类型和约束。
                      </p>
                    </div>

                    <div className="bg-[#13152E] rounded-lg p-3 border border-green-500/20">
                      <div className="font-medium text-green-400 mb-2">🟢 表文档</div>
                      <p className="leading-relaxed">
                        提供表的业务含义、字段说明等文档，帮助 AI 理解数据的业务含义。
                      </p>
                    </div>
                  </div>
                </div>

                <div className="border-t border-white/5 pt-4">
                  <h3 className="text-sm font-semibold text-gray-400 mb-3">数据统计</h3>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between items-center text-gray-400">
                      <span>当前数据库:</span>
                      <span className="text-cyan-400 font-medium">MySQL</span>
                    </div>
                    <div className="flex justify-between items-center text-gray-400">
                      <span>向量数据库:</span>
                      <span className="text-cyan-400 font-medium">Milvus</span>
                    </div>
                    <div className="flex justify-between items-center text-gray-400">
                      <span>嵌入模型:</span>
                      <span className="text-cyan-400 font-medium">Jina</span>
                    </div>
                  </div>
                </div>

                <div className="border-t border-white/5 pt-4">
                  <h3 className="text-sm font-semibold text-gray-400 mb-3">最佳实践</h3>
                  <div className="space-y-2 text-xs text-gray-500">
                    <div className="flex items-start gap-2">
                      <span className="text-emerald-400 mt-0.5">✓</span>
                      <span>添加常见业务查询的示例</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="text-emerald-400 mt-0.5">✓</span>
                      <span>包含所有表的 DDL 定义</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="text-emerald-400 mt-0.5">✓</span>
                      <span>提供详细的表和字段文档</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="text-emerald-400 mt-0.5">✓</span>
                      <span>定期更新和维护训练数据</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Conditional Content Based on Tab */}
        {leftPanelTab === 'datasource' ? (
          <>
            {/* Center Panel - SQL Editor + Results */}
            <div className="flex-1 min-w-0 flex flex-col bg-[#0F1123]">
              {/* Top: SQL Editor */}
              <div className="flex-shrink-0">
                <QueryPanel
                  selectedTable={selectedTable}
                  selectedDatabase={selectedDatabase}
                  onQueryResult={handleQueryResult}
                />
              </div>

              {/* Bottom: Results Table */}
              <div className="flex-1 min-h-0 overflow-hidden border-t border-white/5">
                <ResultsPanel queryResult={queryResult} />
              </div>
            </div>

            {/* Right Panel - Chat/Q&A */}
            <div className="w-[380px] flex-shrink-0 border-l border-white/5 bg-[#0B0D1E]">
              <ChatPanel selectedTable={selectedTable} onQueryResult={handleQueryResult} />
            </div>
          </>
        ) : (
          /* Full Width Training Data Management Panel */
          <div className="flex-1 min-w-0 bg-[#0B0D1E]">
            <TrainingDataPanel />
          </div>
        )}
      </div>

      <Toaster
        theme="dark"
        position="top-right"
        toastOptions={{
          style: {
            background: '#1a1b3e',
            border: '1px solid rgba(92, 225, 230, 0.2)',
            color: '#e5e7eb',
          },
        }}
      />
    </div>
  );
};
