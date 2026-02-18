"""
工具函数模块
提供各种辅助功能
"""
import logging
logger = logging.getLogger(__name__)
from typing import Any, Dict, Optional
import json


def pretty_print(message: str, title: Optional[str] = None, level: str = "info", width: int = 70):
    """
    格式化打印流程日志
    
    Args:
        message: 要打印的消息
        title: 可选的标题
        level: 日志级别 (info, success, error, warning, thinking, step, tool, result)
        width: 打印宽度
    """
    # 定义不同级别的图标和颜色
    icons = {
        "info": "ℹ️ ",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️ ",
        "thinking": "🤔",
        "step": "🔧",
        "tool": "📊",
        "result": "💡",
        "start": "🚀",
        "finish": "🏁",
        "query": "📝",
        "debug": "🔍",
        "ai": "🤖",
        "code": "💻",
        "data": "📁"
    }
    
    icon = icons.get(level, "▪️ ")
    
    # 如果有标题，先打印标题
    if title:
        logger.info("\n" + "="*width)
        logger.info(f"{icon} {title}")
        logger.info("="*width)
    
    # 打印消息
    if message:
        # 如果消息过长，自动换行
        lines = message.split('\n')
        for line in lines:
            if title:
                logger.info(f"   {line}")
            else:
                logger.info(f"{icon} {line}")
    
    # 如果只有标题没有消息，添加空行
    if title and not message:
        logger.info("")


def format_dataframe_result(result: Any) -> str:
    """
    格式化DataFrame结果为易读的字符串
    
    Args:
        result: 任意类型的结果
        
    Returns:
        格式化后的字符串
    """
    if result is None:
        return "操作成功完成，无返回值"
    
    # 转换为字符串
    result_str = str(result)
    
    # 限制输出长度
    max_length = 5000
    if len(result_str) > max_length:
        result_str = result_str[:max_length] + f"\n...(输出过长，已截断，总长度: {len(result_str)}字符)"
    
    return result_str


def print_section(title: str, content: str = "", width: int = 80):
    """
    打印格式化的章节
    
    Args:
        title: 章节标题
        content: 章节内容
        width: 宽度
    """
    logger.info("\n" + "=" * width)
    logger.info(f"  {title}")
    logger.info("=" * width)
    if content:
        logger.info(content)
    logger.info("")


def print_info(message: str):
    """打印信息"""
    logger.info(f"ℹ️  {message}")


def print_success(message: str):
    """打印成功消息"""
    logger.info(f"✅ {message}")


def print_error(message: str):
    """打印错误消息"""
    logger.error(f"❌ 错误: {message}")


def print_warning(message: str):
    """打印警告消息"""
    logger.warning(f"⚠️  警告: {message}")


def print_thinking(message: str):
    """打印思考消息"""
    logger.info(f"🤔 {message}")


def print_result(message: str):
    """打印结果消息"""
    logger.info(f"📊 结果:\n{message}")
