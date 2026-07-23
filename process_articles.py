#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章处理脚本：使用 Ollama 大模型按照标准模块构成改写文章并移动文件
"""

import os
import shutil
import json
import requests


def _load_dotenv(env_path):
    """
    简易 .env 加载器（不依赖 python-dotenv）
    逐行解析 KEY=VALUE，跳过空行和以 # 开头的注释
    仅当环境变量未设置时才注入（系统环境变量优先级更高）
    """
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                # 去掉首尾成对的单引号或双引号
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                # 仅当系统环境变量未设置时，才使用 .env 中的值
                os.environ.setdefault(key, value)
    except Exception as e:
        print("警告: 读取 .env 文件失败: {0}".format(e))


# 加载项目根目录下的 .env 文件（如果存在）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_load_dotenv(os.path.join(BASE_DIR, ".env"))

# 目录路径
NEW_DIR = os.path.join(BASE_DIR, "new")
OLD_DIR = os.path.join(BASE_DIR, "old")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
STANDARD_FILE = os.path.join(BASE_DIR, "standard-template.txt")
CUSTOMER_SEGMENTS_FILE = os.path.join(BASE_DIR, "customer_segments.json")

# LLM 提供方配置：ollama（默认，本地）/ agnes（云端 API）
# 可通过环境变量 LLM_PROVIDER 覆盖，例如 set LLM_PROVIDER=agnes
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").lower()

# Ollama 配置（支持环境变量，便于 Docker / 不同环境部署）
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "192.168.2.111")
OLLAMA_PORT = os.environ.get("OLLAMA_PORT", "11434")
OLLAMA_API_URL = os.environ.get(
    "OLLAMA_API_URL",
    f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"
)
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:latest")

# Agnes-2.0-Flash 配置（OpenAI 兼容 Chat Completions API）
AGNES_API_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
AGNES_MODEL = "agnes-2.0-flash"
AGNES_API_KEY = os.environ.get("AGNES_API_KEY", "")

def load_standard_template():
    """
    加载标准模块构成模板
    """
    if os.path.exists(STANDARD_FILE):
        with open(STANDARD_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    print("警告: 标准模板文件不存在: {}".format(STANDARD_FILE))
    return ""

def load_customer_segments():
    """
    加载客户群体配置
    """
    if os.path.exists(CUSTOMER_SEGMENTS_FILE):
        with open(CUSTOMER_SEGMENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    print("警告: 客户群体配置文件不存在: {}".format(CUSTOMER_SEGMENTS_FILE))
    return {}

def identify_customer_segment(content, customer_segments):
    """
    通过本地关键词匹配识别原文所属客户群体
    返回 (segment_id, segment_info) 或 (None, None)
    匹配规则：统计每个群体的关键词命中数，取最高分（无命中时降级为 general）
    """
    if not customer_segments:
        return None, None

    # 排除通用兜底分组
    candidate_ids = [seg_id for seg_id in customer_segments.keys() if seg_id != "general"]

    # 统计各群体关键词命中数
    scores = {}
    for seg_id in candidate_ids:
        keywords = customer_segments[seg_id].get("keywords", [])
        if not keywords:
            continue
        hit_count = 0
        for kw in keywords:
            if kw and kw in content:
                hit_count += 1
        scores[seg_id] = hit_count

    # 选出命中数最高的群体
    best_id = None
    best_score = 0
    for seg_id, score in scores.items():
        if score > best_score:
            best_score = score
            best_id = seg_id

    # 没有任何命中，降级为通用企业老板视角
    if best_id is None:
        if "general" in customer_segments:
            return "general", customer_segments["general"]
        return None, None

    return best_id, customer_segments[best_id]

# 客户可感知实际利益关键词（用于校验）
BENEFIT_KEYWORDS = [
    "省钱", "省下", "节省", "少花", "多拿", "拿到补贴", "领补贴", "拿补贴", "扶持资金", "政府补贴",
    "减免", "减税", "退税", "加计扣除", "返还",
    "防罚款", "避免罚款", "避免赔偿", "避免损失", "规避风险", "避免下架", "避免封号",
    "拓市场", "开拓市场", "出海", "上亚马逊", "入驻平台", "上新品", "扩品类",
    "拿证", "下证", "授权", "备案", "认定通过", "申报成功", "维权成功", "拿到订单",
    "拿政策", "享受政策", "政策红利", "享受福利", "高企", "高新企业", "专精特新",
    "省钱", "成本", "官费", "补助", "奖励"
]

# 内容质量校验：至少 N 条可感知实际利益（默认 3 条）
MIN_BENEFIT_HITS = 3
# 校验失败时的最大重试次数
MAX_RETRY = 2


def count_benefit_hits(content):
    """
    统计文中命中的"客户可感知实际利益"关键词次数
    """
    if not content:
        return 0
    count = 0
    for kw in BENEFIT_KEYWORDS:
        if kw and kw in content:
            count += 1
    return count


def apply_title_prefix(content, prefix):
    """
    在文章第一个标题前追加行业专属小标题前缀
    如果首行不是 # 开头，则把前缀插入到第一行前面
    """
    if not prefix:
        return content
    lines = content.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('# '):
            # 替换原标题为 "【前缀】原标题"
            new_title = stripped.replace('# ', '# ', 1)
            # 避免重复添加
            if prefix not in new_title:
                new_title = f"# {prefix}{new_title[2:]}"
            lines[i] = new_title
            break
    else:
        # 没有找到 # 标题，直接在最前面插入
        lines.insert(0, f"# {prefix}{content[:30]}")
    return '\n'.join(lines)


def build_frontmatter(segment_id, seg, title):
    """
    生成 YAML frontmatter，包含客户群体标签
    """
    if not seg:
        return ""
    tags = seg.get("tags", [])
    label = seg.get("label", "通用")
    # YAML 格式
    lines = ["---"]
    lines.append('title: "{0}"'.format(title.replace('"', '\\"')))
    lines.append('customer_segment: "{0}"'.format(segment_id or "general"))
    lines.append('customer_label: "{0}"'.format(label))
    if tags:
        lines.append('tags:')
        for t in tags:
            lines.append('  - {0}'.format(t))
    lines.append('---')
    lines.append('')  # frontmatter 后留一个空行
    return '\n'.join(lines)

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


def call_agnes_api(prompt, system_prompt="你是一位资深知识产权内容策略师，擅长将专业内容改写成符合移动端阅读习惯、具有传播力的爆款文章。"):
    """
    调用 Agnes-2.0-Flash API（OpenAI 兼容 Chat Completions 接口）
    启用 Thinking 模式（chat_template_kwargs.enable_thinking=true）
    从环境变量 AGNES_API_KEY 读取 API Key
    """
    if not AGNES_API_KEY:
        print("错误: 未设置环境变量 AGNES_API_KEY，无法调用 Agnes API")
        return None

    headers = {
        "Authorization": "Bearer {0}".format(AGNES_API_KEY),
        "Content-Type": "application/json"
    }

    data = {
        "model": AGNES_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
        "stream": False,
        # 启用 Thinking 模式（提升推理与改写质量）
        "chat_template_kwargs": {
            "enable_thinking": True
        }
    }

    try:
        print("正在调用 Agnes-2.0-Flash API，URL: {0}".format(AGNES_API_URL))
        print("模型: {0}".format(AGNES_MODEL))
        print("Thinking 模式: 启用")
        print("Prompt 长度: {0} 字符".format(len(prompt)))

        response = requests.post(AGNES_API_URL, headers=headers, json=data, timeout=300)
        print("API 响应状态码: {0}".format(response.status_code))

        response.raise_for_status()

        result = response.json()
        choices = result.get("choices", [])
        if not choices:
            print("警告: API 返回了空的 choices")
            return None

        response_text = choices[0].get("message", {}).get("content", "")
        print("生成内容长度: {0} 字符".format(len(response_text)))

        if not response_text or len(response_text.strip()) == 0:
            print("警告: API 返回了空内容")
            return None

        return response_text
    except requests.exceptions.ConnectionError as e:
        print("连接错误: 无法连接到 Agnes API: {0}".format(e))
        return None
    except requests.exceptions.Timeout as e:
        print("超时错误: Agnes API 调用超时: {0}".format(e))
        return None
    except requests.exceptions.HTTPError as e:
        print("HTTP 错误: {0}".format(e))
        print("响应内容: {0}".format(response.text if 'response' in locals() else '无'))
        return None
    except Exception as e:
        print("调用 Agnes API 失败: {0}".format(e))
        import traceback
        traceback.print_exc()
        return None


def call_llm_api(prompt):
    """
    统一的 LLM 调用入口，根据 LLM_PROVIDER 选择后端
    - ollama: 调用本地 Ollama
    - agnes:  调用云端 Agnes-2.0-Flash
    """
    print("当前 LLM 提供方: {0}".format(LLM_PROVIDER))
    if LLM_PROVIDER == "agnes":
        return call_agnes_api(prompt)
    # 默认 ollama
    return call_ollama_api(prompt)

def process_articles():
    """
    处理所有文章
    """
    # 确保目录存在
    os.makedirs(OLD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 加载标准模块构成
    standard_template = load_standard_template()

    # 加载客户群体配置
    customer_segments = load_customer_segments()
    
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
        
        # 识别客户群体（本地关键词匹配，无需联网）
        forward_reason = ""
        comment_question = ""
        title_prefix = ""
        segment_tags = []
        matched_segment_id = None
        matched_seg = None
        if customer_segments:
            print("正在识别客户群体（关键词匹配）...")
            matched_segment_id, matched_seg = identify_customer_segment(content, customer_segments)
            if matched_seg:
                forward_reason = matched_seg.get("forward_reason", "")
                comment_question = matched_seg.get("comment_question", "")
                title_prefix = matched_seg.get("title_prefix", "")
                segment_tags = matched_seg.get("tags", [])
                segment_info_str = (
                    f"客户群体：{matched_seg['label']}\n"
                    f"核心痛点：{matched_seg['core_pain']}\n"
                    f"客户收益：{matched_seg['customer_benefit']}\n"
                    f"互动钩子：{matched_seg['interact_hook']}\n"
                    f"可转发理由：{forward_reason}\n"
                    f"差异化留言引导：{comment_question}"
                )
                print(f"识别到客户群体: {matched_seg['label']} | 前缀: {title_prefix}")
            else:
                print("客户群体识别失败，将使用通用策略")

        if not segment_info_str:
            segment_info_str = "通用中小企业老板视角：侧重合规、省钱、拿政策福利"

        # 行业专属标题前缀提示（注入到 prompt 中，让模型直接产出带前缀的标题）
        title_prefix_hint = title_prefix if title_prefix else "【老板必看】"

        # 构建 prompt
        prompt = f"""
你是一位资深知识产权内容策略师，擅长将专业内容改写成符合移动端阅读习惯、具有传播力的爆款文章。你是一位资深知识产权内容策略师，擅长将专业内容改写成符合移动端阅读习惯、具有传播力的爆款文章。

## 任务
将以下文章按照标准模块结构改写，融入知识产权代理业务场景，输出完整Markdown格式。

## 标准模块结构
""{standard_template}""

## 目标客户群体（必须严格围绕此群体的痛点、收益和互动钩子来组织内容）
{segment_info_str}

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
5. **客户导向**：紧扣"目标客户群体"部分的痛点、收益、互动钩子进行改写

### 内容要求
1. 保持原文核心信息不变，不增删关键事实
2. 将知识产权业务（商标/专利/版权/认证/科创/海外）自然融入内容场景
3. 引用外部信息时必须标注来源
4. 语言风格：专业且有温度，避免生硬说教
5. **文章首行标题必须以行业专属小标题前缀开头**：`{title_prefix_hint}`，让读者一眼识别本文与自己是否相关
6. **文中必须明确给出至少 3 条"客户可感知实际利益"**，覆盖以下类型中的任意组合：
   - 省钱型（少花官费、节省开支、降低侵权赔偿）
   - 拿补贴型（政府补贴、扶持资金、税收减免、加计扣除、高新企业减免所得税）
   - 防罚款/防风险型（避免下架、避免封号、避免赔偿、避免驳回）
   - 拓市场型（出海、入驻平台、扩品类、拿下订单）
   - 拿证/维权型（下证、备案、认定通过、维权成功）
   每条利益必须**具体、可量化、有场景**，例如"拿补贴10万元"比"获得支持"更有感
7. **文末必须包含 2 个固定模块**：
   - **【可转发理由】**：用一段话告诉读者"为什么应该把这篇文章转发给谁"，让读者有明确转发对象和转发动机，例如提醒合伙人/运营负责人提前规避踩坑、省下数万元赔偿
   - **【留言互动】**：用 1 个具体问题向读者提问，**问题必须紧扣上文"目标客户群体"中的痛点，不要使用"你认同第几点"这种通用提问**
     - 电商客户：聚焦店铺侵权、商标被抢、图片盗用
     - 工厂客户：聚焦专利申报、高新认定、研发投入
     - 跨境客户：聚焦海外商标、海关扣货、平台侵权
     - 科技客户：聚焦软著登记、发明专利、科创项目
     - 通用客户：聚焦优先解决哪类知识产权问题

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
        
        # 调用 Ollama API 生成改写内容（带"实际利益 ≥ 3"校验与重试）
        rewritten_content = None
        for attempt in range(MAX_RETRY + 1):
            print("正在调用 LLM API 改写文章（第 {0}/{1} 次）...".format(attempt + 1, MAX_RETRY + 1))
            rewritten_content = call_llm_api(prompt)
            if rewritten_content is None:
                print("警告: LLM API 调用失败，跳过文章 {0}".format(relative_path))
                print("请检查 LLM 服务状态或网络连接")
                break
            if not rewritten_content or len(rewritten_content.strip()) == 0:
                print("警告: API 返回了空内容，跳过文章 {0}".format(relative_path))
                break

            # 校验：至少 MIN_BENEFIT_HITS 条可感知实际利益
            benefit_hits = count_benefit_hits(rewritten_content)
            print("  - 实际利益关键词命中数: {0}/{1}".format(benefit_hits, MIN_BENEFIT_HITS))
            if benefit_hits >= MIN_BENEFIT_HITS:
                print("  - 校验通过")
                break
            else:
                print("  - 校验未通过，利益点不足")
                if attempt < MAX_RETRY:
                    print("  - 准备重试，追加更严格的利益点要求到 prompt")
                    # 在 prompt 末尾追加更严格的利益点要求，重新调用
                    reinforce = '\n\n【重要补充】上一版你输出的内容缺少明确的"客户可感知实际利益"，请严格按以下要求重写：必须在正文中明确写出至少 3 条具体、可量化的实际利益（如"少花 5000 元官费""拿 10 万政府补贴""避免 50 万侵权赔偿""减免 15% 所得税"等），每条都给出数字或场景，越具体越好。\n'
                    prompt = prompt + reinforce
                else:
                    print("  - 已达最大重试次数，使用当前结果输出")

        if rewritten_content is None:
            continue  # 跳过当前文件，继续处理下一个文件
        if not rewritten_content or len(rewritten_content.strip()) == 0:
            continue

        # 1) 给标题追加行业专属小标题前缀（前端兜底，避免模型漏写）
        if title_prefix:
            rewritten_content = apply_title_prefix(rewritten_content, title_prefix)

        # 2) 在文首插入 YAML frontmatter（包含客户群体标签）
        frontmatter = build_frontmatter(matched_segment_id, matched_seg, title)
        if frontmatter:
            rewritten_content = frontmatter + rewritten_content

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
        print("文件已输出到: {0}".format(output_file_path))
        
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
