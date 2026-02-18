"""
共享资源模块
提供全局单例对象和工具函数
"""
import logging
logger = logging.getLogger(__name__)
from .context import (
    set_vanna_client,
    get_vanna_client,
    set_api_key,
    get_api_key,
    set_llm_instance,
    get_llm_instance,
    get_mysql_version_cache,
    set_mysql_version_cache,
    clear_mysql_version_cache,
    set_last_query_result,
    get_last_query_result,
    clear_last_query_result,
)

__all__ = [
    'set_vanna_client',
    'get_vanna_client',
    'set_api_key',
    'get_api_key',
    'set_llm_instance',
    'get_llm_instance',
    'get_mysql_version_cache',
    'set_mysql_version_cache',
    'clear_mysql_version_cache',
    'set_last_query_result',
    'get_last_query_result',
    'clear_last_query_result',
]
