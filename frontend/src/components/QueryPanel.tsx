import React, { useState, useEffect } from 'react';
import { Play, FileText, ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import { api } from '../services/api';

interface QueryPanelProps {
  selectedTable?: string | null;
  onQueryResult?: (result: any) => void;
}

export function QueryPanel({ selectedTable, onQueryResult }: QueryPanelProps) {
  const [showSQL, setShowSQL] = useState(false);
  const [generatedSQL, setGeneratedSQL] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [sqlQuery, setSqlQuery] = useState('SELECT * FROM table_name LIMIT 10;');

  // 当选中的表变化时，更新SQL
  useEffect(() => {
    if (selectedTable) {
      // 如果是上传的文件（file_开头），提取 file_id
      if (selectedTable.startsWith('file_')) {
        setSelectedFileId(selectedTable.replace('file_', ''));
        setSqlQuery('SELECT * FROM uploaded_file LIMIT 10;');
      } else {
        setSelectedFileId(null);
        setSqlQuery(`SELECT * FROM ${selectedTable} LIMIT 10;`);
      }
    }
  }, [selectedTable]);

  const handleRun = async () => {
    if (!selectedTable) {
      alert('请先在左侧选择一个数据表');
      return;
    }

    if (!sqlQuery.trim()) {
      alert('请输入SQL查询语句');
      return;
    }

    console.log('[SQL查询] 开始执行:', { sql: sqlQuery, selectedTable, selectedFileId });
    setIsQuerying(true);
    try {
      const request: any = { sql: sqlQuery };

      // 如果是上传的文件，传递 file_id；否则传递 table_name
      if (selectedFileId) {
        request.file_id = selectedFileId;
      } else {
        request.table_name = selectedTable;
      }

      const result = await api.queryData(request);

      console.log('[查询结果]:', result);

      // 保存生成的SQL（用于展示）
      if (result.sql) {
        setGeneratedSQL(result.sql);
      }

      // 传递结果给父组件
      if (onQueryResult) {
        onQueryResult(result);
      }
    } catch (error) {
      console.error('查询失败:', error);
      alert('查询失败: ' + error);
    } finally {
      setIsQuerying(false);
    }
  };

  return (
    <div className="flex flex-col bg-[#0F1123]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-400" />
            <h2 className="text-cyan-400 font-medium text-sm">SQL 编辑器</h2>
          </div>
          {selectedTable && (
            <span className="text-xs text-gray-500">
              当前表: <span className="text-cyan-400">{selectedTable}</span>
            </span>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="px-4 py-3 flex-shrink-0">
        <div className="space-y-2">
          <Textarea
            placeholder={selectedTable ? `输入SQL查询，例如：SELECT * FROM ${selectedTable} LIMIT 10;` : "请先在左侧选择一个数据表..."}
            value={sqlQuery}
            onChange={(e) => setSqlQuery(e.target.value)}
            disabled={!selectedTable}
            className="min-h-[100px] bg-[#13152E] border-white/10 text-gray-300 placeholder-gray-600 resize-none focus:border-cyan-500/30 font-mono text-sm"
          />

          <div className="flex justify-end items-center">
            <Button
              onClick={handleRun}
              disabled={!selectedTable || !sqlQuery.trim() || isQuerying}
              size="sm"
              className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20"
            >
              {isQuerying ? (
                <>正在执行...</>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  执行 SQL
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
