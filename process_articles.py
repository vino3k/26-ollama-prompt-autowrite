#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章处理脚本：使用 Ollama 大模型按照标准模块构成改写文章并移动文件
"""

import os
import shutil
import json
import requests

# 目录路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEW_DIR = os.path.join(BASE_DIR, "new")
OLD_DIR = os.path.join(BASE_DIR, "old")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
STANDARD_FILE = os.path.join(BASE_DIR, "standard-template.txt")

def load_standard_template():
    """
    加载标准模块构成模板
    """
    if os.path.exists(STANDARD_FILE):
        with open(STANDARD_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    print("警告: 标准模板文件不存在: {}".format(STANDARD_FILE))
    return ""

def call_ollama_api(prompt):
    """
    调用 Ollama API 生成内容
    """
    url = "http://192.168.2.111:11434/api/generate"
    data = {
        "model": "qwen3.5:latest",  # 使用正确的模型名称
        "prompt": prompt,
        "stream": False
    }
    
    try:
        print(f"正在调用 Ollama API，URL: {url}")
        print(f"模型: qwen3.5:latest")
        print(f"Prompt 长度: {len(prompt)} 字符")
        
        response = requests.post(url, json=data, timeout=300)
        print(f"API 响应状态码: {response.status_code}")
        
        response.raise_for_status()
        
        result = response.json()
        print(f"API 响应结果: {result.keys()}")
        
        response_text = result.get("response", "")
        print(f"生成内容长度: {len(response_text)} 字符")
        
        if not response_text or len(response_text.strip()) == 0:
            print("警告: API 返回了空内容，可能是请求超时或模型未正常响应")
            return None  # 返回 None 而不是空字符串
        
        return response_text
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: 无法连接到 Ollama 服务，请确保服务正在运行: {e}")
        return None
    except requests.exceptions.Timeout as e:
        print(f"超时错误: API 调用超时，请检查网络连接和 Ollama 服务状态: {e}")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"HTTP 错误: {e}")
        print(f"响应内容: {response.text if 'response' in locals() else '无'}")
        return None
    except Exception as e:
        print(f"调用 Ollama API 失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def process_articles():
    """
    处理所有文章
    """
    # 确保目录存在
    os.makedirs(OLD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 加载标准模块构成
    standard_template = load_standard_template()
    
    # 递归获取new目录中的所有文件
    files_to_process = []
    for root, dirs, files in os.walk(NEW_DIR):
        for file in files:
            if file.endswith('.md') or file.endswith('.json'):  # 处理markdown和json文件
                file_path = os.path.join(root, file)
                # 计算相对路径
                relative_path = os.path.relpath(file_path, NEW_DIR)
                files_to_process.append((file_path, relative_path))
    
    if not files_to_process:
        print("new目录中没有markdown文件")
        return
    
    print(f"发现 {len(files_to_process)} 个文件需要处理")
    
    for file_path, relative_path in files_to_process:
        file_name = os.path.basename(file_path)
        print(f"\n处理文件: {relative_path}")
        
        # 读取原文件内容
        content = ""
        title = "未知标题"
        
        if file_path.endswith('.json'):
            # 处理JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            content = data.get('text', '')
            title = data.get('title', '未知标题')
        else:
            # 处理Markdown文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # 提取标题（假设标题在文件的第一行，以#开头）
            lines = content.split('\n')
            for line in lines:
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
        
        # 构建 prompt
        prompt = f"""
你是一位资深知识产权内容策略师，擅长将专业内容改写成符合移动端阅读习惯、具有传播力的爆款文章。你是一位资深知识产权内容策略师，擅长将专业内容改写成符合移动端阅读习惯、具有传播力的爆款文章。

## 任务
将以下文章按照标准模块结构改写，融入知识产权代理业务场景，输出完整Markdown格式。

## 标准模块结构
""{standard_template}""

## 待改写内容
""{content}""

## 公司背景
知识产权综合代理机构，主营业务：商标代理、专利申请、版权登记、体系认证、科创项目申报、海外知识产权布局。

## 内容规范

### 结构要求
1. **开头**：使用SCQA模型（情境→冲突→问题→答案）构建引人入胜的开篇
2. **正文**：采用金字塔结构，结论先行，逐层展开论据
3. **排版**：使用多级小标题、加粗重点、emoji点缀，适配移动端阅读
4. **模块**：严格遵循上述标准模块结构组织内容

### 内容要求
1. 保持原文核心信息不变，不增删关键事实
2. 将知识产权业务（商标/专利/版权/认证/科创/海外）自然融入内容场景
3. 引用外部信息时必须标注来源
4. 语言风格：专业且有温度，避免生硬说教

### 禁止事项
1. 出现任何机构标识、版权声明、年份信息
2. 使用"国家安全警示中心"等类似机构名称
3. 任何可能被解读为冒充国家机构的表述
4. AI说明性文字（如"作为AI助手"）、流水账叙述、代码/字符串
5. 正文中出现"框架""模型""结构"等元描述词汇
6. 正文中出现：“S - 情境、C - 冲突、Q - 问题、A - 答案“等词汇。

## 输出
仅输出改写后的Markdown正文，不要添加任何前言、后记或解释说明。
;
"""
        
        # 调用 Ollama API 生成改写内容
        print("正在调用 Ollama API 改写文章...")
        rewritten_content = call_ollama_api(prompt)
        
        if rewritten_content is None:
            print(f"警告: Ollama API 调用失败，跳过文章 {relative_path}")
            print("请检查 Ollama 服务状态或网络连接")
            continue  # 跳过当前文件，继续处理下一个文件
        
        if not rewritten_content or len(rewritten_content.strip()) == 0:
            print(f"警告: API 返回了空内容，跳过文章 {relative_path}")
            continue  # 跳过当前文件，继续处理下一个文件
        
        # 输出到output目录，保持目录结构，将JSON文件转换为MD格式
        if relative_path.endswith('.json'):
            output_relative_path = relative_path[:-5] + '.md'  # 将.json改为.md
        else:
            output_relative_path = relative_path
        
        output_file_path = os.path.join(OUTPUT_DIR, output_relative_path)
        output_dir = os.path.dirname(output_file_path)
        os.makedirs(output_dir, exist_ok=True)
        
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(rewritten_content)
        print(f"文件已输出到: {output_file_path}")
        
        # 移动文件到old目录，保持目录结构
        old_file_path = os.path.join(OLD_DIR, relative_path)
        old_dir = os.path.dirname(old_file_path)
        os.makedirs(old_dir, exist_ok=True)
        
        # 如果文件已存在，先删除
        if os.path.exists(old_file_path):
            os.remove(old_file_path)
            print(f"删除了old目录中的旧文件: {relative_path}")
        
        shutil.move(file_path, old_file_path)
        print(f"文件已从new目录移动到old目录: {relative_path}")
    
    print("\n所有文件处理完成！")

if __name__ == "__main__":
    process_articles()
