import React from 'react';
import { BarChart3, FileText, TableIcon as Table2 } from 'lucide-react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar, Line, Pie, Scatter } from 'react-chartjs-2';
import ChartDataLabels from 'chartjs-plugin-datalabels';

// 注册 Chart.js 组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  ChartDataLabels
);

interface QueryResultDisplayProps {
  queryData: any;
  answer: string;
  chartConfig?: any;
}

export function QueryResultDisplay({ queryData, answer, chartConfig }: QueryResultDisplayProps) {
  console.log('[QueryResultDisplay] 收到 props:', {
    hasQueryData: !!queryData,
    hasAnswer: !!answer,
    hasChartConfig: !!chartConfig,
    chartConfig: chartConfig
  });

  // 根据图表类型渲染对应的组件
  const renderChart = () => {
    if (!chartConfig) return null;

    const { type, data, options } = chartConfig;

    const chartProps = {
      data,
      options: {
        ...options,
        maintainAspectRatio: false
      }
    };

    switch (type) {
      case 'bar':
        return <Bar {...chartProps} />;
      case 'line':
        return <Line {...chartProps} />;
      case 'pie':
        return <Pie {...chartProps} />;
      case 'scatter':
        return <Scatter {...chartProps} />;
      default:
        console.warn(`[QueryResultDisplay] 未知的图表类型: ${type}`);
        return null;
    }
  };

  if (!queryData || !queryData.data || queryData.data.length === 0) {
    return null;
  }

  const columns = queryData.columns || Object.keys(queryData.data[0]);

  const fieldNameMap: Record<string, string> = {
    'product_name': '产品名称',
    'price': '价格',
    'sales_volume': '销售数量',
    'sale_date': '销售日期',
    'category': '类别',
    'brand': '品牌',
    'total_amount': '销售总额',
    'quantity': '数量',
    'name': '名称',
  };

  const getFieldLabel = (field: string) => fieldNameMap[field] || field;

  return (
    <div className="space-y-4">
      {/* 数据表格 */}
      <div className="bg-[#13152E] rounded-lg border border-white/5 overflow-hidden">
        <div className="px-3 py-2 border-b border-white/5 bg-[#0D0F1A]">
          <div className="flex items-center gap-2">
            <Table2 className="w-3.5 h-3.5 text-cyan-400" />
            <h3 className="text-xs font-medium text-cyan-400">查询数据</h3>
            <span className="text-xs text-gray-500">({queryData.data.length} 行)</span>
          </div>
        </div>
        <div className="overflow-x-auto max-h-[200px] overflow-y-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-[#0D0F1A] z-10">
              <TableRow className="border-white/5 hover:bg-transparent">
                {columns.map((col: string, idx: number) => (
                  <TableHead key={idx} className="text-cyan-400 font-medium text-xs">
                    {getFieldLabel(col)}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {queryData.data.map((row: any, rowIdx: number) => (
                <TableRow key={rowIdx} className="border-white/5 hover:bg-white/5">
                  {columns.map((col: string, colIdx: number) => (
                    <TableCell key={colIdx} className="text-gray-300 text-xs">
                      {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* 可视化图表 - React Chart.js */}
      {chartConfig && (
        <div className="bg-[#13152E] rounded-lg border border-white/5 p-3">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
            <h3 className="text-xs font-medium text-cyan-400">数据可视化</h3>
          </div>

          {/* 渲染图表 */}
          <div style={{ height: '300px', position: 'relative' }}>
            {renderChart()}
          </div>
        </div>
      )}

      {/* 数据分析报告 */}
      {answer && answer.trim() && (
        <div className="bg-[#13152E] rounded-lg border border-cyan-500/20 p-3">
          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-white/5">
            <FileText className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs font-medium text-cyan-300">数据分析报告</span>
          </div>
          <div className="prose prose-sm prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h2: ({ node, ...props }) => <h2 className="text-sm font-semibold text-cyan-300 mt-3 mb-2" {...props} />,
                h3: ({ node, ...props }) => <h3 className="text-xs font-medium text-purple-300 mt-2 mb-1" {...props} />,
                p: ({ node, ...props }) => <p className="text-gray-300 text-xs leading-relaxed mb-2" {...props} />,
                ul: ({ node, ...props }) => <ul className="text-gray-300 text-xs space-y-1 ml-4 mb-2 list-disc" {...props} />,
                li: ({ node, ...props }) => <li className="text-gray-300" {...props} />,
                strong: ({ node, ...props }) => <strong className="text-cyan-400 font-medium" {...props} />,
                code: ({ node, inline, ...props }: any) =>
                  inline ? (
                    <code className="bg-gray-800 text-cyan-400 px-1 py-0.5 rounded text-xs font-mono" {...props} />
                  ) : (
                    <code className="block bg-gray-800 text-gray-300 p-2 rounded text-xs font-mono overflow-x-auto my-2" {...props} />
                  ),
              }}
            >
              {answer}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
