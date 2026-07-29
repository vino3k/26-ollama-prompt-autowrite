# config.json 配置说明

> 本文档与 `config.json` 一一对应。**新增/修改/删除 `config.json` 的任何字段，必须同步更新本文档**，禁止脱节。

---

## 1. 顶层结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `_comment` | string | 配置文件总说明，仅为文件自注释，不被程序读取 |
| `version` | string | 当前配置版本号，与 `VERSION.txt` 保持一致 |
| `monitor` | object | 监控循环、运行锁、进程超时等参数 |
| `llm` | object | LLM 提供方（Ollama / Agnes）的路由、地址、模型名、超时等 |
| `content` | object | 内容改写规则：利益关键词、强制段落、标题前缀 |
| `prompt` | object | System Prompt、Prompt 模板、公司背景、风格规则 |
| `security` | object | 安全相关：配置文件名、允许扩展名等 |

---

## 2. monitor（监控循环配置）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `scan_interval_seconds` | int | 3600 | `main.py` 扫描 `new/` 目录的间隔（秒）。典型值：60（调试）/3600（生产） |
| `lock_max_age_seconds` | int | 3600 | 运行锁文件 `.monitor.lock` 最长存活时间，超过则视为脏锁允许重入。**必须大于 process_timeout_seconds** |
| `process_timeout_seconds` | int | 3600 | 单次 `process_articles.py` 调用的最大等待时间。超过则强制终止 |
| `recover_wait_seconds` | int | 60 | 监控主循环异常捕获后的休眠时间（秒）。为避免 100% CPU 空转，异常循环必须 sleep |
| `process_file_exts` | list[str] | `[".md", ".json"]` | `new/` 目录中需要处理的文件后缀。大小写不敏感匹配 |
| `required_dirs` | list[str] | `["new","old","output","logs"]` | 应用启动时必须存在的目录名（相对 `/app`），缺失则自动创建 |

---

## 3. llm（LLM 提供方配置）

### 3.1 顶层

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `provider_env` | string | `LLM_PROVIDER` | 指定 LLM 提供方来源的**环境变量名**。代码通过 `os.environ[provider_env]` 读取，值为 `ollama` 或 `agnes` |

### 3.2 llm.ollama（本地 Ollama）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `host_env` | string | `OLLAMA_HOST` | Ollama 主机地址**环境变量名** |
| `port_env` | string | `OLLAMA_PORT` | Ollama 端口**环境变量名** |
| `host_default` | string | `192.168.2.111` | 当 `OLLAMA_HOST` 未设置时的回退值 |
| `port_default` | int | `11434` | 当 `OLLAMA_PORT` 未设置时的回退值 |
| `model_env` | string | `OLLAMA_MODEL` | 模型名**环境变量名** |
| `model_default` | string | `qwen3.5:latest` | 当 `OLLAMA_MODEL` 未设置时的回退值 |
| `api_url_env` | string | `OLLAMA_API_URL` | 完整 API URL **环境变量名**。设置后将**覆盖** host+port 拼接逻辑 |
| `request_timeout_seconds` | int | 300 | 单次 LLM 请求超时（秒） |
| `health_check_timeout_seconds` | int | 10 | `main.py` 中健康检查（GET `/api/tags`）的超时（秒） |

### 3.3 llm.agnes（云端 Agnes-2.0-Flash）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key_env` | string | `AGNES_API_KEY` | Agnes API Key **环境变量名**。真实 Key 必须仅出现在 `.env` 或系统环境变量中 |
| `api_url` | string | `https://apihub.agnes-ai.cn/v1/chat/completions` | Agnes Chat Completions 接口地址 |
| `model` | string | `agnes-2.0-flash` | Agnes 模型 ID |
| `max_tokens` | int | 4096 | `max_tokens` 参数上限 |
| `temperature` | float | 0.7 | 采样温度（0~1） |
| `thinking` | bool | `false` | 是否启用 Think 模式（经测试 Agnes-2.0-Flash 不支持有效 thinking，建议保持 false） |
| `request_timeout_seconds` | int | 300 | 单次 LLM 请求超时（秒） |

### 3.4 llm.retry（重试与内容校验）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_attempts` | int | 2 | **校验未通过**时的最大重试次数。总尝试次数 = `max_attempts + 1`（首次 + 重试） |
| `min_benefit_hits` | int | 3 | 内容中必须命中的 `content.benefit_keywords` 数量。低于此值判定为不合格并触发重试 |
| `default_system_prompt` | string | `你是一位资深知识产权内容策略师...` | Agnes 调用时的 System Prompt；Ollama 因无 Chat 接口不使用此字段 |

---

## 4. content（内容规则）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `benefit_keywords` | list[str] | 见 `config.json` | 内容中"客户可感知实际利益"的关键词集合。每条至少出现一次即计入 |
| `required_title_prefix` | list[str] | 固定条目 | 对标题前缀的**描述性约束**，将作为 Prompt 要求的一部分 |
| `required_sections_after_body` | list[str] | 固定条目 | 正文之后必须包含的模块说明，作为 Prompt 约束 |

> **注意**：`benefit_keywords` 为**公共非敏感配置**，可以提交代码库；若后续新增关键词请在 `config.json` 中追加并在本说明中列出新增语义。

---

## 5. prompt（Prompt 组装配置）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `role` | string | `你是一位资深知识产权内容策略师...` | LLM 的角色定义，作为 Prompt 的首段，同时也是 Agnes 的 System Prompt |
| `company_background` | string | `知识产权综合代理机构...` | Prompt 中"公司背景"段落 |
| `standard_template_ref` | string | `standard-template.md` | 引用的标准模板文件名；代码会**读取该文件的实际内容**嵌入 Prompt |
| `style_rules` | list[str] | 见 config.json | Prompt 的完整规则集（含结构要求/内容要求/严禁输出标记/禁止事项），条目按顺序用 `\n- ` 连接进入 Prompt |
| `required_sections_after_body` | list[str] | 固定 2 条 | 对"文末固定模块"的说明（用自然方式表达，不要【】标记），会嵌入 Prompt |
| `task_template` | string | 带占位符模板 | 主 Prompt 模板。占位符：`{role}`、`{standard_template}`（文件内容）、`{segment_info}`、`{source}`、`{company_background}`、`{style_rules_block}`、`{required_sections_block}` |

> **修改此段前请充分评估**：改动会直接影响 LLM 输出质量。建议做 A/B 测试再上线。
> `style_rules` 包含 LLM 输出质量的核心约束（如"必须包含 3 条可感知利益"、"禁止 AI 自述"等），修改后务必在 Docker 容器中做一次端到端验证。

---

## 6. security（安全边界配置）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `config_file` | string | `customer_segments.json` | 客户群体识别规则文件名，与 `process_articles.py` 中 `CUSTOMER_SEGMENTS_FILE` 对应 |
| `template_file` | string | `standard-template.md` | 改写结构模板文件名，与 `process_articles.py` 中 `STANDARD_FILE` 对应 |
| `allowed_file_exts` | list[str] | `[".md", ".json"]` | 应用允许处理的源文件后缀，跨模块边界校验用 |
| `tag_preview_limit` | int | 10 | YAML frontmatter 中标签预览数量上限 |

---

## 7. 修改约定

1. **新增字段**：追加到所属分类末尾，在本说明中新增一行，并标注类型/默认值/说明；完成后在 `CHANGELOG.md` 中登记。
2. **修改字段语义**（如 `provider_env` 改名为 `provider_env_name`）：视为**不兼容变更**，必须在 `CHANGELOG.md` 的「不兼容变更」章节标注，并同步在代码中替换所有引用。
3. **删除字段**：先在代码中移除所有引用，再从 `config.json` 删除，最后从本说明删除对应段落。
4. **敏感值**：`api_key`、`token` 等一律通过环境变量注入；`config.json` 只能存放 `xxx_env`（环境变量名），不得直接写 `xxx_value`。

---

## 8. 代码侧加载方式（参考）

```python
import json, os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config(path: str = _CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get(cfg: dict, *keys, default=None):
    cur = cfg
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
```

---

## 9. 变更历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.1.0 | 2026-07-29 | 初版：由业务代码中散落的常量抽离而来 |
