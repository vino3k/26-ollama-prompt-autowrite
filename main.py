#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主监控脚本：定时监控 new 目录，如果有新文件就执行 process_articles.py
所有可配置常量统一从 config.json 读取。
"""

import os
import sys
import json
import time
import hashlib
import subprocess
import requests
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass

# ===== 配置加载 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def load_config(path: str = CONFIG_PATH) -> dict:
    """加载 config.json；失败则抛出异常终止进程。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"[FATAL] 加载 config.json 失败({path}): {e}") from e

CFG = load_config()

def cfg_get(*keys, default=None):
    cur = CFG
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

# ===== 目录与路径 =====
NEW_DIR = os.path.join(BASE_DIR, "new")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
PROCESS_SCRIPT = os.path.join(BASE_DIR, "process_articles.py")
LOG_FILE = os.path.join(LOGS_DIR, "monitor.log")
LOCK_FILE = os.path.join(LOGS_DIR, ".monitor.lock")

# ===== 时间参数（全部从 config.json 读取，禁止裸数字）=====
SCAN_INTERVAL = cfg_get("monitor", "scan_interval_seconds", default=3600)
LOCK_MAX_AGE = cfg_get("monitor", "lock_max_age_seconds", default=3600)
PROCESS_TIMEOUT = cfg_get("monitor", "process_timeout_seconds", default=3600)
RECOVER_WAIT = cfg_get("monitor", "recover_wait_seconds", default=60)
ALLOWED_EXTS = tuple(cfg_get("monitor", "process_file_exts", default=[".md", ".json"]))

# ===== Ollama API 配置 =====
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", cfg_get("llm", "ollama", "host_default", default="192.168.2.111"))
OLLAMA_PORT = os.environ.get("OLLAMA_PORT", str(cfg_get("llm", "ollama", "port_default", default=11434)))
OLLAMA_API_URL = os.environ.get(
    "OLLAMA_API_URL",
    f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"
)
HEALTH_CHECK_TIMEOUT = cfg_get("llm", "ollama", "health_check_timeout_seconds", default=10)

# LLM 提供方判断（agres 模式下不需要检查 Ollama）
LLM_PROVIDER = os.environ.get(
    cfg_get("llm", "provider_env", default="LLM_PROVIDER"),
    "ollama"
).lower()


def log_message(message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    print(log_line.strip())
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line)
    except Exception as e:
        print(f"写入日志失败: {e}")


def get_file_hash(file_path):
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        # 文件名含非法字节（挂载卷 emoji 等）时无法 open：标记存在，
        # 交给 process_articles.py 的 sanitize_filenames 自动重命名修复
        return "unreadable"


def scan_new_directory():
    files_info = {}
    if not os.path.exists(NEW_DIR):
        return files_info
    for root, dirs, files in os.walk(NEW_DIR):
        for file in files:
            if file.endswith(ALLOWED_EXTS):
                file_path = os.path.join(root, file)
                file_hash = get_file_hash(file_path)
                if file_hash:
                    relative_path = os.path.relpath(file_path, NEW_DIR)
                    files_info[relative_path] = file_hash
    return files_info


def check_ollama_service():
    """检查 Ollama 服务是否可用。使用 agres 时直接跳过。"""
    if LLM_PROVIDER != "ollama":
        return True
    try:
        base_url = OLLAMA_API_URL.split('/api/')[0]
        response = requests.get(f"{base_url}/api/tags", timeout=HEALTH_CHECK_TIMEOUT)
        return response.status_code == 200
    except requests.exceptions.Timeout:
        log_message("Ollama 服务检查超时")
        return False
    except requests.exceptions.ConnectionError:
        log_message("无法连接到 Ollama 服务")
        return False
    except Exception as e:
        log_message(f"检查 Ollama 服务时出错: {e}")
        return False


def acquire_lock():
    try:
        if os.path.exists(LOCK_FILE):
            lock_age = time.time() - os.path.getctime(LOCK_FILE)
            if lock_age < LOCK_MAX_AGE:
                log_message("检测到已有脚本在运行，跳过本次执行")
                return False
            os.remove(LOCK_FILE)
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except Exception as e:
        log_message(f"获取锁失败: {e}")
        return False


def release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        log_message(f"释放锁失败: {e}")


def run_process_script():
    if not acquire_lock():
        return False
    try:
        log_message("发现新文件，开始执行处理脚本...")
        result = subprocess.run(
            [sys.executable, PROCESS_SCRIPT],
            capture_output=True,
            text=True,
            timeout=PROCESS_TIMEOUT,
            encoding='utf-8'
        )
        if result.returncode == 0:
            log_message("脚本执行成功")
            if result.stdout:
                log_message(f"脚本输出:\n{result.stdout}")
            return True
        log_message(f"脚本执行失败，返回码: {result.returncode}")
        if result.stderr:
            log_message(f"错误信息:\n{result.stderr}")
        return False
    except subprocess.TimeoutExpired:
        log_message(f"脚本执行超时（{PROCESS_TIMEOUT}s）")
        return False
    except Exception as e:
        log_message(f"执行脚本时出错: {e}")
        return False
    finally:
        release_lock()


def main():
    log_message("=" * 60)
    log_message(f"文章处理监控系统启动 (LLM: {LLM_PROVIDER})")
    log_message("=" * 60)
    log_message(f"监控目录: {NEW_DIR}")
    log_message(f"处理脚本: {PROCESS_SCRIPT}")
    log_message(f"检查间隔: {SCAN_INTERVAL}s")
    log_message(f"锁最大存活: {LOCK_MAX_AGE}s")
    log_message(f"单次处理超时: {PROCESS_TIMEOUT}s")
    log_message(f"日志文件: {LOG_FILE}")
    log_message("=" * 60)

    if not os.path.exists(NEW_DIR):
        log_message(f"警告: 监控目录不存在，已创建: {NEW_DIR}")
        os.makedirs(NEW_DIR, exist_ok=True)

    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR, exist_ok=True)

    if not os.path.exists(PROCESS_SCRIPT):
        log_message(f"错误: 处理脚本不存在: {PROCESS_SCRIPT}")
        return

    last_files_info = scan_new_directory()
    log_message(f"当前文件数: {len(last_files_info)}")

    if last_files_info:
        log_message(f"启动时检测到目录中有文件 ({len(last_files_info)} 个)")
        if check_ollama_service():
            run_process_script()
        else:
            log_message("LLM 服务不可用，跳过启动时的处理")

    while True:
        try:
            time.sleep(SCAN_INTERVAL)
            current_files_info = scan_new_directory()
            if current_files_info:
                log_message(f"检测到目录中有文件 ({len(current_files_info)} 个)")
                if check_ollama_service():
                    run_process_script()
                else:
                    log_message("LLM 服务不可用，跳过本次处理")
            else:
                log_message("目录中无文件")
        except KeyboardInterrupt:
            log_message("监控系统已停止")
            break
        except Exception as e:
            log_message(f"监控出错: {e}")
            time.sleep(RECOVER_WAIT)


if __name__ == "__main__":
    main()
