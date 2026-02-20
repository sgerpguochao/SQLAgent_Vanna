"""
RAG 检索工具
提供 DDL、文档、历史 SQL 的检索功能（支持 db_name 过滤）
"""
import logging
logger = logging.getLogger(__name__)
from langchain.tools import tool  # type: ignore
from ..shared import get_vanna_client


# ==================== 辅助函数 ====================

def _extract_keywords(question: str) -> list:
    """从问题中提取关键词"""
    if not question:
        return []

    import re
    stop_words = {'的', '是', '在', '有', '和', '与', '或', '了', '一个', '什么', '怎么', '如何', '请', '查询', '获取', '找出'}

    words = re.split(r'[\s,，。、！？\.\-\_\/]+', question)
    words = [w.strip() for w in words if w.strip()]

    keywords = [w for w in words if w not in stop_words and len(w) >= 2]
    return keywords


def _merge_and_deduplicate(list1: list, list2: list) -> list:
    """合并两个列表并去重"""
    seen = set()
    result = []
    for item in list1 + list2:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


# ==================== RAG 检索工具 ====================

@tool
def get_table_schema(question: str) -> str:
    """获取与问题相关的完整RAG信息（DDL、文档说明、历史SQL）
    支持 db_name 过滤、多路召回（向量检索 + 关键词匹配）

    Args:
        question: 用户问题

    Returns:
        包含表结构、业务说明和历史查询的完整上下文
    """
    vn = get_vanna_client()

    try:
        # 获取当前数据库名
        db_query = "SELECT DATABASE()"
        db_result = vn.run_sql(db_query)
        db_name = db_result.iloc[0, 0]

        # 提取关键词
        keywords = _extract_keywords(question)

        result_parts = []

        # 1. 向量检索 DDL（阈值 0.5，topk=5，按 db_name 过滤）
        ddl_list = vn.get_related_ddl(
            question,
            db_name=db_name,
            threshold=0.5,
            top_k=5
        )

        # 2. 关键词增强：补充相关 DDL
        if keywords:
            keyword_ddl_list = vn._get_ddl_by_keywords(keywords, db_name=db_name, top_k=5)
            ddl_list = _merge_and_deduplicate(ddl_list, keyword_ddl_list)

        if ddl_list:
            result_parts.append("相关表结构 (DDL):")
            result_parts.append("\n".join(ddl_list[:5]))

        # 3. 向量检索文档（按 db_name 过滤）
        doc_list = vn.get_related_documentation(
            question,
            db_name=db_name,
            top_k=5
        )

        # 4. 关键词增强：补充相关文档
        if keywords:
            keyword_doc_list = vn._get_doc_by_keywords(keywords, db_name=db_name, top_k=5)
            doc_list = _merge_and_deduplicate(doc_list, keyword_doc_list)

        if doc_list:
            result_parts.append("\n\n业务文档说明:")
            for i, doc in enumerate(doc_list[:5], 1):
                result_parts.append(f"\n[文档{i}]\n{doc}")

        # 5. 历史 SQL 检索（按 db_name 过滤）
        similar_pairs = vn.get_similar_question_sql(
            question,
            db_name=db_name,
            top_k=3
        )
        if similar_pairs:
            result_parts.append("\n\n历史相似查询:")
            for i, pair in enumerate(similar_pairs[:3], 1):
                q = pair.get('question', 'N/A')
                sql = pair.get('sql', 'N/A')
                result_parts.append(f"\n[示例{i}]\n问题: {q}\nSQL: {sql}")

        return "\n".join(result_parts) if result_parts else "未找到相关信息"

    except Exception as e:
        logger.error(f"获取RAG信息失败: {e}")
        return f"获取RAG信息失败: {str(e)}"
