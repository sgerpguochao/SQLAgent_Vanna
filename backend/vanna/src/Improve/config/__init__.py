"""
配置模块
包含系统配置和常量
"""

import logging
logger = logging.getLogger(__name__)
from .prompts import SYSTEM_PROMPT
from .test_questions import TEST_QUESTIONS

__all__ = [
    'SYSTEM_PROMPT',
    'TEST_QUESTIONS',
]
