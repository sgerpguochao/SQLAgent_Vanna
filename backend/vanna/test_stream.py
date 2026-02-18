#!/usr/bin/env python3
"""
测试流式对话接口

演示如何接收 Agent 执行步骤和最终答案
"""

import requests
import json
import sys
import time

API_URL = "http://localhost:8101/api/v1/chat/stream"

def test_stream_chat():
    """测试流式对话"""
    question = """分析25-35岁年龄段的客户群体：
1. 按性别统计各品类（category）的购买偏好（销量TOP5）
2. 对比线上和线下渠道的客单价差异
3. 找出该年龄段退货率最高的3个子品类（sub_category），并分析主要退货原因
4. 统计该群体在不同季节（season）服装上的消费占比"""
    
    print(f"🤖 问题: {question}\n")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        response = requests.post(
            API_URL,
            json={"question": question},
            stream=True,
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP 错误: {response.status_code}")
            print(response.text)
            return
        
        answer_text = ""
        steps = []
        step_times = []
        last_step_time = start_time
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        current_time = time.time()
                        
                        if data['type'] == 'step':
                            # Agent 执行步骤
                            action = data['action']
                            status = data['status']
                            is_temp = data.get('temp', False)
                            is_update = data.get('update', False)
                            duration_ms = data.get('duration_ms')
                            
                            if status == '准备中' and is_temp:
                                # 临时状态（立即推送，等待 LLM 描述）
                                steps.append(action)
                                last_step_time = current_time
                                print(f"🔄 {action}", end='', flush=True)
                            
                            elif status == '进行中' and is_update:
                                # LLM 生成的描述到了，更新之前的临时状态
                                print(f"\r✏️  {action}...", flush=True)
                            
                            elif status == '进行中' and not is_temp:
                                # 直接进入进行中（没有经过准备状态）
                                steps.append(action)
                                last_step_time = current_time
                                print(f"⏳ {action}...")
                            
                            elif status == '完成':
                                elapsed = current_time - last_step_time
                                step_times.append(elapsed)
                                if duration_ms:
                                    print(f"✅ {action} ({duration_ms:.0f}ms)")
                                else:
                                    print(f"✅ {action} ({elapsed:.1f}s)")
                        
                        elif data['type'] == 'answer':
                            # 答案内容（逐字符）
                            if not answer_text:
                                print("\n" + "=" * 60)
                                print("📝 最终答案:\n")
                            answer_text += data['content']
                            # 实时打印（打字机效果）
                            print(data['content'], end='', flush=True)
                        
                        elif data['type'] == 'done':
                            # 完成
                            total_elapsed = time.time() - start_time
                            print("\n\n" + "=" * 60)
                            print(f"✅ 对话完成（总耗时: {total_elapsed:.1f}s）")
                        
                        elif data['type'] == 'error':
                            # 错误
                            print(f"\n❌ 错误: {data['message']}")
                    
                    except json.JSONDecodeError as e:
                        print(f"⚠️  JSON 解析错误: {e}")
                        print(f"   原始数据: {data_str[:100]}")
                        continue
        
        print(f"\n\n📊 统计:")
        print(f"   执行步骤数: {len(steps)}")
        if step_times:
            print(f"   平均步骤耗时: {sum(step_times)/len(step_times):.1f}s")
        print(f"   答案长度: {len(answer_text)} 字符")
        
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（120秒）")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败，请确保 API 服务正在运行")
        print(f"   URL: {API_URL}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_stream_chat()
