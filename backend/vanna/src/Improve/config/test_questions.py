import logging
logger = logging.getLogger(__name__)
"""
测试问题集
"""

TEST_QUESTIONS = {
    "electronics_simple": "小米品牌的总销量是多少？",
    
    "electronics_complex": """计算2024年上半年（1-6月），在北京、上海、广州三个城市中，
各品牌的市场份额（按销量计算），并找出每个城市的TOP3品牌，
同时计算这些TOP3品牌的平均折扣率和平均好评率。""",
    
    "clothing_simple": "女性客户的平均消费金额是多少？",
    
    "clothing_complex": """分析25-35岁年龄段的客户群体：
1. 按性别统计各品类（category）的购买偏好（销量TOP5）
2. 对比线上和线下渠道的客单价差异
3. 找出该年龄段退货率最高的3个子品类（sub_category），并分析主要退货原因
4. 统计该群体在不同季节（season）服装上的消费占比""",
}
