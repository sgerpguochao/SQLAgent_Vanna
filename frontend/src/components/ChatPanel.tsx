import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, Loader2, CheckCircle, Clock, ChevronDown, ChevronRight, BarChart3, FileText, Hash, TableIcon } from 'lucide-react';
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

interface ChatPanelProps {
  selectedTable?: string | null;
  onQueryResult?: (result: any) => void;
}

interface ThinkingStep {
  action: string;
  status: '准备中' | '进行中' | '完成';
  duration_ms?: number;
  tool_name?: string;
  result?: string;  // 工具执行结果
}

export function ChatPanel({ selectedTable, onQueryResult }: ChatPanelProps) {
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
  const abortControllerRef = useRef<AbortController | null>(null);

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
    <div className="h-full flex flex-col bg-[#0B0D1E] overflow-hidden">
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
                        <p className="text-xs text-gray-500 mb-1">执行结果:</p>
                        <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono overflow-x-auto">
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
            className="min-h-[100px] bg-[#13152E] border-white/10 text-gray-300 placeholder-gray-600 resize-none focus:border-purple-500/30 text-sm"
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
