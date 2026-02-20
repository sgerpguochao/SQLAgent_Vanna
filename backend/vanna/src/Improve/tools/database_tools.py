"""
数据库相关工具模块
包含：数据库连接、表结构查询、SQL 执行、语法校验等
"""

import logging
logger = logging.getLogger(__name__)
import threading
import time
import pandas as pd
import re
from langchain.tools import tool  # type: ignore

# 导入共享上下文（统一管理）
from ..shared import get_vanna_client, set_last_query_result


_sql_execution_lock = threading.Lock()


def _extract_keywords(question: str) -> list:
    """
    从问题中提取关键词

    Args:
        question: 用户问题

    Returns:
        list: 关键词列表
    """
    if not question:
        return []

    # 移除常见停用词
    stop_words = {'的', '是', '在', '有', '和', '与', '或', '了', '一个', '什么', '怎么', '如何', '请', '查询', '获取', '找出'}

    # 简单分词（按空格和标点分割）
    words = re.split(r'[\s,，。、！？\.\-\_\/]+', question)
    words = [w.strip() for w in words if w.strip()]

    # 过滤停用词和短词
    keywords = [w for w in words if w not in stop_words and len(w) >= 2]

    return keywords


def _filter_tables_by_keywords(tables_df: pd.DataFrame, keywords: list) -> pd.DataFrame:
    """
    通过关键字过滤表

    Args:
        tables_df: 包含所有表的 DataFrame
        keywords: 关键词列表

    Returns:
        pd.DataFrame: 过滤后的表
    """
    if not keywords or tables_df.empty:
        return tables_df

    # 将关键词转为小写进行匹配
    keywords_lower = [k.lower() for k in keywords]

    def matches_keyword(table_name: str, table_comment: str) -> bool:
        """检查表名或表注释是否包含关键词"""
        table_lower = table_name.lower()
        comment_lower = (table_comment or "").lower()

        for kw in keywords_lower:
            if kw in table_lower or kw in comment_lower:
                return True
        return False

    # 过滤匹配的表
    mask = tables_df.apply(
        lambda row: matches_keyword(row['TABLE_NAME'], row['TABLE_COMMENT']),
        axis=1
    )

    filtered_df = tables_df[mask]

    # 如果没有匹配，返回前10个表
    if filtered_df.empty:
        return tables_df.head(10)

    return filtered_df


def _filter_tables_by_plan(vn, db_name: str, question: str, all_tables: list) -> list:
    """
    通过 vannaplan 检索相关表名并与 all_tables 取交集

    Args:
        vn: Vanna 客户端
        db_name: 数据库名称
        question: 用户问题
        all_tables: 所有表名列表

    Returns:
        list: 过滤后的表名列表（优先使用 plan 过滤）
    """
    if not question or not db_name or not all_tables:
        return []

    try:
        # 调用 vannaplan 检索方法，获取相似度 >= 0.75 的 top5 相关表
        related_tables = vn.get_related_plan_tables(
            question=question,
            db_name=db_name,
            threshold=0.75,
            top_k=5
        )

        if not related_tables:
            logger.info("Plan 过滤未返回相关表，将使用关键字过滤")
            return []

        # 将 all_tables 转为小写映射
        all_tables_lower = {t.lower(): t for t in all_tables}

        # 取交集（按大小写不敏感）
        filtered_tables = []
        for table in related_tables:
            table_lower = table.lower()
            if table_lower in all_tables_lower:
                filtered_tables.append(all_tables_lower[table_lower])

        logger.info(f"Plan 过滤结果: {len(filtered_tables)}/{len(related_tables)} 个表匹配")

        return filtered_tables

    except Exception as e:
        logger.warning(f"Plan 过滤失败: {e}，将使用关键字过滤")
        return []

@tool
def get_all_tables_info(question: str = "") -> str:
    """直接从MySQL数据库获取所有表及其列信息

    支持两种过滤方式（优先使用 Plan 过滤，其次是关键字过滤）：
    1. Plan 过滤：通过 vannaplan 检索相似度 >= 0.85 的 top5 记录，提取关联表
    2. 关键字过滤：从问题中提取关键词，匹配表名或表注释

    Args:
        question: 用户问题（可选），用于过滤相关表

    Returns:
        所有表的结构信息（表名、列名、数据类型、注释）
    """

    # 调用 ：backend/vanna/src/Improve/clients/vanna_client.py
    vn = get_vanna_client()
    try:
        # 获取当前数据库名
        db_query = "SELECT DATABASE()"
        db_result = vn.run_sql(db_query)
        db_name = db_result.iloc[0, 0]

        # 查询所有表的详细信息
        tables_query = f"""
        SELECT
            TABLE_NAME,
            TABLE_COMMENT
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = '{db_name}'
        ORDER BY TABLE_NAME
        """

        # run_sql 方法是 Vanna 库安装后自带的方法： backend/vanna/src/vanna/base/base.py
        # class VannaBase(ABC):
        #     def run_sql(self, sql: str, **kwargs) -> pd.DataFrame:
        #         """Run a SQL query on the connected database."""
        #         raise Exception("You need to connect to a database first...")

        tables_df = vn.run_sql(tables_query)

        if tables_df.empty:
            return f"Database {db_name} has no tables"

        # 保存所有表名列表（用于过滤）
        all_table_names = tables_df['TABLE_NAME'].tolist()

        # 如果提供了问题，进行表过滤
        filtered_table_names = None
        filter_method = None

        if question:
            # 1. 优先尝试 Plan 过滤
            plan_filtered = _filter_tables_by_plan(vn, db_name, question, all_table_names)
            if plan_filtered:
                filtered_table_names = plan_filtered
                filter_method = "Plan"
                logger.info(f"使用 Plan 过滤，匹配到 {len(filtered_table_names)} 个表")
            else:
                # 2. Plan 过滤无结果，使用关键字过滤
                keywords = _extract_keywords(question)
                if keywords:
                    filtered_df = _filter_tables_by_keywords(tables_df, keywords)
                    filtered_table_names = filtered_df['TABLE_NAME'].tolist()
                    filter_method = "关键字"
                    logger.info(f"使用关键字过滤，匹配到 {len(filtered_table_names)} 个表")

        # 应用过滤
        if filtered_table_names is not None and filtered_table_names:
            # 过滤后的表（确保只包含存在的表）
            tables_df = tables_df[tables_df['TABLE_NAME'].isin(filtered_table_names)]
            if tables_df.empty:
                # 过滤后为空，回退到所有表
                tables_df = vn.run_sql(tables_query)
                filter_method = None
        else:
            filter_method = None

        result_parts = [f"数据库: {db_name}"]
        result_parts.append(f"表数量: {len(tables_df)}")
        if filter_method:
            result_parts.append(f"过滤方式: {filter_method}\n")
        else:
            result_parts.append("")

        # 遍历每个表，获取列信息
        for _, table_row in tables_df.iterrows():
            table_name = table_row['TABLE_NAME']
            table_comment = table_row['TABLE_COMMENT'] or '无描述'

            # 获取表的列信息
            columns_query = f"""
            SELECT
                COLUMN_NAME,
                COLUMN_TYPE,
                IS_NULLABLE,
                COLUMN_KEY,
                COLUMN_DEFAULT,
                COLUMN_COMMENT
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = '{db_name}' 
              AND TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
            """
            columns_df = vn.run_sql(columns_query)
            
            result_parts.append(f"\n{'='*60}")
            result_parts.append(f"表名: {table_name}")
            result_parts.append(f"说明: {table_comment}")
            result_parts.append(f"列数: {len(columns_df)}")
            result_parts.append("-" * 60)
            
            # 格式化列信息
            for _, col in columns_df.iterrows():
                col_info = f"  • {col['COLUMN_NAME']}"
                col_info += f" ({col['COLUMN_TYPE']})"
                
                if col['COLUMN_KEY'] == 'PRI':
                    col_info += " [主键]"
                elif col['COLUMN_KEY'] == 'UNI':
                    col_info += " [唯一]"
                elif col['COLUMN_KEY'] == 'MUL':
                    col_info += " [索引]"
                
                if col['IS_NULLABLE'] == 'NO':
                    col_info += " [NOT NULL]"
                
                if pd.notna(col['COLUMN_DEFAULT']):
                    col_info += f" [默认: {col['COLUMN_DEFAULT']}]"
                
                if col['COLUMN_COMMENT']:
                    col_info += f"\n    说明: {col['COLUMN_COMMENT']}"
                
                result_parts.append(col_info)
        
        return "\n".join(result_parts)
        
    except Exception as e:
        return f"Failed to get table information: {str(e)}"


@tool
def check_mysql_version() -> str:
    """检查 MySQL 版本及其支持的特性
    
    Returns:
        MySQL 版本信息和支持的语法特性
    """
    vn = get_vanna_client()
    
    # 重试机制（避免连接状态问题）
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = vn.run_sql("SELECT VERSION()")
            
            # 检查结果是否为空
            if result is None or len(result) == 0:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return "Version detection failed: query returned empty result\n Assuming MySQL 5.7 (no CTE support), avoid using WITH clauses"
            
            version = result.iloc[0, 0]
            major_version = int(version.split('.')[0])
            
            # 版本检查，如果 major_version >= 8，则支持 CTE (WITH), 窗口函数 (RANK, ROW_NUMBER)
            if major_version >= 8:
                return f"MySQL {version}\nSupports: CTE (WITH), window functions (RANK, ROW_NUMBER)\nSupports GROUP BY strict mode: ONLY_FULL_GROUP_BY"
            else:
                return f"MySQL {version}\nDoes not support: CTE (WITH), window functions\nSuggest using: subqueries, GROUP BY + LIMIT\nPossible GROUP BY strict mode, columns in SELECT must be in GROUP BY"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            # 最后一次尝试失败，返回默认假设
            return f"Version detection failed: {str(e)}\nAssuming MySQL 5.7 (no CTE support), avoid using WITH clauses\nNote GROUP BY rules"
    
    return "Version detection failed (unknown error)"


# ==================== SQL 执行工具（核心）====================

# 全局互斥锁，防止并发执行 SQL
_sql_execution_lock = threading.Lock()

@tool
def execute_sql(sql: str) -> str:
    """执行 SQL 查询并返回结果
    
    重要: 一次只能执行一个SQL，不要并发调用此工具！
    技术保障: 内部使用互斥锁强制串行执行
    自动分割: 如果传入多条SQL（用分号分隔），会自动逐条执行
    
    Args:
        sql: SQL 查询语句（支持单条或多条，用分号分隔）
        
    Returns:
        查询结果摘要
    """
    # 使用互斥锁强制串行执行，防止并发破坏 MySQL 连接
    with _sql_execution_lock:
        vn = get_vanna_client()
        
        # ==================== SQL 语法检查 ====================
        import re
        
        # 检查是否包含 SET 语句（用户变量）
        if re.search(r'\bSET\s+@', sql, re.IGNORECASE):
            return f"""SQL 语法错误: 禁止使用 SET 语句（MySQL 5.7 限制）

检测到的 SQL:
{sql[:500]}...

错误用法: SET @var = 'value'; SELECT * WHERE col IN (@var);
正确用法: SELECT * WHERE col IN ('value');  ← 直接硬编码值

原因:
1. SET 语句不返回结果集，vn.run_sql() 会返回 None
2. 用户变量可能导致字符集冲突错误

请修改 SQL，直接在 WHERE 子句中使用字面量。"""
        
        # ==================== 智能分割多条 SQL ====================
        # 移除注释并按分号分割
        
        # 移除单行注释（-- 开头）
        sql_no_comments = re.sub(r'--[^\n]*', '', sql)
        
        # 按分号分割（忽略空白语句）
        sql_statements = [
            stmt.strip() 
            for stmt in sql_no_comments.split(';') 
            if stmt.strip()
        ]
        
        # 如果检测到多条 SQL，给出警告并逐条执行
        if len(sql_statements) > 1:
            logger.warning(f"Detected {len(sql_statements)} SQL statements, will execute one by one...")
            
            all_results = []
            for i, stmt in enumerate(sql_statements, 1):
                logger.info(f"\nExecuting {i}/{len(sql_statements)} SQL...")
                result = _execute_single_sql(vn, stmt, max_retries=3)

                # 用中文记录输出
                all_results.append(f"=== 查询 {i} ===\n{result}")
            
            return "\n\n".join(all_results)
        else:
            # 单条 SQL，直接执行
            return _execute_single_sql(vn, sql_statements[0] if sql_statements else sql, max_retries=3)


def _execute_single_sql(vn, sql: str, max_retries: int = 3) -> str:
    """执行单条 SQL（内部函数）"""
    retry_delay = 1  # 秒
    
    for attempt in range(max_retries):
        try:
            df = vn.run_sql(sql)
            
            # 检查返回值是否为 None
            if df is None:
                return f"""SQL执行失败: 查询返回 None

可能原因:
1. SQL中包含注释被过滤后变成空语句
2. MySQL连接返回空结果
3. vanna.run_sql() 内部错误

原始SQL:
{sql[:500]}...

建议: 移除SQL中的注释（--），只保留纯SQL语句"""
            
            row_count = len(df)

            # 🔥 缓存 DataFrame 到全局变量（供 api_server 提取）
            set_last_query_result(df)
            logger.info(f"[execute_sql] 已缓存查询结果 DataFrame，行数: {row_count}")

            # 使用中文记录结果摘要
            result_summary = f"查询成功\n"
            result_summary += f"返回行数: {row_count}\n"
            result_summary += f"列名: {', '.join(df.columns.tolist())}\n\n"

            if row_count > 0:
                result_summary += f"前5行数据:\n{df.head(5).to_string()}\n\n"

                # 添加数据统计
                numeric_cols = df.select_dtypes(include=['number']).columns
            else:
                result_summary += "查询结果为空"

            # 成功执行，返回结果
            return result_summary
            
        except Exception as e:
            error_msg = str(e)
            
            # 特殊处理：'NoneType' object is not iterable（df 为 None）
            if "'NoneType' object is not iterable" in error_msg or "NoneType" in error_msg:
                return f"""SQL执行失败: vn.run_sql() 返回 None

错误信息: {error_msg}

可能原因:
1. SQL 包含注释（--）导致解析失败
2. MySQL 查询返回空但 vanna 未正确处理
3. 数据库连接状态异常

原始SQL（含注释）:
{sql[:500]}...

解决方案: 移除 SQL 中的注释，只保留纯 SQL 语句
例如: 
  -- 这是注释 SELECT * FROM table;
  SELECT * FROM table;"""
            
            # 处理空错误 (0, '') - 通常是连接问题
            if error_msg == "(0, '')" or error_msg == "(0, b'')":
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue  # 重试
                else:
                    return f"""SQL执行失败: MySQL连接错误

错误信息: {error_msg} (空错误)

可能原因:
1. MySQL连接已断开或处于异常状态
2. 之前的查询导致连接状态异常
3. 并发查询破坏了连接

已尝试 {max_retries} 次重试，仍然失败。

SQL语句:
{sql[:200]}...

建议:
1. 重新启动Agent，重新建立数据库连接
2. 检查是否有并发执行的SQL
3. 确保之前的SQL执行完全结束"""
            
            # 检查是否是并发错误（Packet sequence number）
            elif "Packet sequence number wrong" in error_msg or "packet" in error_msg.lower():
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue  # 重试
                else:
                    return f"""SQL执行失败: 连接并发冲突
                
错误信息: {error_msg}

原因: MySQL连接不支持并发查询，请确保：
1. 一次只执行一个 execute_sql 工具调用
2. 等待上一个SQL完全执行完成后再执行下一个

已尝试 {max_retries} 次重试,仍然失败。

建议: 
- 检查是否同时提交了多个 execute_sql 调用
- 如需执行多个SQL，请按顺序逐个执行"""
            
            # 检查是否是GROUP BY错误
            elif "isn't in GROUP BY" in error_msg or "ONLY_FULL_GROUP_BY" in error_msg:
                return f"""SQL执行失败: GROUP BY语法错误

错误信息: {error_msg}

原因: MySQL 5.7+ 启用了 ONLY_FULL_GROUP_BY 模式

规则: SELECT中的非聚合列必须出现在GROUP BY中

错误SQL示例:
SELECT a, b, MAX(c) FROM t GROUP BY a  (b未分组)

正确写法:
方案1: SELECT a, b, MAX(c) FROM t GROUP BY a, b  
方案2: SELECT a, MAX(c) FROM t GROUP BY a  
方案3: SELECT a, ANY_VALUE(b), MAX(c) FROM t GROUP BY a  

请检查你的SQL:
{sql[:200]}...

建议: 修改SQL，确保所有非聚合列都在GROUP BY中"""
            
            # 检查是否是CTE/WITH子句错误（MySQL 5.7不支持）
            elif "WITH" in sql.upper() and ("syntax" in error_msg.lower() or "near" in error_msg.lower()):
                return f"""SQL执行失败: CTE（WITH子句）语法不支持

错误信息: {error_msg}

原因: MySQL 5.7.44 不支持 WITH 子句（Common Table Expression）

你的SQL使用了:
{sql[:300]}...

MySQL 5.7 替代方案:

方案1 - 使用嵌套子查询:
-- 错误: WITH temp AS (SELECT ...) SELECT * FROM temp
-- 正确: SELECT * FROM (SELECT ...) AS temp

方案2 - 使用临时表:
CREATE TEMPORARY TABLE temp_table AS SELECT ...;
SELECT * FROM temp_table;

方案3 - 直接在FROM子句中使用子查询:
SELECT t1.*, t2.* 
FROM (SELECT ... FROM table1) AS t1
JOIN (SELECT ... FROM table2) AS t2

请立即重新生成SQL，避免使用WITH关键字！"""
            
            # 其他错误
            else:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue  # 重试
                else:
                    return f"""SQL执行失败: {error_msg}

SQL语句:
{sql[:200]}...

已尝试 {max_retries} 次执行，仍然失败。

请检查:
1. SQL语法是否正确
2. 表名、列名是否存在
3. 数据类型是否匹配
4. JOIN条件是否正确"""
    
    # 理论上不会到达这里（循环中已包含所有返回情况）
    return f"SQL执行失败: 未知错误"


@tool
def validate_sql_syntax(sql: str) -> str:
    """验证 SQL 语法是否正确（不执行）
    
    Args:
        sql: SQL 查询语句
        
    Returns:
        语法验证结果
    """
    import re
    
    # 安全性检查
    dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 
                         'TRUNCATE', 'CREATE', 'GRANT', 'REVOKE']
    
    sql_upper = sql.upper()
    for keyword in dangerous_keywords:
        if re.search(rf'\b{keyword}\b', sql_upper):
            return f"安全风险: SQL包含危险操作 {keyword}"
    
    # 基础语法检查
    if not sql.strip():
        return "SQL为空"
    
    if not re.search(r'\bSELECT\b', sql_upper):
        return "SQL必须以SELECT开头"
    
    # 括号匹配检查
    if sql.count('(') != sql.count(')'):
        return "括号不匹配"
    
    return "语法检查通过（基础验证）"
