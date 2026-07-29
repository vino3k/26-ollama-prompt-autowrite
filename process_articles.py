#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章处理脚本：使用 LLM 按照标准模块构成改写文章并移动文件。
所有可配置常量统一从 config.json 读取；敏感值（API Key）走环境变量。
"""

import os
import sys
import json
import shutil
import requests


def _load_dotenv(env_path):
    """
    简易 .env 加载器（不依赖 python-dotenv）。
    逐行解析 KEY=VALUE，跳过空行和 # 注释行。
    仅当环境变量未设置时才注入（系统环境变量优先级更高）。
    """
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key, value = key.strip(), value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                os.environ.setdefault(key, value)
    except Exception as e:
        print(f"警告: 读取 .env 文件失败: {e}")


# ===== 路径与配置加载 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_load_dotenv(os.path.join(BASE_DIR, ".env"))

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


# ===== 目录 =====
NEW_DIR = os.path.join(BASE_DIR, "new")
OLD_DIR = os.path.join(BASE_DIR, "old")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
STANDARD_FILE = os.path.join(BASE_DIR, cfg_get("security", "template_file", default="standard-template.txt"))
CUSTOMER_SEGMENTS_FILE = os.path.join(BASE_DIR, cfg_get("security", "config_file", default="customer_segments.json"))


# ===== LLM 配置（全部从 config + 环境变量读取）=====
PROVIDER_ENV = cfg_get("llm", "provider_env", default="LLM_PROVIDER")
LLM_PROVIDER = os.environ.get(PROVIDER_ENV, "ollama").lower()

# Ollama
ollama_cfg = cfg_get("llm", "ollama", default={})
OLLAMA_HOST = os.environ.get(
    ollama_cfg.get("host_env", "OLLAMA_HOST"),
    ollama_cfg.get("host_default", "192.168.2.111"),
)
OLLAMA_PORT = os.environ.get(
    ollama_cfg.get("port_env", "OLLAMA_PORT"),
    str(ollama_cfg.get("port_default", 11434)),
)
OLLAMA_MODEL = os.environ.get(
    ollama_cfg.get("model_env", "OLLAMA_MODEL"),
    ollama_cfg.get("model_default", "qwen3.5:latest"),
)
OLLAMA_API_URL = os.environ.get(
    ollama_cfg.get("api_url_env", "OLLAMA_API_URL"),
    f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate",
)
OLLAMA_TIMEOUT = ollama_cfg.get("request_timeout_seconds", 300)

# Agnes
agnes_cfg = cfg_get("llm", "agnes", default={})
AGNES_API_KEY = os.environ.get(agnes_cfg.get("api_key_env", "AGNES_API_KEY"), "")
AGNES_API_URL = agnes_cfg.get("api_url", "https://apihub.agnes-ai.cn/v1/chat/completions")
AGNES_MODEL = agnes_cfg.get("model", "agnes-2.0-flash")
AGNES_MAX_TOKENS = agnes_cfg.get("max_tokens", 4096)
AGNES_TEMPERATURE = agnes_cfg.get("temperature", 0.7)
AGNES_THINKING = agnes_cfg.get("thinking", True)
AGNES_TIMEOUT = agnes_cfg.get("request_timeout_seconds", 300)

# 重试 / 校验
retry_cfg = cfg_get("llm", "retry", default={})
MAX_RETRY = retry_cfg.get("max_attempts", 2)
MIN_BENEFIT_HITS = retry_cfg.get("min_benefit_hits", 3)
DEFAULT_SYSTEM_PROMPT = retry_cfg.get(
    "default_system_prompt",
    "你是一位资深知识产权内容策略师，擅长将专业内容改写成符合移动端阅读习惯、具有传播力的爆款文章。",
)

# 内容规则
BENEFIT_KEYWORDS = cfg_get(
    "content", "benefit_keywords",
    default=[],
)


def load_standard_template():
    if os.path.exists(STANDARD_FILE):
        with open(STANDARD_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    print(f"警告: 标准模板文件不存在: {STANDARD_FILE}")
    return ""


def load_customer_segments():
    if os.path.exists(CUSTOMER_SEGMENTS_FILE):
        with open(CUSTOMER_SEGMENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    print(f"警告: 客户群体配置文件不存在: {CUSTOMER_SEGMENTS_FILE}")
    return {}


def identify_customer_segment(content, customer_segments):
    if not customer_segments:
        return None, None
    candidate_ids = [sid for sid in customer_segments.keys() if sid != "general"]
    scores = {}
    for sid in candidate_ids:
        keywords = customer_segments[sid].get("keywords", [])
        if not keywords:
            continue
        score = sum(1 for kw in keywords if kw and kw in content)
        scores[sid] = score
    best_id, best_score = None, 0
    for sid, score in scores.items():
        if score > best_score:
            best_score, best_id = score, sid
    if best_id is None:
        if "general" in customer_segments:
            return "general", customer_segments["general"]
        return None, None
    return best_id, customer_segments[best_id]


def count_benefit_hits(content):
    if not content:
        return 0
    return sum(1 for kw in BENEFIT_KEYWORDS if kw and kw in content)


def apply_title_prefix(content, prefix):
    if not prefix:
        return content
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('# '):
            if prefix not in line:
                lines[i] = f"# {prefix}{line[2:]}"
            break
    return '\n'.join(lines)


def build_frontmatter(segment_id, seg, title):
    if not seg:
        return ""
    tags = seg.get("tags", [])
    label = seg.get("label", "通用")
    lines = ["---"]
    lines.append(f'title: "{title.replace(chr(34), chr(92) + chr(34))}"')
    lines.append(f'customer_segment: "{segment_id or "general"}"')
    lines.append(f'customer_label: "{label}"')
    if tags:
        lines.append('tags:')
        for t in tags:
            lines.append(f'  - {t}')
    lines.append('---')
    lines.append('')
    return '\n'.join(lines)


def call_ollama_api(prompt):
    """调用本地 Ollama 接口。URL 必须从 config + 环境变量解析，禁止硬编码。"""
    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    try:
        print(f"正在调用 Ollama API，URL: {OLLAMA_API_URL}")
        print(f"模型: {OLLAMA_MODEL}")
        print(f"Prompt 长度: {len(prompt)} 字符")
        response = requests.post(OLLAMA_API_URL, json=data, timeout=OLLAMA_TIMEOUT)
        print(f"API 响应状态码: {response.status_code}")
        response.raise_for_status()
        result = response.json()
        response_text = result.get("response", "")
        print(f"生成内容长度: {len(response_text)} 字符")
        return response_text if response_text and response_text.strip() else None
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: 无法连接到 Ollama 服务: {e}")
    except requests.exceptions.Timeout as e:
        print(f"超时错误: Ollama API 调用超时({OLLAMA_TIMEOUT}s): {e}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP 错误: {e}")
    except Exception as e:
        print(f"调用 Ollama API 失败: {e}")
        import traceback
        traceback.print_exc()
    return None


def call_agnes_api(prompt, system_prompt=None):
    """调用云端 Agnes-2.0-Flash。URL 与所有参数从 config + 环境变量读取。"""
    if not AGNES_API_KEY:
        print(f"错误: 未设置环境变量 {agnes_cfg.get('api_key_env', 'AGNES_API_KEY')}，无法调用 Agnes API")
        return None

    system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
    headers = {
        "Authorization": f"Bearer {AGNES_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": AGNES_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": AGNES_TEMPERATURE,
        "max_tokens": AGNES_MAX_TOKENS,
        "stream": False,
    }
    if AGNES_THINKING:
        data["chat_template_kwargs"] = {"enable_thinking": True}

    try:
        print(f"正在调用 Agnes API，URL: {AGNES_API_URL}")
        print(f"模型: {AGNES_MODEL}, Thinking: {AGNES_THINKING}")
        print(f"Prompt 长度: {len(prompt)} 字符")
        response = requests.post(AGNES_API_URL, headers=headers, json=data, timeout=AGNES_TIMEOUT)
        print(f"API 响应状态码: {response.status_code}")
        
        # 打印完整响应用于调试
        try:
            result = response.json()
            print(f"响应 JSON keys: {list(result.keys())}")
            if "choices" in result:
                choice = result["choices"][0]
                print(f"choice keys: {list(choice.keys())}")
                if "message" in choice:
                    print(f"message keys: {list(choice['message'].keys())}")
        except:
            print(f"响应原文(前500字符): {response.text[:500]}")
        
        response.raise_for_status()
        result = response.json()
        choices = result.get("choices", [])
        if not choices:
            print("警告: API 返回空的 choices")
            return None
        
        # 处理 thinking 模式：先尝试 reasoning_content，再尝试 content
        message = choices[0].get("message", {})
        
        # 优先取 reasoning_content（thinking 模式下的实际内容）
        response_text = message.get("reasoning_content", "")
        if not response_text:
            response_text = message.get("content", "")
        
        # 如果 content 是数组（某些 API 格式），取文本内容
        if isinstance(response_text, list):
            text_parts = []
            for item in response_text:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            response_text = "".join(text_parts)
        
        print(f"生成内容长度: {len(response_text)} 字符")
        return response_text if response_text and response_text.strip() else None
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: 无法连接到 Agnes API: {e}")
    except requests.exceptions.Timeout as e:
        print(f"超时错误: Agnes API 调用超时({AGNES_TIMEOUT}s): {e}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP 错误: {e}")
    except Exception as e:
        print(f"调用 Agnes API 失败: {e}")
        import traceback
        traceback.print_exc()
    return None


def call_llm_api(prompt, system_prompt=None):
    print(f"当前 LLM 提供方: {LLM_PROVIDER}")
    if LLM_PROVIDER == "agnes":
        return call_agnes_api(prompt, system_prompt=system_prompt)
    return call_ollama_api(prompt)


def build_prompt(segment_info_str, content, title_prefix_hint, min_benefit_hits):
    """按照 config.prompt 的模板拼接 Prompt。"""
    prompt_cfg = cfg_get("prompt", default={})
    task_template = prompt_cfg.get("task_template", "")
    role = prompt_cfg.get("role", "")
    style_rules_list = prompt_cfg.get("style_rules", [])
    company_background = prompt_cfg.get("company_background", "")
    required_sections_list = prompt_cfg.get("required_sections_after_body", [])

    # 加载 standard-template.txt 的实际内容
    standard_template_content = load_standard_template()
    if not standard_template_content:
        standard_template_content = "(标准模板文件加载失败，请检查 standard-template.txt)"

    # 将 title_prefix 作为一条运行时规则附加到 style_rules
    style_rules_with_dynamic = style_rules_list + [
        "",
        f"【动态要求】文章标题必须以 '{title_prefix_hint}' 开头；内容中必须包含至少 {min_benefit_hits} 条具体、可量化的客户可感知实际利益。"
    ]
    style_rules_block = "\n".join(f"- {r}" if r else "" for r in style_rules_with_dynamic)

    # 生成 required_sections_block
    required_sections_block = "\n".join(f"- {r}" for r in required_sections_list)

    return task_template.format(
        role=role,
        standard_template=standard_template_content,
        segment_info=segment_info_str,
        source=content,
        style_rules_block=style_rules_block,
        company_background=company_background,
        required_sections_block=required_sections_block,
    )


def process_articles():
    os.makedirs(OLD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    customer_segments = load_customer_segments()

    files_to_process = []
    for root, dirs, files in os.walk(NEW_DIR):
        for file in files:
            if file.endswith('.md') or file.endswith('.json'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, NEW_DIR)
                files_to_process.append((file_path, relative_path))

    if not files_to_process:
        print("new 目录中没有待处理文件")
        return

    print(f"发现 {len(files_to_process)} 个文件待处理")

    for file_path, relative_path in files_to_process:
        print(f"\n处理文件: {relative_path}")
        content, title = "", "未知标题"

        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            content = data.get('text', '')
            title = data.get('title', '未知标题')
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            for line in content.split('\n'):
                if line.startswith('# '):
                    title = line[2:].strip()
                    break

        matched_segment_id, matched_seg = identify_customer_segment(content, customer_segments)
        segment_info_str = ""
        title_prefix_hint = "【老板必看】"
        if matched_seg:
            title_prefix_hint = matched_seg.get("title_prefix", title_prefix_hint)
            segment_info_str = (
                f"身份标签: {matched_seg.get('label', '通用')}\n"
                f"核心痛点: {matched_seg.get('core_pain', '')}\n"
                f"客户收益: {matched_seg.get('customer_benefit', '')}\n"
                f"互动钩子: {matched_seg.get('interact_hook', '')}\n"
                f"转发理由: {matched_seg.get('forward_reason', '')}\n"
                f"留言引导: {matched_seg.get('comment_question', '')}\n"
                f"强制标题前缀: {title_prefix_hint}"
            )
            print(f"识别到客户群体: {matched_seg.get('label')}")
        else:
            print("客户群体识别失败，使用通用策略")
            segment_info_str = "通用中小企业老板视角：侧重合规、省钱、拿政策福利"

        prompt = build_prompt(segment_info_str, content, title_prefix_hint, MIN_BENEFIT_HITS)

        rewritten_content = None
        for attempt in range(MAX_RETRY + 1):
            print(f"调用 LLM 改写文章（第 {attempt + 1}/{MAX_RETRY + 1} 次）...")
            rewritten_content = call_llm_api(prompt)
            if rewritten_content is None or not rewritten_content.strip():
                print("LLM API 调用失败或返回空，跳过此文件")
                break

            hits = count_benefit_hits(rewritten_content)
            print(f"实际利益关键词命中: {hits}/{MIN_BENEFIT_HITS}")
            if hits >= MIN_BENEFIT_HITS:
                print("校验通过")
                break

            print("校验未通过，追加更严格要求到 Prompt")
            reinforce = (
                "\n\n【重要补充】上一版缺少明确的'客户可感知实际利益'，请严格重写："
                f"必须在正文中明确写出至少 {MIN_BENEFIT_HITS} 条具体、可量化的实际利益"
                f"（如'少花 5000 元官费''拿 10 万政府补贴''避免 50 万侵权赔偿''减免 15% 所得税'）"
                "，每条给出数字或场景。"
            )
            prompt = build_prompt(segment_info_str, content, title_prefix_hint, MIN_BENEFIT_HITS) + reinforce

        if rewritten_content is None or not rewritten_content.strip():
            continue

        if title_prefix_hint:
            rewritten_content = apply_title_prefix(rewritten_content, title_prefix_hint)

        frontmatter = build_frontmatter(matched_segment_id, matched_seg, title)
        if frontmatter:
            rewritten_content = frontmatter + rewritten_content

        output_rel = relative_path[:-5] + '.md' if relative_path.endswith('.json') else relative_path
        output_path = os.path.join(OUTPUT_DIR, output_rel)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rewritten_content)
        print(f"已输出到: {output_path}")

        old_path = os.path.join(OLD_DIR, relative_path)
        os.makedirs(os.path.dirname(old_path), exist_ok=True)
        if os.path.exists(old_path):
            os.remove(old_path)
            print(f"删除 old 目录中的旧文件: {relative_path}")
        try:
            shutil.move(file_path, old_path)
        except OSError:
            shutil.copy2(file_path, old_path)
            os.remove(file_path)
        print(f"已从 new 移动到 old: {relative_path}")

    print("\n所有文件处理完成！")


if __name__ == "__main__":
    process_articles()
