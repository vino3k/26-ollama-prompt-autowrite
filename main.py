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
LOG_FILE = os.path.join(BASE_DIR, "monitor.log")
LOCK_FILE = os.path.join(BASE_DIR, ".monitor.lock")

# Ollama API配置
OLLAMA_API_URL = "http://192.168.2.111:11434/api/generate"

def log_message(message):
    """记录日志到文件和控制台"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    
    # 输出到控制台
    print(log_line.strip())
    
    # 写入日志文件
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line)
    except Exception as e:
        print(f"写入日志失败: {e}")

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
        base_url = OLLAMA_API_URL.split('/api/')[0]
        response = requests.get(f"{base_url}/api/tags", timeout=10)
        return response.status_code == 200
    except requests.exceptions.Timeout:
        log_message("Ollama服务超时")
        return False
    except requests.exceptions.ConnectionError:
        log_message("无法连接到Ollama服务")
        return False
    except Exception as e:
        log_message(f"检查Ollama服务时出错: {e}")
        return False

def acquire_lock():
    """获取运行锁，防止重复执行（跨平台实现）"""
    try:
        # 尝试创建锁文件，如果文件已存在且时间戳较新，则认为有其他进程在运行
        if os.path.exists(LOCK_FILE):
            # 检查锁文件的创建时间，如果超过1小时则认为是旧锁，可以删除
            lock_age = time.time() - os.path.getctime(LOCK_FILE)
            if lock_age < 3600:
                log_message("检测到已有脚本在运行，跳过本次执行")
                return False
            else:
                # 旧锁文件，删除它
                os.remove(LOCK_FILE)
        
        # 创建新的锁文件
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        return True
    except Exception as e:
        log_message(f"获取锁失败: {e}")
        return False

def release_lock():
    """释放运行锁"""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        log_message(f"释放锁失败: {e}")

def run_process_script():
    """执行process_articles.py脚本"""
    if not acquire_lock():
        return False
    
    try:
        log_message("发现新文件，开始执行处理脚本...")
        
        result = subprocess.run(
            [sys.executable, PROCESS_SCRIPT],
            capture_output=True,
            text=True,
            timeout=3600,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            log_message("脚本执行成功")
            if result.stdout:
                log_message(f"脚本输出:\n{result.stdout}")
            return True
        else:
            log_message(f"脚本执行失败，返回码: {result.returncode}")
            if result.stderr:
                log_message(f"错误信息:\n{result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        log_message("脚本执行超时")
        return False
    except Exception as e:
        log_message(f"执行脚本时出错: {e}")
        return False
    finally:
        release_lock()

def main():
    """主函数"""
    log_message("=" * 60)
    log_message("Ollama 文章处理监控系统启动")
    log_message("=" * 60)
    log_message(f"监控目录: {NEW_DIR}")
    log_message(f"处理脚本: {PROCESS_SCRIPT}")
    log_message(f"检查间隔: 3600秒")
    log_message(f"日志文件: {LOG_FILE}")
    log_message("=" * 60)
    
    if not os.path.exists(NEW_DIR):
        log_message(f"警告: 监控目录不存在，已创建: {NEW_DIR}")
        os.makedirs(NEW_DIR, exist_ok=True)
    
    if not os.path.exists(PROCESS_SCRIPT):
        log_message(f"错误: 处理脚本不存在: {PROCESS_SCRIPT}")
        return
    
    last_files_info = scan_new_directory()
    log_message(f"当前文件数: {len(last_files_info)}")
    
    while True:
        try:
            time.sleep(3600)
            
            current_files_info = scan_new_directory()
            
            if current_files_info:
                log_message(f"检测到目录中有文件 ({len(current_files_info)} 个)")
                
                if check_ollama_service():
                    run_process_script()
                else:
                    log_message("Ollama服务不可用，跳过本次处理")
            else:
                log_message("目录中无文件")
        
        except KeyboardInterrupt:
            log_message("监控系统已停止")
            break
        except Exception as e:
            log_message(f"监控出错: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
