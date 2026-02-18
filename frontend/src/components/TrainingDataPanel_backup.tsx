import React, { useState, useEffect } from 'react';
import { BookOpen, Plus, Trash2, Download, Upload, Database } from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { toast } from 'sonner';

// 示例数据模板（从 nl2sql_training_data.py 提取）
const EXAMPLE_TEMPLATES = {
  documentation: `表名: dim_product
描述: 存储所有电子产品的基本信息，用于产品分析
字段:
- product_sk (BIGINT, 主键): 产品唯一标识，代理键
- product_name (VARCHAR): 产品完整名称，如"OPPO 投影仪 X4"
- brand (VARCHAR): 品牌名称，如"OPPO"、"小米"、"苹果"、"华为"
- category (VARCHAR): 产品分类，如"投影仪"、"智能手机"、"电视"、"耳机"
记录数: 800`,

  ddl: `CREATE TABLE dim_product (
    product_sk      BIGINT NOT NULL COMMENT '产品唯一标识，代理键',
    product_name    VARCHAR(255) COMMENT '产品完整名称',
    brand           VARCHAR(100) COMMENT '品牌名称',
    category        VARCHAR(100) COMMENT '产品分类',
    PRIMARY KEY (product_sk)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品维度表';`,

  sql: `SELECT
    p.brand,
    SUM(f.quantity) AS total_quantity,
    ROUND(SUM(f.price * f.quantity), 2) AS total_gmv
FROM fact_sales_electronics f
JOIN dim_product p ON f.product_sk = p.product_sk
GROUP BY p.brand
ORDER BY total_quantity DESC
LIMIT 10`
};

interface TrainingData {
  id: string;
  type: string;
  content: string;
  question?: string;
}

export function TrainingDataPanel() {
  const [trainingData, setTrainingData] = useState<TrainingData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

  // 添加表单状态
  const [dataType, setDataType] = useState<'documentation' | 'ddl' | 'sql'>('documentation');
  const [content, setContent] = useState('');
  const [question, setQuestion] = useState('');

  // 加载训练数据
  const loadTrainingData = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://117.50.174.50:8100/api/v1/training/get');
      const data = await response.json();

      if (data.success && data.data) {
        setTrainingData(data.data);
        toast.success(`加载了 ${data.data.length} 条训练数据`);
      }
    } catch (error) {
      console.error('加载训练数据失败:', error);
      toast.error('加载训练数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 添加训练数据
  const handleAdd = async () => {
    if (!content.trim()) {
      toast.error('请输入训练数据内容');
      return;
    }

    if (dataType === 'sql' && !question.trim()) {
      toast.error('SQL 类型需要提供对应的问题');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('http://117.50.174.50:8100/api/v1/training/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          data_type: dataType,
          content: content,
          question: dataType === 'sql' ? question : undefined
        })
      });

      const data = await response.json();

      if (data.success) {
        toast.success(data.message || '添加成功');
        setContent('');
        setQuestion('');
        setShowAddForm(false);
        loadTrainingData();
      } else {
        toast.error(data.message || '添加失败');
      }
    } catch (error) {
      console.error('添加训练数据失败:', error);
      toast.error('添加训练数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 删除训练数据
  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除这条训练数据吗？')) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('http://117.50.174.50:8100/api/v1/training/delete', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      });

      const data = await response.json();

      if (data.success) {
        toast.success('删除成功');
        loadTrainingData();
      } else {
        toast.error(data.message || '删除失败');
      }
    } catch (error) {
      console.error('删除训练数据失败:', error);
      toast.error('删除训练数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 使用示例模板
  const useTemplate = () => {
    setContent(EXAMPLE_TEMPLATES[dataType]);
    if (dataType === 'sql') {
      setQuestion('哪个品牌销量最高？');
    }
  };

  useEffect(() => {
    loadTrainingData();
  }, []);

  return (
    <div className="flex flex-col h-full bg-[#0A0B1E]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-emerald-400" />
            <h2 className="text-emerald-400 font-medium text-sm">训练数据管理</h2>
          </div>
          <Button
            onClick={() => setShowAddForm(!showAddForm)}
            size="sm"
            className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20"
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            添加
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto min-h-0 px-4 py-4 space-y-4">
        {/* 添加表单 */}
        {showAddForm && (
          <div className="bg-[#13152E] rounded-lg border border-emerald-500/20 p-4 space-y-3">
            <h3 className="text-sm font-medium text-emerald-400 flex items-center gap-2">
              <Plus className="w-4 h-4" />
              添加新训练数据
            </h3>

            {/* 数据类型选择 */}
            <div className="space-y-2">
              <label className="text-xs text-gray-400">数据类型</label>
              <Select value={dataType} onValueChange={(value: any) => setDataType(value)}>
                <SelectTrigger className="bg-[#0A0B1E] border-white/10 text-gray-300">
                  <SelectValue placeholder="选择数据类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="documentation">Documentation (表文档)</SelectItem>
                  <SelectItem value="ddl">DDL (表结构)</SelectItem>
                  <SelectItem value="sql">SQL (示例查询)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* SQL 问题输入 */}
            {dataType === 'sql' && (
              <div className="space-y-2">
                <label className="text-xs text-gray-400">问题</label>
                <Textarea
                  placeholder="输入对应的业务问题，如：哪个品牌销量最高？"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  className="min-h-[60px] bg-[#0A0B1E] border-white/10 text-gray-300 text-sm"
                />
              </div>
            )}

            {/* 内容输入 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs text-gray-400">内容</label>
                <Button
                  onClick={useTemplate}
                  size="sm"
                  variant="ghost"
                  className="text-xs text-emerald-400 hover:text-emerald-300"
                >
                  <Download className="w-3 h-3 mr-1" />
                  使用示例模板
                </Button>
              </div>
              <Textarea
                placeholder={`输入 ${dataType} 内容...`}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="min-h-[200px] bg-[#0A0B1E] border-white/10 text-gray-300 text-sm font-mono"
              />
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-2">
              <Button
                onClick={handleAdd}
                disabled={isLoading}
                size="sm"
                className="bg-emerald-500 hover:bg-emerald-600 text-white"
              >
                <Upload className="w-3.5 h-3.5 mr-1" />
                {isLoading ? '添加中...' : '添加'}
              </Button>
              <Button
                onClick={() => {
                  setShowAddForm(false);
                  setContent('');
                  setQuestion('');
                }}
                size="sm"
                variant="outline"
                className="border-white/10 text-gray-400"
              >
                取消
              </Button>
            </div>
          </div>
        )}

        {/* 训练数据列表 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">
              共 {trainingData.length} 条训练数据
            </p>
            <Button
              onClick={loadTrainingData}
              disabled={isLoading}
              size="sm"
              variant="ghost"
              className="text-xs text-gray-400 hover:text-gray-300"
            >
              刷新
            </Button>
          </div>

          {isLoading && trainingData.length === 0 ? (
            <div className="text-center py-8 text-gray-500 text-sm">
              加载中...
            </div>
          ) : trainingData.length === 0 ? (
            <div className="text-center py-8 text-gray-500 text-sm">
              暂无训练数据
            </div>
          ) : (
            trainingData.map((item) => (
              <div
                key={item.id}
                className="bg-[#13152E] rounded-lg border border-white/5 p-3 hover:border-emerald-500/30 transition-all"
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      item.type === 'sql' ? 'bg-blue-500/10 text-blue-400' :
                      item.type === 'ddl' ? 'bg-purple-500/10 text-purple-400' :
                      'bg-emerald-500/10 text-emerald-400'
                    }`}>
                      {item.type.toUpperCase()}
                    </span>
                    {item.question && (
                      <span className="text-xs text-gray-400">
                        问题: {item.question}
                      </span>
                    )}
                  </div>
                  <Button
                    onClick={() => handleDelete(item.id)}
                    size="sm"
                    variant="ghost"
                    className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
                <pre className="text-xs text-gray-400 bg-[#0A0B1E] p-2 rounded overflow-x-auto max-h-[200px] overflow-y-auto">
                  {item.content}
                </pre>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
