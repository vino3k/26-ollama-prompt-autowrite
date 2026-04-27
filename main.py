#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主监控脚本：定时监控new目录，如果有新文件就执行process_articles.py
"""

import os
import sys
import time
import hashlib
import subprocess
import requests
from pathlib import Path

# 目录路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEW_DIR = os.path.join(BASE_DIR, "new")
PROCESS_SCRIPT = os.path.join(BASE_DIR, "process_articles.py")

# Ollama API配置
OLLAMA_API_URL = "http://192.168.2.111:11434/api/generate"

def get_file_hash(file_path):
    """获取文件的MD5哈希值"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

def scan_new_directory():
    """扫描new目录，返回所有文件的路径和哈希值"""
    files_info = {}
    if not os.path.exists(NEW_DIR):
        return files_info
    
    for root, dirs, files in os.walk(NEW_DIR):
        for file in files:
            if file.endswith('.md') or file.endswith('.json'):
                file_path = os.path.join(root, file)
                file_hash = get_file_hash(file_path)
                if file_hash:
                    relative_path = os.path.relpath(file_path, NEW_DIR)
                    files_info[relative_path] = file_hash
    return files_info

def check_ollama_service():
    """检查Ollama服务是否可用"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=60)
        return response.status_code == 200
    except Exception:
        return False

def run_process_script():
    """执行process_articles.py脚本"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 发现新文件，开始执行处理脚本...")
    
    try:
        # 使用当前Python解释器执行脚本
        result = subprocess.run(
            [sys.executable, PROCESS_SCRIPT],
            capture_output=True,
            text=True,
            timeout=3600  # 1小时超时
        )
        
        if result.returncode == 0:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 脚本执行成功")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 脚本执行失败，返回码: {result.returncode}")
            if result.stderr:
                print(f"错误信息: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 脚本执行超时")
        return False
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 执行脚本时出错: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("Ollama 文章处理监控系统")
    print("=" * 60)
    print(f"监控目录: {NEW_DIR}")
    print(f"处理脚本: {PROCESS_SCRIPT}")
    print(f"检查间隔: 60秒")
    print("=" * 60)
    
    # 检查必要的目录和文件
    if not os.path.exists(NEW_DIR):
        print(f"错误: 监控目录不存在: {NEW_DIR}")
        os.makedirs(NEW_DIR, exist_ok=True)
        print(f"已创建目录: {NEW_DIR}")
    
    if not os.path.exists(PROCESS_SCRIPT):
        print(f"错误: 处理脚本不存在: {PROCESS_SCRIPT}")
        return
    
    # 记录当前文件状态
    last_files_info = scan_new_directory()
    
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 监控系统启动")
    print(f"当前文件数: {len(last_files_info)}")
    
    while True:
        try:
            # 等待一段时间
            time.sleep(600)  # 每600秒检查一次
            
            # 扫描当前目录状态
            current_files_info = scan_new_directory()
            
            # 检查是否有新文件或文件有变化
            has_changes = False
            
            # 检查新增或修改的文件
            for file_path, file_hash in current_files_info.items():
                if file_path not in last_files_info or last_files_info[file_path] != file_hash:
                    has_changes = True
                    break
            
            # 检查是否有文件被删除（如果需要处理这种情况）
            # for file_path in last_files_info:
            #     if file_path not in current_files_info:
            #         has_changes = True
            #         break
            
            if has_changes:
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 检测到目录变化")
                print(f"文件数量: {len(last_files_info)} -> {len(current_files_info)}")
                
                # 检查Ollama服务是否可用
                if check_ollama_service():
                    run_process_script()
                else:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ollama服务不可用，跳过本次处理")
                
                # 更新文件状态
                last_files_info = scan_new_directory()
            else:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 目录无变化 ({len(current_files_info)} 个文件)")
        
        except KeyboardInterrupt:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 监控系统已停止")
            break
        except Exception as e:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 监控出错: {e}")
            time.sleep(60)  # 出错后等待一段时间再继续

if __name__ == "__main__":
    main()
