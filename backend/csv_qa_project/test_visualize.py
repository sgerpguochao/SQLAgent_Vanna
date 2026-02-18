"""
测试对话可视化接口
"""
import logging
logger = logging.getLogger(__name__)
import requests
import json

# API地址
API_URL = "http://192.168.110.131:8000/visualize"

# 测试数据 - 包含明确的数值数据用于生成图表
test_data = {
    "conversation": [
        {
            "user": "查询各产品的销售额",
            "answer": "根据数据分析结果：产品A销售额500万元，产品B销售额380万元，产品C销售额250万元，产品D销售额180万元，产品E销售额120万元。"
        },
        {
            "user": "最近6个月的销售趋势如何",
            "answer": "最近6个月销售数据如下：1月份320万，2月份380万，3月份450万，4月份420万，5月份480万，6月份550万。整体呈上升趋势。"
        }
    ],
    "chart_type": "auto"  # 可以是 bar, pie, line, 或 auto
}

# 额外的测试用例
test_cases = {
    "pie_chart": {
        "conversation": [
            {
                "user": "各地区销售占比",
                "answer": "华东地区占40%，华南地区占25%，华北地区占20%，西南地区占10%，其他地区占5%"
            }
        ],
        "chart_type": "pie"
    },
    "line_chart": {
        "conversation": [
            {
                "user": "展示季度增长趋势",
                "answer": "Q1季度营收100万，Q2季度150万，Q3季度220万，Q4季度280万"
            }
        ],
        "chart_type": "line"
    }
}

def test_visualize(test_name="default", test_config=None):
    """测试可视化接口"""
    if test_config is None:
        test_config = test_data
    
    logger.info(f"\n🧪 测试图表生成接口 [{test_name}]")
    logger.info(f"📡 API地址: {API_URL}")
    logger.info(f"📊 对话轮数: {len(test_config['conversation'])}")
    logger.info(f"📈 图表类型: {test_config.get('chart_type', 'auto')}")
    logger.info("\n发送请求...")
    
    try:
        response = requests.post(
            API_URL,
            json=test_config,
            headers={"Content-Type": "application/json"}
        )
        
        logger.info(f"✅ 状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 保存HTML到文件
            output_file = f"chart_{test_name}.html"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            logger.info(f"✅ 成功生成图表页面！")
            logger.info(f"📄 已保存到: {output_file}")
            logger.info(f"🌐 请在浏览器中打开该文件查看图表")
        else:
            logger.error(f"❌ 请求失败")
            logger.info(f"错误信息: {response.text}")
            return False
    
    except requests.exceptions.ConnectionError:
        logger.info("❌ 无法连接到服务器")
        logger.info("💡 请先启动API服务器: python api_server.py")
        return False
    except Exception as e:
        logger.error(f"❌ 发生错误: {str(e)}")
        return False
    
    return True


def run_all_tests():
    """运行所有测试用例"""
    logger.info("="*70)
    logger.info("🚀 开始测试图表生成接口")
    logger.info("="*70)
    
    # 测试默认用例
    test_visualize("default", test_data)
    
    # 测试其他用例
    for name, config in test_cases.items():
        test_visualize(name, config)
    
    logger.info("\n" + "="*70)
    logger.info("✅ 所有测试完成！")
    logger.info("💡 请在浏览器中查看生成的 chart_*.html 文件")
    logger.info("="*70)


if __name__ == "__main__":
    run_all_tests()
    # test_visualize("default", test_data)
