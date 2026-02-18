"""
后处理训练模块：负责训练后处理，优化冗余（如LLM实例只创建一次）
使用 Pydantic 结构化输出替代正则解析 JSON
"""

import logging
logger = logging.getLogger(__name__)
from typing import List, Any, TypedDict
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


# ==================== Pydantic 结构化输出模型 ====================

class SimilarityEvaluation(BaseModel):
    """相似度评估结果（结构化输出）"""
    most_similar_question: str = Field(
        description="最相似的问题原文，如果没有相似问题则为空字符串"
    )
    similarity_score: float = Field(
        ge=0.0, 
        le=1.0, 
        description="相似度评分 0.0-1.0"
    )
    similarity_analysis: str = Field(
        description="相似度分析：详细解释为什么选择这个相似度评分"
    )


class SQLSelection(BaseModel):
    """SQL选择结果（结构化输出）"""
    selected_sql: str = Field(
        description="完整的 SQL 语句（从列表中选择一个，不要修改）"
    )
    reason: str = Field(
        description="选择理由：简要说明为什么选择这个 SQL"
    )


class ConversationSummary(TypedDict):
    """对话摘要的结构化定义（类型安全）"""
    question: str
    sql_list: List[str]
    execution_result: str
    final_answer: str
    tool_calls: List[dict]


# ==================== 对话摘要提取 ====================

def extract_conversation_summary(messages: List[Any]) -> ConversationSummary:
    """从消息历史中提取关键信息
    
    Args:
        messages: LangChain 消息列表（包含用户消息、AI消息、工具消息）
        
    Returns:
        包含问题、SQL、执行结果的字典
    """
    summary = {
        "question": "",
        "sql_list": [],  # 可能有多个 SQL
        "execution_result": "",
        "final_answer": "",
        "tool_calls": [],
    }
    
    # 遍历消息历史
    for msg in messages:
        msg_type = getattr(msg, 'type', 'unknown')
        
        # 1. 提取用户问题（第一条人类消息）
        if msg_type == 'human' and not summary["question"]:
            summary["question"] = getattr(msg, 'content', '')
        
        # 2. 提取工具调用（SQL 生成和执行）
        if msg_type == 'ai' and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.get('name', '')
                tool_args = tc.get('args', {})
                summary["tool_calls"].append({
                    "tool": tool_name,
                    "args": tool_args
                })
                
                # 提取 SQL（从 generate_sql 或 execute_sql）
                if tool_name == 'generate_sql':
                    pass  # SQL 在下一条 ToolMessage
                elif tool_name == 'execute_sql':
                    sql = tool_args.get('sql', '')
                    if sql and sql not in summary["sql_list"]:
                        summary["sql_list"].append(sql)
        
        # 3. 提取工具返回的 SQL（generate_sql 的返回）
        if msg_type == 'tool':
            content = getattr(msg, 'content', '')
            # 检查是否是 SQL 语句（包含 SELECT）
            if 'SELECT' in content.upper() and len(content) < 1000:
                # 简单清洗
                sql = content.strip()
                if sql not in summary["sql_list"]:
                    summary["sql_list"].append(sql)
            
            # 检查是否是执行结果
            if '查询成功' in content or '返回行数' in content:
                summary["execution_result"] = content
        
        # 4. 提取最终答案（最后一条 AI 消息的 content）
        if msg_type == 'ai':
            content = getattr(msg, 'content', '')
            if content and not hasattr(msg, 'tool_calls'):  # 不是工具调用，是回答
                summary["final_answer"] = content
    
    return summary


class PostTrainingProcessor:
    """后处理训练处理器，负责决策是否将对话加入训练集
    
    优化：复用全局 LLM 实例，避免重复创建
    """

    def __init__(self):
        """初始化处理器（不再创建新的 LLM 实例）"""
        from ..shared import get_llm_instance
        
        # 从全局上下文获取 LLM 实例
        self.llm = get_llm_instance()
        if self.llm is None:
            raise RuntimeError("LLM 实例未初始化，请先调用 set_llm_instance()")
    
    def decide_and_add_to_training(
        self,
        question: str,
        conversation_history: List[Any],
        vanna_client
    ) -> str:
        """基于对话历史决策是否加入训练集，并执行添加
        
        Args:
            question: 用户原始问题
            conversation_history: 完整对话历史（event["messages"]）
            vanna_client: Vanna 客户端实例
            
        Returns:
            训练决策结果和执行反馈
        """
        try:
            # 步骤1: 提取对话摘要
            summary = extract_conversation_summary(conversation_history)
            
            logger.info("📋 对话摘要：")
            logger.info(f"  问题: {summary['question'][:100]}...")
            logger.info(f"  SQL 数量: {len(summary['sql_list'])}")
            logger.info(f"  工具调用: {len(summary['tool_calls'])} 次")
            logger.info(f"  最终答案: {summary['final_answer'][:100]}...")
            logger.info("")
            
            # 步骤2: 检索相似问题
            similar_sqls = vanna_client.get_similar_question_sql(question, n_results=5)
            
            logger.info("🔍 相似度检查：")
            if similar_sqls:
                logger.info(f"  找到 {len(similar_sqls)} 个相似问题")
                for i, pair in enumerate(similar_sqls[:3], 1):
                    logger.info(f"  [{i}] {pair.get('question', 'N/A')[:60]}...")
            else:
                logger.info("  未找到相似问题")
            logger.info("")
            
            # 步骤3: 评估相似度（使用结构化输出）
            logger.info("🤖 第一步：评估相似度...")
            
            # ✅ 使用结构化输出，不需要正则解析！
            similarity_result = self._evaluate_similarity_structured(
                summary['question'], 
                similar_sqls
            )
            
            most_similar = similarity_result.most_similar_question
            similarity_score = similarity_result.similarity_score
            similarity_analysis = similarity_result.similarity_analysis
            
            logger.info(f"  最相似问题: {most_similar[:50]}{'...' if len(most_similar) > 50 else ''}")
            logger.info(f"  相似度评分: {similarity_score:.2f}")
            logger.info(f"  分析: {similarity_analysis[:80]}...")
            logger.info("")
            
            # 步骤4: 基于相似度直接决策
            if similarity_score >= 0.85:
                return f"⏭️  未添加到训练集（相似度过高: {similarity_score:.2f}）"
            
            # 检查基本条件
            if '查询成功' not in summary['execution_result']:
                return f"⏭️  未添加到训练集（SQL执行失败）"
            
            if not summary['sql_list']:
                return f"⏭️  未添加到训练集（未找到SQL）"
            
            # 步骤5: 选择最优SQL（使用结构化输出）
            logger.info("🤖 第二步：从对话中选择最优 SQL...")
            
            # ✅ 使用结构化输出，不需要正则解析！
            sql_result = self._select_best_sql_structured(
                summary['question'],
                summary['sql_list'],
                summary['execution_result'],
                summary['final_answer']
            )
            
            selected_sql = sql_result.selected_sql
            selection_reason = sql_result.reason
            
            logger.info(f"  选择的SQL: {selected_sql[:80]}{'...' if len(selected_sql) > 80 else ''}")
            logger.info(f"  选择理由: {selection_reason[:80]}...")
            logger.info("")
            
            # 步骤6: 执行添加
            if selected_sql:
                try:
                    logger.info("💾 添加到训练集...")
                    sql_id = vanna_client.train(question=question, sql=selected_sql)
                    
                    if "已存在" in str(sql_id):
                        return f"⏭️  训练集决策结果: 未添加（数据已存在）\nSQL ID: {sql_id}"
                    else:
                        return f"✅ 已成功添加到训练集！\n训练数据ID: {sql_id[:50]}..."
                except Exception as e:
                    return f"❌ 添加到训练集失败\n错误信息: {str(e)}"
            else:
                return f"⏭️  未添加到训练集（SQL选择失败）"
                
        except Exception as e:
            return f"❌ 训练决策失败\n错误信息: {str(e)}"
    
    def _build_similarity_prompt(self, question: str, similar_sqls: list) -> str:
        """构建相似度评估提示"""
        prompt = f"""
你是一个语义相似度评估专家。请评估用户问题与训练集中已有问题的相似度。

**用户问题:**
{question}

**训练集中的相似问题（按向量检索结果排序，共{len(similar_sqls)}个）:**

"""
        
        if similar_sqls:
            for i, pair in enumerate(similar_sqls, 1):
                prompt += f"[{i}] {pair.get('question', 'N/A')}\n"
        else:
            prompt += "（未找到相似问题）\n"
        
        prompt += """

**任务要求:**
请从上述问题中找出与用户问题最相似的那个，并给出相似度评分（0-1）。

**评分标准:**
- 1.0: 完全相同（只是标点、空格等细微差异）
- 0.95-0.99: 语义完全一致，表述略有不同
- 0.85-0.94: 高度相似，核心意图相同，细节略有差异
- 0.70-0.84: 较为相似，属于同类问题但具体查询内容不同
- 0.50-0.69: 部分相似，涉及相同领域但查询目标不同
- < 0.50: 不相似

请返回 JSON 格式（不要使用代码块包裹）：
{
    "most_similar_question": "最相似的问题原文（如果没有相似问题则为空字符串）",
    "similarity_score": <0.0-1.0>,
    "similarity_analysis": "相似度分析：请详细解释为什么选择这个相似度评分。"
}

**重要提示：**
- 如果训练集为空，similarity_score 应为 0
- 必须基于语义相似度，不是关键词匹配
- 相似度评分要严格遵守标准，不要过于宽松
"""
        return prompt
    
    def _build_sql_selection_prompt(
        self,
        question: str,
        sql_list: list,
        execution_result: str,
        final_answer: str
    ) -> str:
        """构建SQL选择提示"""
        prompt = f"""
你是一个 SQL 专家。请从对话历史中提取的 SQL 语句中，选出最重要、最有价值的那个用于加入训练集。

**用户问题:**
{question}

**对话中生成的 SQL 语句（共 {len(sql_list)} 个）:**

"""
        
        for i, sql in enumerate(sql_list, 1):
            prompt += f"""
[SQL {i}]
{sql}

"""
        
        prompt += f"""
**执行结果:**
{execution_result[:500]}

**最终答案:**
{final_answer}

**任务要求:**
请选择一个最适合加入训练集的 SQL 语句。

**选择标准:**
1. 能够正确回答用户问题（执行成功并返回了正确结果）
2. SQL 语句结构清晰、规范
3. 如果有多个 SQL，选择最终使用的那个（通常是最后一个执行成功的）
4. 不要修改 SQL 内容，直接返回原始语句

请返回 JSON 格式（不要使用代码块包裹）：
{{
    "selected_sql": "完整的 SQL 语句（从上面的列表中选择一个，不要修改）",
    "reason": "选择理由：简要说明为什么选择这个 SQL"
}}

**重要提示：**
- selected_sql 必须是上面列表中的某一个，完整复制，不要修改
- 如果只有一个 SQL，就选择它
- 如果有多个，选择最终执行成功并给出答案的那个
"""
        return prompt
    
    # ==================== 新增：结构化输出方法 ====================
    
    def _evaluate_similarity_structured(
        self, 
        question: str, 
        similar_sqls: list
    ) -> SimilarityEvaluation:
        """评估相似度（使用结构化输出）
        
        Args:
            question: 用户问题
            similar_sqls: 相似问题列表
            
        Returns:
            SimilarityEvaluation: 结构化的相似度评估结果
        """
        # ✅ 创建支持结构化输出的 LLM
        structured_llm = self.llm.with_structured_output(SimilarityEvaluation)
        
        prompt = f"""
你是一个语义相似度评估专家。请评估用户问题与训练集中已有问题的相似度，并以 JSON 格式返回结果。

**用户问题:**
{question}

**训练集中的相似问题（按向量检索结果排序，共{len(similar_sqls)}个）:**

"""
        
        if similar_sqls:
            for i, pair in enumerate(similar_sqls, 1):
                prompt += f"[{i}] {pair.get('question', 'N/A')}\n"
        else:
            prompt += "（未找到相似问题）\n"
        
        prompt += """

**任务要求:**
请从上述问题中找出与用户问题最相似的那个，并给出相似度评分（0-1）。

**评分标准:**
- 1.0: 完全相同（只是标点、空格等细微差异）
- 0.95-0.99: 语义完全一致，表述略有不同
- 0.85-0.94: 高度相似，核心意图相同，细节略有差异
- 0.70-0.84: 较为相似，属于同类问题但具体查询内容不同
- 0.50-0.69: 部分相似，涉及相同领域但查询目标不同
- < 0.50: 不相似

**输出要求:**
请以 JSON 格式返回评估结果，包含以下字段：
- most_similar_question: 最相似的问题原文（如果没有相似问题则为空字符串）
- similarity_score: 相似度评分 0.0-1.0
- similarity_analysis: 相似度分析，详细解释为什么选择这个相似度评分

**重要提示：**
- 如果训练集为空，similarity_score 应为 0
- 必须基于语义相似度，不是关键词匹配
- 相似度评分要严格遵守标准，不要过于宽松
"""
        
        # ✅ 直接返回 Pydantic 对象，无需正则解析！
        return structured_llm.invoke(prompt)
    
    def _select_best_sql_structured(
        self,
        question: str,
        sql_list: List[str],
        execution_result: str,
        final_answer: str
    ) -> SQLSelection:
        """选择最优SQL（使用结构化输出）
        
        Args:
            question: 用户问题
            sql_list: SQL 列表
            execution_result: 执行结果
            final_answer: 最终答案
            
        Returns:
            SQLSelection: 结构化的SQL选择结果
        """
        # ✅ 创建支持结构化输出的 LLM
        structured_llm = self.llm.with_structured_output(SQLSelection)
        
        prompt = f"""
你是一个 SQL 专家。请从对话历史中提取的 SQL 语句中，选出最重要、最有价值的那个用于加入训练集，并以 JSON 格式返回结果。

**用户问题:**
{question}

**对话中生成的 SQL 语句（共 {len(sql_list)} 个）:**

"""
        
        for i, sql in enumerate(sql_list, 1):
            prompt += f"""
[SQL {i}]
{sql}

"""
        
        prompt += f"""
**执行结果:**
{execution_result[:500]}

**最终答案:**
{final_answer}

**任务要求:**
请选择一个最适合加入训练集的 SQL 语句。

**选择标准:**
1. 能够正确回答用户问题（执行成功并返回了正确结果）
2. SQL 语句结构清晰、规范
3. 如果有多个 SQL，选择最终使用的那个（通常是最后一个执行成功的）
4. 不要修改 SQL 内容，直接返回原始语句

**输出要求:**
请以 JSON 格式返回选择结果，包含以下字段：
- selected_sql: 完整的 SQL 语句（从上面的列表中选择一个，不要修改）
- reason: 选择理由，简要说明为什么选择这个 SQL

**重要提示：**
- selected_sql 必须是上面列表中的某一个，完整复制，不要修改
- 如果只有一个 SQL，就选择它
- 如果有多个，选择最终执行成功并给出答案的那个
"""
        
        # ✅ 直接返回 Pydantic 对象，无需正则解析！
        return structured_llm.invoke(prompt)
