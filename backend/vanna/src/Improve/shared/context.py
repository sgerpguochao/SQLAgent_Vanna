"""
全局上下文管理
所有模块共享的 Vanna 客户端、API Key 和 LLM 实例
"""
import logging
logger = logging.getLogger(__name__)
from typing import Optional

# ==================== 全局单例变量 ====================
_vanna_client: Optional[any] = None
_api_key: Optional[str] = None
_mysql_version_cache: Optional[str] = None  # 缓存 MySQL 版本信息
_llm_instance: Optional[any] = None  # 全局 LLM 实例（避免重复创建）
_last_query_result: Optional[any] = None  # 缓存最后一次查询结果（DataFrame）


# ==================== Vanna 客户端管理 ====================

def set_vanna_client(vn):
    """设置全局 Vanna 客户端
    
    Args:
        vn: Vanna 客户端实例
    """
    global _vanna_client
    _vanna_client = vn


def get_vanna_client():
    """获取全局 Vanna 客户端
    
    Returns:
        Vanna 客户端实例
        
    Raises:
        RuntimeError: 如果客户端未初始化
    """
    if _vanna_client is None:
        raise RuntimeError("Vanna 客户端未初始化，请先调用 set_vanna_client()")
    return _vanna_client


# ==================== API Key 管理 ====================

def set_api_key(api_key: str):
    """设置全局 API Key
    
    Args:
        api_key: OpenAI API key
    """
    global _api_key
    _api_key = api_key


def get_api_key() -> Optional[str]:
    """获取全局 API Key
    
    Returns:
        API key 字符串，如果未设置则返回 None
    """
    return _api_key


# ==================== LLM 实例管理 ====================

def set_llm_instance(llm):
    """设置全局 LLM 实例（避免重复创建）
    
    Args:
        llm: ChatOpenAI 或其他 LLM 实例
    """
    global _llm_instance
    _llm_instance = llm


def get_llm_instance():
    """获取全局 LLM 实例
    
    Returns:
        LLM 实例，如果未设置则返回 None
    """
    return _llm_instance


# ==================== MySQL 版本缓存管理 ====================

def get_mysql_version_cache() -> Optional[str]:
    """获取缓存的 MySQL 版本信息"""
    return _mysql_version_cache


def set_mysql_version_cache(version_info: str):
    """设置 MySQL 版本缓存"""
    global _mysql_version_cache
    _mysql_version_cache = version_info


def clear_mysql_version_cache():
    """清除 MySQL 版本缓存"""
    global _mysql_version_cache
    _mysql_version_cache = None


# ==================== 查询结果缓存管理 ====================

def set_last_query_result(df):
    """缓存最后一次查询结果

    Args:
        df: pandas DataFrame 查询结果
    """
    global _last_query_result
    _last_query_result = df
    logger.info(f"[查询缓存] 已缓存查询结果，行数: {len(df) if df is not None else 0}")


def get_last_query_result():
    """获取最后一次查询结果

    Returns:
        pandas DataFrame 或 None
    """
    return _last_query_result


def clear_last_query_result():
    """清除查询结果缓存"""
    global _last_query_result
    _last_query_result = None
    logger.info("[查询缓存] 已清除查询结果缓存")
