import React from 'react';
import { Download, RefreshCw, TableIcon } from 'lucide-react';
import { Button } from './ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';

interface ResultsPanelProps {
  queryResult?: any;
}

export function ResultsPanel({ queryResult }: ResultsPanelProps) {
  const handleExport = () => {
    if (!queryResult || !queryResult.data) return;

    const headers = queryResult.columns?.join(',') || '';
    const rows = queryResult.data.map((row: any) =>
      Object.values(row).join(',')
    ).join('\n');

    const csv = `${headers}\n${rows}`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `query_result_${Date.now()}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const totalRows = queryResult?.total_rows || queryResult?.data?.length || 0;
  const returnedRows = queryResult?.returned_rows || queryResult?.data?.length || 0;

  return (
    <div className="h-full flex flex-col bg-[#0B0D1E] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-2 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TableIcon className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-medium text-cyan-400">查询结果</h3>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleExport}
              disabled={!queryResult || !queryResult.data}
              className="h-7 px-2 text-gray-400 hover:text-cyan-400 hover:bg-white/5"
              title="导出为CSV"
            >
              <Download className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Pagination/Stats Bar */}
      {queryResult && queryResult.data && queryResult.data.length > 0 && (
        <div className="px-4 py-2 border-b border-white/5 flex items-center justify-between bg-[#0D0F1A] flex-shrink-0">
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <span>Total: {totalRows}</span>
          </div>
          <div className="text-xs text-gray-500">
            <span className="text-cyan-400">{returnedRows}</span> row{returnedRows !== 1 ? 's' : ''}
          </div>
        </div>
      )}

      {/* Search bar */}
      {queryResult && queryResult.data && queryResult.data.length > 0 && (
        <div className="px-4 py-2 border-b border-white/5 bg-[#0D0F1A] flex-shrink-0">
          <input
            type="text"
            placeholder="Search result data"
            className="w-full bg-[#13152E] border border-white/10 text-gray-300 text-xs px-3 py-1.5 rounded focus:outline-none focus:ring-1 focus:ring-cyan-500/30 placeholder-gray-600"
          />
        </div>
      )}

      {/* Table Content */}
      <div className="flex-1 overflow-auto min-h-0">
        {!queryResult || !queryResult.data || queryResult.data.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <TableIcon className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">暂无查询结果</p>
              <p className="text-gray-600 text-xs mt-1">请选择表并执行查询</p>
            </div>
          </div>
        ) : (
          <div className="h-full">
            <Table>
              <TableHeader className="sticky top-0 bg-[#0D0F1A] z-10">
                <TableRow className="border-white/5 hover:bg-transparent">
                  <TableHead className="text-gray-500 font-medium text-xs w-12 text-center">#</TableHead>
                  {(queryResult.columns || Object.keys(queryResult.data[0])).map((col: string, idx: number) => (
                    <TableHead key={idx} className="text-cyan-400 font-medium text-xs">
                      <div className="flex items-center gap-1">
                        <span>{col}</span>
                        <svg className="w-3 h-3 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                        </svg>
                      </div>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {queryResult.data.map((row: any, rowIdx: number) => (
                  <TableRow key={rowIdx} className="border-white/5 hover:bg-white/5">
                    <TableCell className="text-gray-500 text-xs text-center">{rowIdx + 1}</TableCell>
                    {(queryResult.columns || Object.keys(row)).map((col: string, colIdx: number) => (
                      <TableCell key={colIdx} className="text-gray-300 text-xs font-mono">
                        {row[col] !== null && row[col] !== undefined ? String(row[col]) : 'NULL'}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Footer with execution info */}
      {queryResult && queryResult.data && queryResult.data.length > 0 && (
        <div className="px-4 py-1.5 border-t border-white/5 bg-[#0D0F1A] flex items-center justify-between flex-shrink-0">
          <div className="text-xs text-gray-500">
            [Result] Execution successful.
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>[Time Consumed] {queryResult.executionTime || '187'}ms</span>
            <span>[Search Result] {returnedRows} row{returnedRows !== 1 ? 's' : ''}</span>
          </div>
        </div>
      )}
    </div>
  );
}
