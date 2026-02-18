import React, { useState } from 'react';
import { Database, MessageSquare } from 'lucide-react';
import { DatabaseConnectionPanel } from './DatabaseConnectionPanel';
import { DataSourcePanel } from './DataSourcePanel';

interface UnifiedSidePanelProps {
  onTableSelect?: (tableName: string) => void;
}

type PanelView = 'database' | 'chat';

export function UnifiedSidePanel({ onTableSelect }: UnifiedSidePanelProps) {
  const [activeView, setActiveView] = useState<PanelView>('database');

  return (
    <div className="h-full flex">
      {/* Left Sidebar - Navigation Icons */}
      <div className="w-[60px] bg-[#1a1d3e] border-r border-white/5 flex flex-col items-center py-4 gap-2">
        {/* User Avatar */}
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-4">
          <span className="text-white text-sm font-semibold">小</span>
        </div>

        {/* Database Icon */}
        <button
          onClick={() => setActiveView('database')}
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all ${
            activeView === 'database'
              ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
              : 'bg-[#13152E] text-gray-400 hover:bg-white/5 hover:text-gray-300'
          }`}
          title="数据库"
        >
          <Database className="w-5 h-5" />
        </button>

        {/* AI Chat Icon */}
        <button
          onClick={() => setActiveView('chat')}
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all ${
            activeView === 'chat'
              ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
              : 'bg-[#13152E] text-gray-400 hover:bg-white/5 hover:text-gray-300'
          }`}
          title="AI 对话"
        >
          <MessageSquare className="w-5 h-5" />
        </button>

        {/* Additional Icons (matching the screenshot) */}
        <button
          className="w-10 h-10 rounded-lg bg-[#13152E] text-gray-400 hover:bg-white/5 hover:text-gray-300 flex items-center justify-center transition-all"
          title="图表"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </button>

        <button
          className="w-10 h-10 rounded-lg bg-[#13152E] text-gray-400 hover:bg-white/5 hover:text-gray-300 flex items-center justify-center transition-all"
          title="工具"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
        </button>

        <button
          className="w-10 h-10 rounded-lg bg-[#13152E] text-gray-400 hover:bg-white/5 hover:text-gray-300 flex items-center justify-center transition-all"
          title="文档"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </button>
      </div>

      {/* Right Content Area */}
      <div className="flex-1 bg-[#0B0D1E]">
        {activeView === 'database' ? (
          <DataSourcePanel onTableSelect={onTableSelect} />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-4">
            <MessageSquare className="w-16 h-16 text-gray-600 mb-4" />
            <p className="text-gray-500 text-sm">AI 对话功能</p>
            <p className="text-gray-600 text-xs mt-2">即将推出</p>
          </div>
        )}
      </div>
    </div>
  );
}
