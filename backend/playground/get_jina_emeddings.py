import requests
import json

# API 端点
url = "http://localhost:8898/v1/embeddings"

# 请求数据
payload = {
    "inputs": [
        {"text": "人工智能正在改变世界1"},
        {"text": "Machine learning is a subset of AI"}
    ],
    "normalize": True,
    "pooling": "mean"
}

# 发送 POST 请求
response = requests.post(url, json=payload)

# 打印结果
if response.status_code == 200:
    result = response.json()
    print(f"成功获取 {len(result['embeddings'])} 个向量")
    print(f"向量维度: {len(result['embeddings'][0])}")
    print(f"第一个向量的前10个值: {result['embeddings'][0][:10]}")
else:
    print(f"请求失败: {response.status_code}")
    print(response.text)