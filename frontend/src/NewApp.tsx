import React, { useState } from 'react';
import { FileUploadPanel } from './components/FileUploadPanel';
import { NewQueryPanel } from './components/NewQueryPanel';
import { ResultsPanel } from './components/ResultsPanel';
import { Toaster } from './components/ui/sonner';
import { toast } from 'sonner';

export default function NewApp() {
  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [selectedFileId, setSelectedFileId] = useState<string>('');
  const [queryResult, setQueryResult] = useState<any>(null);

  const handleFileUploaded = (file: any) => {
    setSelectedFile(file);
    toast.success('文件上传成功', {
      description: `${file.name} 已成功上传`,
    });
  };

  const handleFileSelect = (fileId: string) => {
    setSelectedFileId(fileId);
  };

  const handleQueryResult = (result: any) => {
    setQueryResult(result);
    if (result.success) {
      toast.success('查询成功', {
        description: `返回 ${result.returnedRows || 0} 条结果`,
      });
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-gray-50">
      {/* Header */}
      <div className="h-16 border-b bg-white flex items-center px-6 flex-shrink-0">
        <div className="flex items-center gap-3">
          {/* Logo 图片 */}
          <div className="flex items-center gap-2">
            <img 
              src="/logo.png" 
              alt="Logo" 
              className="w-10 h-10 rounded-xl object-contain shadow-lg"
            />
            <div className="flex flex-col">
              <h1 className="text-lg font-semibold text-gray-900 leading-tight">
                SQL Agent
              </h1>
              <span className="text-[10px] text-gray-400 -mt-0.5">云南水利水电职业学院</span>
            </div>
          </div>
          <span className="text-gray-500 text-base ml-1">智能数据分析平台</span>
        </div>
        <div className="ml-auto flex items-center gap-2 text-sm text-gray-500">
          {selectedFile && (
            <>
              <span>当前文件：</span>
              <span className="font-medium text-gray-700">{selectedFile.name}</span>
            </>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - File Upload */}
        <div className="w-[320px] flex-shrink-0 border-r bg-white">
          <FileUploadPanel
            onFileUploaded={handleFileUploaded}
            selectedFileId={selectedFileId}
            onFileSelect={handleFileSelect}
          />
        </div>

        {/* Center Panel - Query */}
        <div className="flex-1 min-w-0 bg-gray-50">
          <NewQueryPanel
            selectedFileId={selectedFileId}
            onQueryResult={handleQueryResult}
            onVisualizationRequest={(data) => console.log('Visualization requested:', data)}
          />
        </div>

        {/* Right Panel - Results */}
        <div className="w-[500px] flex-shrink-0 border-l bg-white">
          <ResultsPanel data={queryResult?.data || []} />
        </div>
      </div>

      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'white',
            border: '1px solid #e5e7eb',
            color: '#1f2937',
          },
        }}
      />
    </div>
  );
}