import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, Loader2, CheckCircle, Clock, ChevronDown, ChevronRight, BarChart3, FileText, Hash, TableIcon, Database, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, ScatterChart, Scatter } from 'recharts';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from '../services/api';
import { QueryResultDisplay } from './QueryResultDisplay';
import { getApiUrl, API_ENDPOINTS } from '../config';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

interface ChatPanelProps {
  selectedTable?: string | null;
  selectedDatabase?: string | null;
  onQueryResult?: (result: any) => void;
}

interface ThinkingStep {
  action: string;
  status: '准备中' | '进行中' | '完成';
  duration_ms?: number;
  tool_name?: string;
  result?: string;  // 工具执行结果
  sql?: string;     // SQL 语句（execute_sql 工具使用）
}

export function ChatPanel({ selectedTable, selectedDatabase, onQueryResult }: ChatPanelProps) {
  const [query, setQuery] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);
  const [answer, setAnswer] = useState('');
  const [showThinking, setShowThinking] = useState(false);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);  // 默认折叠
  const [expandedStepIndex, setExpandedStepIndex] = useState<number | null>(null);  // 当前展开的步骤
  const [chartConfig, setChartConfig] = useState<any>(null);  // Chart.js 配置对象
  const [queryData, setQueryData] = useState<any>(null);  // 查询数据
  const [chatDbName, setChatDbName] = useState<string>('');  // 对话选择的数据库
  const [databaseList, setDatabaseList] = useState<string[]>([]);  // 已连接的数据库列表
  const [isRefreshingDb, setIsRefreshingDb] = useState(false);  // 刷新数据库列表中
  const abortControllerRef = useRef<AbortController | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);  // 聊天容器引用，用于自动滚动

  // 刷新数据库列表
  const refreshDatabaseList = async () => {
    setIsRefreshingDb(true);
    try {
      const result = await api.getConnectedDatabases();
      if (result.success && result.databases) {
        const newList = result.databases;
        setDatabaseList(newList);
        // 如果当前选择的数据库不在新列表中，自动选中第一个
        if (newList.length > 0 && !newList.includes(chatDbName)) {
          setChatDbName(newList[0]);
        }
      }
    } catch (e) {
      console.error('刷新数据库列表失败:', e);
    } finally {
      setIsRefreshingDb(false);
    }
  };

  // 示例问题模板
  const exampleQuestions = [
    '销售额最高的前10个产品',
    '好评率超过95%且销量过万的产品',
    '各品牌在智能手机分类中的销量对比',
    '折扣率>30%且价格<5000的性价比产品',
    '显示前10条数据',
    '统计各类别的平均价格'
  ];

  // 当选中的表变化时，更新提示
  useEffect(() => {
    if (selectedTable) {
      // 如果是上传的文件（file_开头），提取 file_id
      if (selectedTable.startsWith('file_')) {
        setSelectedFileId(selectedTable.replace('file_', ''));
        setQuery('');
      } else {
        setSelectedFileId(null);
        setQuery('');
      }
    }
  }, [selectedTable]);

  // 当 answer 更新时，自动滚动到底部
  useEffect(() => {
    if (answer && chatContainerRef.current) {
      // 使用 setTimeout 确保 DOM 渲染完成后再滚动
      setTimeout(() => {
        if (chatContainerRef.current) {
          chatContainerRef.current.scrollTo({
            top: chatContainerRef.current.scrollHeight,
            behavior: 'smooth'
          });
        }
      }, 100);
    }
  }, [answer]);

  // 当 thinkingSteps 更新时，自动滚动到底部
  useEffect(() => {
    if (thinkingSteps.length > 0 && chatContainerRef.current) {
      setTimeout(() => {
        if (chatContainerRef.current) {
          chatContainerRef.current.scrollTo({
            top: chatContainerRef.current.scrollHeight,
            behavior: 'smooth'
          });
        }
      }, 100);
    }
  }, [thinkingSteps]);

  // 当 queryData 更新时，自动滚动到底部
  useEffect(() => {
    if (queryData && chatContainerRef.current) {
      setTimeout(() => {
        if (chatContainerRef.current) {
          chatContainerRef.current.scrollTo({
            top: chatContainerRef.current.scrollHeight,
            behavior: 'smooth'
          });
        }
      }, 100);
    }
  }, [queryData]);

  // 加载数据库列表
  useEffect(() => {
    const loadDatabases = async () => {
      try {
        const result = await api.getConnectedDatabases();
        if (result.success && result.databases) {
          setDatabaseList(result.databases);
          // 如果有数据库且当前没有选中，自动选中第一个
          if (result.databases.length > 0 && !chatDbName) {
            setChatDbName(result.databases[0]);
          }
        }
      } catch (e) {
        console.error('从后端获取数据库列表失败:', e);
        // 降级到从 localStorage 获取
        try {
          const configs = localStorage.getItem('dataSourceConfigs');
          if (configs) {
            const parsed = JSON.parse(configs);
            const dbList = parsed.map((c: any) => c.database).filter(Boolean);
            setDatabaseList([...new Set(dbList)]);
          }
        } catch (e2) {
          console.error('读取数据库列表失败:', e2);
        }
      }
    };
    loadDatabases();
  }, []);

  // 当 selectedDatabase 变化时，更新 chatDbName
  useEffect(() => {
    if (selectedDatabase) {
      setChatDbName(selectedDatabase);
    }
  }, [selectedDatabase]);

  const handleSend = async () => {
    if (!query.trim()) {
      alert('请输入您的问题');
      return;
    }

    console.log('[流式对话] 开始查询:', { query });

    // 重置状态
    setIsQuerying(true);
    setThinkingSteps([]);
    setAnswer('');
    setQueryData(null);
    setChartConfig(null);
    setShowThinking(true);

    // 创建新的 AbortController
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(getApiUrl(API_ENDPOINTS.CHAT_STREAM), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: query.trim(),
          db_name: chatDbName || undefined,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('无法读取响应流');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));

            if (data.type === 'step') {
              // 处理思考步骤
              setThinkingSteps(prev => {
                if (data.update) {
                  // 更新最后一个步骤
                  const newSteps = [...prev];
                  if (newSteps.length > 0) {
                    newSteps[newSteps.length - 1] = {
                      action: data.action,
                      status: data.status,
                      duration_ms: data.duration_ms,
                      tool_name: data.tool_name,
                      result: data.result,  // 保存工具执行结果
                      sql: data.sql,  // 保存 SQL 语句
                    };
                  }
                  return newSteps;
                } else {
                  // 添加新步骤
                  return [...prev, {
                    action: data.action,
                    status: data.status,
                    duration_ms: data.duration_ms,
                    tool_name: data.tool_name,
                    result: data.result,  // 保存工具执行结果
                    sql: data.sql,  // 保存 SQL 语句
                  }];
                }
              });
            } else if (data.type === 'answer') {
              // 累加答案
              setAnswer(prev => prev + data.content);
            } else if (data.type === 'chart_config') {
              // 接收图表配置
              console.log('[图表配置] 收到图表配置事件:', data.config);
              setChartConfig(data.config);
            } else if (data.type === 'data') {
              // 接收查询数据
              console.log('[数据接收] 收到数据事件:', data);
              console.log('[数据接收] 数据行数:', data.data?.length);
              console.log('[数据接收] 列:', data.columns);

              const resultData = {
                success: true,
                data: data.data,
                columns: data.columns || Object.keys(data.data[0] || {}),
                returned_rows: data.data.length,
                sql: data.sql,
              };

              console.log('[数据接收] 格式化后的结果:', resultData);

              // 保存到本地状态用于图表展示
              setQueryData(resultData);
              console.log('[数据接收] ✓ queryData 已设置');

              // 也传递给父组件（ResultsPanel）
              if (onQueryResult) {
                onQueryResult(resultData);
                console.log('[数据接收] ✓ 已传递给父组件');
              }
            } else if (data.type === 'done') {
              // 完成
              console.log('[流式对话] 完成');
            } else if (data.type === 'error') {
              throw new Error(data.message);
            }
          }
        }
      }

      // 清空输入
      setQuery('');
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('[流式对话] 已取消');
      } else {
        console.error('查询失败:', error);
        alert('查询失败: ' + error.message);
      }
    } finally {
      setIsQuerying(false);
      abortControllerRef.current = null;
    }
  };

  const handleExampleClick = (question: string) => {
    setQuery(question);
  };

  return (
    <div ref={chatContainerRef} className="h-full flex flex-col bg-[#0B0D1E] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-purple-400" />
          <h2 className="text-purple-400 font-medium text-sm">AI 智能问答</h2>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto min-h-0 px-4 py-4 space-y-4">
        {/* Thinking Process */}
        {showThinking && thinkingSteps.length > 0 && (
          <Collapsible
            open={isThinkingExpanded}
            onOpenChange={setIsThinkingExpanded}
            className="bg-[#13152E] rounded-lg border border-purple-500/20"
          >
            <CollapsibleTrigger className="w-full px-3 py-2 flex items-center gap-3 hover:bg-white/5 transition-colors">
              <div className="flex items-center gap-2 flex-shrink-0">
                {isQuerying ? (
                  <Loader2 className="w-3.5 h-3.5 text-purple-400 animate-spin" />
                ) : (
                  <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                )}
                <span className="text-xs font-medium text-purple-300 whitespace-nowrap">
                  {isQuerying ? `AI 正在处理 (${thinkingSteps.length}步)` : `AI 处理完成 (${thinkingSteps.length}步)`}
                </span>
              </div>

              {/* 折叠状态下显示最新步骤 */}
              {!isThinkingExpanded && thinkingSteps.length > 0 && (
                <div className="flex items-center gap-2 text-xs text-gray-400 flex-1 min-w-0 mr-2">
                  {thinkingSteps[thinkingSteps.length - 1].status === '进行中' && (
                    <Loader2 className="w-3 h-3 text-cyan-400 animate-spin flex-shrink-0" />
                  )}
                  <span className="truncate">
                    {thinkingSteps[thinkingSteps.length - 1].action}
                  </span>
                </div>
              )}

              <div className="flex-shrink-0 ml-auto">
                {isThinkingExpanded ? (
                  <ChevronDown className="w-4 h-4 text-purple-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-purple-400" />
                )}
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent className="px-3 pb-3">
              <div className="pt-2 border-t border-white/5 space-y-2">
                {thinkingSteps.map((step, idx) => (
                  <div key={idx}>
                    <button
                      onClick={() => setExpandedStepIndex(expandedStepIndex === idx ? null : idx)}
                      className="w-full flex items-start gap-2 text-xs hover:bg-white/5 p-2 rounded transition-colors text-left"
                    >
                      <div className="flex-shrink-0 mt-0.5">
                        {step.status === '完成' ? (
                          <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                        ) : step.status === '进行中' ? (
                          <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
                        ) : (
                          <Clock className="w-3.5 h-3.5 text-gray-500" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-gray-300">{step.action}</p>
                          {step.result && (
                            expandedStepIndex === idx ? (
                              <ChevronDown className="w-3 h-3 text-gray-500" />
                            ) : (
                              <ChevronRight className="w-3 h-3 text-gray-500" />
                            )
                          )}
                        </div>
                        <div className="flex gap-3 mt-0.5">
                          {step.duration_ms && (
                            <p className="text-gray-600 text-xs">
                              耗时: {step.duration_ms.toFixed(0)}ms
                            </p>
                          )}
                          {step.tool_name && (
                            <p className="text-gray-600 text-xs">
                              工具: {step.tool_name}
                            </p>
                          )}
                        </div>
                      </div>
                    </button>
                    {/* 展开显示工具执行结果 */}
                    {expandedStepIndex === idx && step.result && (
                      <div className="ml-7 mt-1 p-2 bg-[#0D0F1A] rounded border border-white/5">
                        {/* 如果有 SQL 语句，先显示 SQL */}
                        {step.sql && (
                          <div className="mb-2">
                            <div className="flex items-center justify-between mb-1">
                              <p className="text-xs text-green-400">SQL 语句:</p>
                              <button
                                onClick={(e) => {
                                  e.preventDefault();
                                  const text = step.sql || '';
                                  if (text) {
                                    // 创建临时 textarea 复制
                                    const textarea = document.createElement('textarea');
                                    textarea.value = text;
                                    textarea.style.position = 'fixed';
                                    textarea.style.opacity = '0';
                                    document.body.appendChild(textarea);
                                    textarea.select();
                                    try {
                                      document.execCommand('copy');
                                      alert('复制成功');
                                    } catch {
                                      alert('复制失败');
                                    }
                                    document.body.removeChild(textarea);
                                  }
                                }}
                                className="text-xs text-gray-500 hover:text-gray-300 px-2 py-0.5 rounded bg-white/5 cursor-pointer"
                              >
                                复制
                              </button>
                            </div>
                            <pre className="text-xs text-green-300 whitespace-pre-wrap font-mono overflow-x-auto max-h-32 scrollbar-thin">
                              {step.sql}
                            </pre>
                          </div>
                        )}
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-xs text-gray-500">执行结果:</p>
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              const text = step.result || '';
                              if (text) {
                                // 创建临时 textarea 复制
                                const textarea = document.createElement('textarea');
                                textarea.value = text;
                                textarea.style.position = 'fixed';
                                textarea.style.opacity = '0';
                                document.body.appendChild(textarea);
                                textarea.select();
                                try {
                                  document.execCommand('copy');
                                  alert('复制成功');
                                } catch {
                                  alert('复制失败');
                                }
                                document.body.removeChild(textarea);
                              }
                            }}
                            className="text-xs text-gray-500 hover:text-gray-300 px-2 py-0.5 rounded bg-white/5 cursor-pointer"
                          >
                            复制
                          </button>
                        </div>
                        <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono overflow-auto max-h-64 scrollbar-thin">
                          {step.result}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Query Results: Data, Chart, and Analysis Report */}
        {(() => {
          console.log('[渲染检查] queryData:', queryData);
          console.log('[渲染检查] queryData.data:', queryData?.data);
          console.log('[渲染检查] queryData.data.length:', queryData?.data?.length);
          console.log('[渲染检查] 是否显示结果:', queryData && queryData.data && queryData.data.length > 0);
          return null;
        })()}
        {queryData && queryData.data && queryData.data.length > 0 && (
          <QueryResultDisplay
            queryData={queryData}
            answer={answer}
            chartConfig={chartConfig}
          />
        )}

        {/* 如果没有查询数据但有文本答案，也显示答案 */}
        {(!queryData || !queryData.data || queryData.data.length === 0) && answer && answer.trim() && (
          <div className="bg-[#13152E] rounded-lg border border-cyan-500/20 p-3 mt-4">
            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-white/5">
              <FileText className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-xs font-medium text-cyan-300">回答</span>
            </div>
            <div className="prose prose-sm prose-invert max-w-none">
              <p className="text-gray-300 text-xs leading-relaxed whitespace-pre-wrap">
                {answer}
              </p>
            </div>
          </div>
        )}

        {/* Example Questions */}
        {!showThinking && (
          <div>
            <p className="text-xs text-gray-500 mb-3 flex items-center gap-1">
              <span>💡</span>
              <span>示例问题</span>
            </p>
            <div className="space-y-2">
              {exampleQuestions.map((question, idx) => (
                <button
                  key={idx}
                  onClick={() => handleExampleClick(question)}
                  className="w-full text-left px-3 py-2.5 rounded-lg bg-[#13152E] hover:bg-[#1a1d3e] border border-white/5 hover:border-purple-500/30 transition-all text-xs text-gray-300"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Guide */}
        {!showThinking && (
          <div className="mt-8 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-purple-500/10 mb-3">
              <Sparkles className="w-6 h-6 text-purple-400" />
            </div>
            <p className="text-sm text-gray-400 mb-1">AI 智能问答</p>
            <p className="text-xs text-gray-600">支持多表查询，自动分析数据库结构</p>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-white/5 px-4 py-4 flex-shrink-0">
        <div className="space-y-3">
          {/* 数据库选择下拉框 */}
          {databaseList.length > 0 && (
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-cyan-400" />
              <Select value={chatDbName} onValueChange={setChatDbName}>
                <SelectTrigger className="bg-[#13152E] border-white/10 text-gray-300 w-[200px]">
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
              <button
                onClick={refreshDatabaseList}
                disabled={isRefreshingDb}
                className="p-1.5 rounded hover:bg-white/10 transition-colors text-gray-400 hover:text-cyan-400 disabled:opacity-50"
                title="刷新数据库列表"
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshingDb ? 'animate-spin' : ''}`} />
              </button>
            </div>
          )}
          <Textarea
            placeholder="输入您的问题，AI 将自动分析数据库、生成 SQL 并查询..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={isQuerying}
            className="min-h-[100px] bg-[#13152E] border-white/10 text-gray-300 placeholder-gray-600 resize-none focus:border-purple-500/30 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <div className="flex justify-between items-center">
            <p className="text-xs text-gray-600">
              Enter 发送，Shift + Enter 换行
            </p>
            <Button
              onClick={handleSend}
              disabled={!query.trim() || isQuerying}
              size="sm"
              className="bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-400 hover:to-pink-500 text-white shadow-lg shadow-purple-500/20"
            >
              {isQuerying ? (
                <>发送中...</>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5 mr-1.5" />
                  发送
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
