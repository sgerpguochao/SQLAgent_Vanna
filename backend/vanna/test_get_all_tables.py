"""
测试 get_all_tables_info 工具的输出格式
"""
import os
import sys
sys.path.insert(0, '/home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/backend/vanna')

from dotenv import load_dotenv
load_dotenv('/home/ubuntu/workspace/my_vanna_cc/SQLAgent_Vanna_1/backend/vanna/.env')

from src.Improve.clients import create_vanna_client
from src.Improve.tools.database_tools import get_all_tables_info
from src.Improve.shared import set_vanna_client

# 创建 Vanna 客户端
vn = create_vanna_client(
    openai_api_key=os.getenv('API_KEY'),
    openai_base_url=os.getenv('BASE_URL'),
    model=os.getenv('LLM_MODEL', 'gpt-4o-mini'),
    max_tokens=int(os.getenv('LLM_MAX_TOKENS', '14000')),
    milvus_uri=os.getenv('MILVUS_URI'),
    embedding_api_url=os.getenv('EMBEDDING_API_URL'),
)

# 设置全局客户端
set_vanna_client(vn)

# 连接数据库
vn.connect_to_mysql(
    host=os.getenv('MYSQL_HOST'),
    dbname='ai_sales_data',
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    port=int(os.getenv('MYSQL_PORT', '3306')),
)

# 测试问题
question = "销售额最高的前10个产品"

print("=" * 60)
print(f"测试问题: {question}")
print("=" * 60)

# 调用 get_all_tables_info
result = get_all_tables_info.invoke(question)

print("\n原始输出:")
print(result[:500])

# 模拟中间件的解析逻辑
print("\n" + "=" * 60)
print("模拟中间件解析:")
print("=" * 60)

lines = result.split('\n')
table_names = []
for line in lines:
    if "表名:" in line:
        table_name = line.split("表名:")[-1].strip()
        if table_name and table_name not in table_names:
            table_names.append(table_name)

if table_names:
    simplified = f"已找到 {len(table_names)} 张表: {', '.join(table_names)}"
    print(f"\n简化后输出: {simplified}")
else:
    print("\n未能解析出表名!")
    print(f"检查的行: {[l for l in lines if '表名' in l]}")
