#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Ollama API 是否正常工作
"""

import requests
import json

# API 端点
url = "http://localhost:11434/api/generate"

# 请求数据
data = {
    "model": "qwen3.5",  # 使用更简单的模型名称
    "prompt": "你好",  # 使用更简单的prompt
    "stream": False
}

try:
    print("正在测试 Ollama API...")
    print(f"URL: {url}")
    print(f"模型: {data['model']}")
    print(f"Prompt: {data['prompt']}")
    
    response = requests.post(url, json=data, timeout=300)
    print(f"\nAPI 响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nAPI 响应成功！")
        print(f"生成的内容: {result.get('response', '无')}")
    else:
        print(f"\nAPI 响应失败: {response.text}")
        
except requests.exceptions.ConnectionError as e:
    print(f"\n连接错误: 无法连接到 Ollama 服务，请确保服务正在运行: {e}")
except requests.exceptions.Timeout as e:
    print(f"\n超时错误: API 调用超时，请检查网络连接和 Ollama 服务状态: {e}")
except Exception as e:
    print(f"\n测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成！")
