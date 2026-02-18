"""
RAG 检索工具
提供 DDL、文档、历史 SQL 的检索功能
"""
import logging
logger = logging.getLogger(__name__)
from langchain.tools import tool  # type: ignore
from ..shared import get_vanna_client


# ==================== RAG 检索工具 ====================

@tool
def get_table_schema(question: str) -> str:
    """获取与问题相关的完整RAG信息（DDL、文档说明、历史SQL）
    
    Args:
        question: 用户问题
    Returns:
        包含表结构、业务说明和历史查询的完整上下文
    """
    vn = get_vanna_client()
    try:
        result_parts = []
        # backend/vanna/src/vanna/milvus/milvus_vector.py： Vanna 提供的内置方法，根据问题检索相关的 DDL（表结构定义）
        # 我们是做了源码优化的，Vanna 使用 Milvus 向量数据库存储 RAG 数据，分为三个集合：
        # 集合名 存储内容 用途
        # vannaddl DDL 语句（表结构） 提供表结构上下文
        # vannadoc 业务文档 提供业务语义说明
        # vannasql 问题-SQL 对 提供历史查询示例
        
        # 1. 获取相关表结构 (DDL)
        ddl_list = vn.get_related_ddl(question, n_results=3)
        if ddl_list:
            # 使用中文记录结果
            result_parts.append("相关表结构 (DDL):")
            result_parts.append("\n".join(ddl_list))
        
        # 2. 获取文档说明 (Documentation)
        doc_list = vn.get_related_documentation(question, n_results=3)
        if doc_list:
            result_parts.append("\n\n业务文档说明:")
            for i, doc in enumerate(doc_list, 1):
                result_parts.append(f"\n[文档{i}]\n{doc}")
        
        # 3. 获取历史相似SQL (Question-SQL pairs)
        similar_pairs = vn.get_similar_question_sql(question, n_results=2)
        if similar_pairs:
            result_parts.append("\n\n历史相似查询:")
            for i, pair in enumerate(similar_pairs, 1):
                # similar_pairs 返回的是字典列表: [{'question': '...', 'sql': '...'}, ...]
                q = pair.get('question', 'N/A')
                sql = pair.get('sql', 'N/A')
                result_parts.append(f"\n[示例{i}]\n问题: {q}\nSQL: {sql}")
        
        return "\n".join(result_parts) if result_parts else "未找到相关信息"
    except Exception as e:
        return f"获取RAG信息失败: {str(e)}"
