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
| `templates` | object | 多模板匹配机制：模板列表、匹配关键词、默认模板 |
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
| `default_title_prefix` | string | `【老板必看】` | 客户群体未匹配到专属前缀时使用的默认标题前缀 |
| `originality_signal_words` | list[str] | 见 `config.json` | 独家内容信号词集合（如"我们经手""广东企业""踩坑""复盘""反常识"等）。用于后置原创度校验，输出中命中越多表示独家实操内容越充分 |
| `min_originality_hits` | int | `5` | 输出中必须命中的 `originality_signal_words` 最低数量。低于此值判定为原创度不足并触发重试 |
| `banned_section_patterns` | list[str] | 见 `config.json` | 禁止的章节编号模式（如"一、""二、""1.1""2.1"等）。后置校验命中数必须为0，否则触发重试。用于避免AI同质化文章结构 |
| `banned_marketing_phrases` | list[str] | 见 `config.json` | 禁止的营销话术（如"全流程代办""一站式搞定""免费评估""留言送方案"等）。后置校验命中数必须为0，否则触发重试 |
| `required_local_scene_words` | list[str] | 见 `config.json` | 本地场景词集合（如"广东""深圳""东莞""我们经手""一线""实操"等）。用于校验输出是否包含足够的广东本地企业实操内容 |
| `min_local_scene_hits` | int | `2` | 输出中必须命中的 `required_local_scene_words` 最低数量。低于此值判定为本地实操内容不足并触发重试 |

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

## 6. templates（多模板匹配配置）

> 多模板匹配机制：`process_articles.py` 根据文章内容关键词打分，从 `templates.list` 中选出最合适的改写模板，再按该模板的 role / company_background / style_rules / task_template 组装 Prompt。目的是让不同内容类型（政策公示 / 干货科普 / 案例复盘）使用差异化写作风格，通过公众号原创检测。

### 6.1 顶层

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `_comment` | string | 固定 | 机制说明，仅自注释，不被程序读取 |
| `default_template` | string | `knowledge_share` | 所有模板关键词均未命中时的兜底模板 `id` |
| `force_policy_keywords` | list[str] | 见 `config.json` | 通知类强信号词（第一组，如"通知""公告""公示""征集""展会"等）。与 `force_policy_context_keywords` 同时命中时，强制匹配 `policy_announcement` 模板，避免展会/通知类文章被干货科普模板抢走 |
| `force_policy_context_keywords` | list[str] | 见 `config.json` | 通知类强信号词（第二组，上下文词，如"截止""报名""时间""地点""主办"等）。与 `force_policy_keywords` 同时命中时触发强制匹配 |
| `list` | list[object] | 4 个模板 | 模板列表，按顺序遍历打分。当前：policy_announcement（政策公示）、knowledge_share（干货科普）、case_review（案例复盘）、hot_topic（热点事件） |

### 6.2 templates.list[]（单个模板）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `id` | string | 必填 | 模板唯一标识（小写下划线，如 `policy_announcement`），写入输出 frontmatter 的 `template` 字段 |
| `name` | string | 必填 | 模板中文名（如 `政策公示类`），写入 frontmatter 的 `template_name` 字段 |
| `description` | string | 必填 | 适配场景说明，供维护者理解用途 |
| `match_priority` | int | 必填 | 同分决胜优先级，**越小越优先**。当前：政策公示=1、干货科普=2、案例复盘=3、热点事件=4 |
| `priority_keywords` | list[str] | 必填 | 强信号关键词，命中 1 条计 **2 分**。用于区分度高的词（如"名单""公示""软著""案例"） |
| `match_keywords` | list[str] | 必填 | 普通关键词，命中 1 条计 **1 分**。用于通用相关词（如"申报""认定""企业"） |
| `role` | string | 必填 | LLM 角色定义，作为 Prompt 首段；Agnes 模式下同时作为 System Prompt |
| `company_background` | string | 必填 | Prompt 中"公司背景"段落 |
| `style_rules` | list[str] | 必填 | 写作规范规则集，按顺序用 `\n- ` 连接进入 Prompt |
| `required_sections_after_body` | list[str] | 必填 | 文末固定模块说明，进入 Prompt |
| `task_template` | string | 必填 | 主 Prompt 模板。占位符：`{role}`、`{source}`、`{company_background}`、`{style_rules_block}`、`{required_sections_block}` |

> **匹配规则**：总得分 = 2×priority 命中数 + 1×match 命中数；得分最高者胜出；同分按 `match_priority` 决胜；全部为 0 分时回退 `default_template`。
> **新增模板**：在 `list` 中追加对象，`id` 唯一、`match_priority` 不重复，并在 `CHANGELOG.md` 登记。
> **回退兼容**：若 `templates.list` 为空或缺失，代码自动回退旧 `config.prompt` 单模板逻辑（含 `{standard_template}`、`{segment_info}` 占位符）。

---

## 7. security（安全边界配置）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `config_file` | string | `customer_segments.json` | 客户群体识别规则文件名，与 `process_articles.py` 中 `CUSTOMER_SEGMENTS_FILE` 对应 |
| `template_file` | string | `standard-template.md` | 改写结构模板文件名，与 `process_articles.py` 中 `STANDARD_FILE` 对应 |
| `allowed_file_exts` | list[str] | `[".md", ".json"]` | 应用允许处理的源文件后缀，跨模块边界校验用 |
| `tag_preview_limit` | int | 10 | YAML frontmatter 中标签预览数量上限 |

---

## 8. 修改约定

1. **新增字段**：追加到所属分类末尾，在本说明中新增一行，并标注类型/默认值/说明；完成后在 `CHANGELOG.md` 中登记。
2. **修改字段语义**（如 `provider_env` 改名为 `provider_env_name`）：视为**不兼容变更**，必须在 `CHANGELOG.md` 的「不兼容变更」章节标注，并同步在代码中替换所有引用。
3. **删除字段**：先在代码中移除所有引用，再从 `config.json` 删除，最后从本说明删除对应段落。
4. **敏感值**：`api_key`、`token` 等一律通过环境变量注入；`config.json` 只能存放 `xxx_env`（环境变量名），不得直接写 `xxx_value`。

---

## 9. 代码侧加载方式（参考）

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

## 10. 变更历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.4.0 | 2026-09-09 | 热点事件类模板+后置校验强化：新增 `hot_topic` 热点事件类模板（适配科研发现/热点新闻/行业动态+知识产权类比，热点信息≤20%，强制2个本地踩坑+1个反常识+1个趋势观察）；统一强化4个模板共性约束（禁止章节编号、禁止全流程代办/一站式搞定等营销话术、强制2个广东本地案例、关键数据准确性约束）；新增3项后置校验——章节编号检测（`banned_section_patterns`，命中=0才通过）、营销话术检测（`banned_marketing_phrases`，命中=0才通过）、本地场景词检测（`required_local_scene_words` + `min_local_scene_hits=2`）；校验不通过自动重试并在Prompt中追加对应强化要求 |
| 1.3.0 | 2026-09-03 | 原创度强化：policy_announcement 扩充关键词（展会/参展/征集等）+ 强化 style_rules（公共信息≤25%、幻觉防护、强制2个本地踩坑场景+1个独家趋势+1个反常识）；knowledge_share 收窄 priority_keywords（"专利"降级为 match）；全局删除"保持原文核心信息不变"冲突条款；新增 `content.originality_signal_words` + `min_originality_hits` 后置原创度校验；`match_template` 新增通知类强信号强制匹配（`force_policy_keywords` + `force_policy_context_keywords`）；全模板 style_rules + customer_segments 弱化营销引流话术（去掉"免费评估/免费帮你"等，改为纯粹知识交流） |
| 1.2.0 | 2026-08-21 | 新增 `templates` 多模板匹配段（政策公示/干货科普/案例复盘）+ `content.default_title_prefix` |
| 1.1.0 | 2026-07-29 | 初版：由业务代码中散落的常量抽离而来 |
