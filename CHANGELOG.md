# 更新日志

> 本项目遵循 [AGENTS.md](./AGENTS.md) 规范，按语义化版本号（X.Y.Z）管理。
> - X：不兼容的架构变更
> - Y：新增功能、模块
> - Z：bug 修复、小优化
> - 所有可配置常量统一在 [config.json](./config.json) 管理，配套文档 [config.readme.md](./config.readme.md)。

---

## [1.4.1] - 2026-09-09

### Bug 修复 - 模板匹配误匹配

- **问题**：通知类强信号匹配（`force_policy_keywords` + `force_policy_context_keywords`）过于激进，只要全文中同时命中就强制匹配政策公示类，导致干货科普类和案例复盘类文章被误匹配
- **修复**：
  - 只在文章**前500字**检测通知类强信号（政策通知类文章通常在开头就有"通知""公告"等词，科普/案例文章可能在中间提到）
  - 增加排除逻辑：如果案例复盘类（`case_review`）的 `priority_keywords` 命中≥2，则不强制匹配政策公示类

### 功能优化 - 429退避重试机制

- **问题**：Agnes API 返回429（限流）时直接失败，导致批量处理时大量文章被跳过
- **修复**：`call_agnes_api` 新增429退避重试机制
  - 遇到429时自动等待后重试，初始等待10秒，每次翻倍，最大60秒
  - 最多重试3次（可通过 `llm.retry.retry_429_max_attempts` 配置）
  - 超过最大重试次数后才返回失败

### 配置变更

- Agnes 模型升级：`config.llm.agnes.model` 从 `agnes-2.0-flash` 改为 `agnes-2.5-flash`（同步更新 process_articles.py 兜底默认值、config.readme.md、.env.example、.env.example.docker、AGENTS.md 黑名单）
- `config.llm.retry` 新增3个配置项：`retry_429_max_attempts`（默认3）、`retry_429_initial_delay_seconds`（默认10）、`retry_429_max_delay_seconds`（默认60）
- 版本号 1.4.0 → 1.4.1

### 不兼容变更

- 无（所有新增配置均有默认值，向下兼容）

---

## [1.4.0] - 2026-09-09

### 新增功能 - 热点事件类模板（hot_topic）

- 新增 `hot_topic` 热点事件类模板，适配科研发现、热点新闻、行业动态、社会事件+知识产权/科创申报类比的文章
- 核心约束：
  - 热点事件/公共信息占比≤20%，80%为知识产权独家实操复盘
  - 热点事件信息只极简引用（不超过2段），快速切入知识产权话题
  - 强制包含2个广东本地企业真实踩坑场景
  - 强制包含1个反常识独家观点
  - 强制包含1个本年度独家趋势观察
  - 关键数据准确性约束（软著周期30-60工作日、发明授权18-24个月）
- 匹配关键词：priority（科研、发现、研究、突破、首次、最新、热点、事件、新闻、科学家、院士、实验室、望远镜、卫星、芯片、AI、中子星、黑洞、基因、量子、航天、探测器、论文、期刊、发表）；match（技术、创新、企业、知识产权、专利、软著、启示、借鉴、类比、思考、背后、逻辑、原理、机制、证明、身份、户籍、路径）

### 功能优化 - 统一强化4个模板共性约束

- 所有模板新增禁止固定章节编号（一、二、三、1.1、2.1等）
- 所有模板新增禁止"全流程代办""一站式搞定""我们提供XX服务"等销售话术
- knowledge_share 模板新增强制2个广东本地企业踩坑场景+1个反常识观点
- 所有模板新增关键数据准确性约束
- policy_announcement 模板强化禁止章节编号表述

### 新增功能 - 3项后置校验

- **章节编号检测**（`banned_section_patterns`，19个模式）：输出中命中数必须为0，否则触发重试。用于避免AI同质化文章结构
- **营销话术检测**（`banned_marketing_phrases`，11个短语）：输出中命中数必须为0，否则触发重试
- **本地场景词检测**（`required_local_scene_words`，14个词 + `min_local_scene_hits=2`）：输出中命中数必须≥2，否则触发重试。用于确保包含足够广东本地企业实操内容
- 校验不通过时，重试 Prompt 自动追加对应强化要求（章节编号→删除序号改用自然小标题；营销话术→删除销售话术；本地场景→增加广东企业案例）

### 配置变更

- `config.content` 新增4个配置项：`banned_section_patterns`、`banned_marketing_phrases`、`required_local_scene_words`、`min_local_scene_hits`
- `config.templates.list` 新增第4个模板 `hot_topic`
- 版本号 1.3.0 → 1.4.0

### 不兼容变更

- 无（所有新增配置均有默认值，向下兼容）

---

## [1.3.0] - 2026-09-03

### 功能优化 - 原创度全面强化（解决公众号原创不通过问题）

- **policy_announcement 模板强化**：
  - `priority_keywords` 扩充 8 个词（展会/参展/征集/大会/论坛/报名/邀请函/政策解读），确保展会通知类文章能正确命中
  - `style_rules` 全面重构：新增【最高优先级·公众号原创硬性约束】4 条（公共信息≤25%、幻觉防护、内部统计标注来源、输出前自检）；强制要求 2 个广东本地企业踩坑场景 + 1 个本年度独家趋势观察 + 1 个反常识观点；禁止营销引流话术
- **knowledge_share 模板收窄**：将"专利"从 `priority_keywords` 降级为 `match_keywords`，避免政策公示类文章被干货科普模板抢走
- **全局 prompt 清理**：删除"保持原文核心信息不变，不增删关键事实"冲突条款（与原创目标直接矛盾）
- **新增后置原创度校验**：
  - `config.content` 新增 `originality_signal_words`（20 个独家内容信号词）和 `min_originality_hits`（默认 5）
  - `process_articles.py` 新增 `count_originality_hits()` 函数
  - 重试循环校验条件从"利益关键词≥3"改为"利益关键词≥3 AND 原创信号词≥5"
  - 原创度不足时，重试 Prompt 自动追加强化要求（增加独家案例/踩坑复盘/趋势观察，减少公共信息复述）
- **模板匹配增强**：
  - `config.templates` 新增 `force_policy_keywords`（9 个通知类强信号词）和 `force_policy_context_keywords`（9 个上下文词）
  - `match_template()` 新增通知类强信号检测：两组关键词同时命中时，强制匹配 `policy_announcement`，从根本上解决模板误匹配问题
- **弱化营销属性**：
  - 全模板 `style_rules` 新增禁止"免费评估/免费帮你/留言送方案/私信领取"等营销引流话术
  - `customer_segments.json` 中 manufacture / tech_company / general 的 `comment_question` 和 `interact_hook` 全部去掉"免费"话术，改为纯粹的知识交流风格（如"关于XX，你有什么想了解的？欢迎留言交流"）

### 不兼容变更

- 无（所有新增配置均有默认值，向下兼容；`config.prompt` 保留作为回退）

---

## [1.2.0] - 2026-08-21

### 新增功能 - 多模板匹配机制（通过公众号原创检测）

- 新增 `config.templates` 多模板配置段，内置 3 个差异化改写模板：
  - **政策公示类**（`policy_announcement`）：适配入库名单、公示、新规、数据播报，一线申报总监视角，独家实操复盘
  - **干货科普类**（`knowledge_share`）：适配软著/专利/高企/财税科普，实战顾问视角，独家干货增量
  - **客户案例复盘类**（`case_review`）：适配客户服务案例、申报复盘，独家案例复盘，内容唯一性
- `process_articles.py` 新增 `load_templates()` 与 `match_template()`：按内容关键词打分匹配模板（`priority_keywords` 计 2 分、`match_keywords` 计 1 分，同分按 `match_priority` 决胜，全部未命中回退 `default_template`）
- `build_prompt()` 重构为按匹配模板组装 Prompt；`templates.list` 为空时自动回退旧 `config.prompt` 单模板逻辑（向下兼容）
- 匹配到的模板 `role` 在 Agnes 模式下作为 System Prompt 传入
- 输出 frontmatter 新增 `template` / `template_name` 字段，记录实际使用的改写模板
- 新增 `content.default_title_prefix`（默认 `【老板必看】`），替换代码中硬编码的标题前缀默认值

### 功能优化

- 客户群体匹配（`customer_segments.json`）保留为标题前缀/受众画像层，与模板匹配（写作风格层）解耦

### 不兼容变更

- 无（`config.prompt` 保留，作为 `templates.list` 为空时的回退逻辑）

---

## [1.1.11] - 2026-07-29

### Prompt 优化 - 提升用户"收获感"
- 新增【让用户有'收获感'的核心要求 - 最重要】章节，包含 8 项具体要求：
  1. 信息增量：补充 2-3 个"不知道但应该知道"的知识点
  2. 可执行清单：转化为 3 步可执行 / 5 个避坑点等具体动作
  3. 数字/案例落地：引用权威数据、官方文件、具体金额、时间节点
  4. 痛点共鸣 + 解决方案：每观点回答"对客户意味着什么"
  5. 专业深度展示：自然融入商标撤三、专利优先审查等专业概念
  6. 场景化叙事：用"小王的公司""张老板的工厂"等具体场景
  7. 反常识洞察：至少 1 个"大多数人以为...其实..."观点
  8. 知识卡片/工具箱：使用 📌 划重点、⚠️ 注意 等小贴士
- 新增禁止：空话套话（"总之""综上所述""值得注意的是"等）

---

## [1.1.10] - 2026-07-29

### Bug 修复
- **严重**：修复输出内容是思考过程而非最终文章的问题
- 原因：Agnes API 即使关闭 thinking 参数，仍会返回 `reasoning_content` 字段
- 修复：响应解析优先取 `content`（最终输出），仅在 content 为空时兜底使用 `reasoning_content`

---

## [1.1.9] - 2026-07-29

### 文件重命名
- 将 `standard-template.txt` 重命名为 `standard-template.md`
- 更新所有代码和配置中的文件引用：
  - config.json: standard_template_ref, template_file
  - process_articles.py: STANDARD_FILE 默认值和注释
  - Dockerfile: COPY 指令
  - AGENTS.md, config.readme.md, DOCKER.md: 文档引用

---

## [1.1.8] - 2026-07-29

### Prompt 优化
- **重要**：新增【严禁输出的标记文字】章节，明确禁止在正文中出现：
  - 结构术语：SCQA、SC、S、C、Q、A
  - 层级标记：H1、H2、H3、L1、L2、L3、L4
  - 模块标记：可转发理由、留言互动、顶部引导等
  - 章节编号：一、二、三 或 1.1、2.1 等
  - 格式说明：emoji 点缀、H2 小标题等
- 优化 task_template：明确标注写作参考与实际输出的区别
- 移除【可转发理由】【留言互动】的方括号标记要求，改为自然表达

### 新增功能
- 新增禁止事项：不得出现"正确做法""参考""说明"等指导性文字
- 新增禁止事项：不得使用"你应该""必须""一定要"等命令式口吻

---

## [1.1.7] - 2026-07-29

### 配置变更
- 关闭 Agnes-2.0-Flash 默认的 thinking 模式
- 经测试验证，开启 thinking 后响应结构无变化（无 reasoning_content），生成内容完全相同

---

## [1.1.6] - 2026-07-29

### Bug 修复
- **严重**：修复 Agnes API 开启 thinking 模式后返回 200 但内容为空的问题。原因是 `thinking=true` 时响应结构不同，实际内容在 `reasoning_content` 而非 `content` 字段

### 优化
- 增加响应解析的兼容性：优先取 `reasoning_content`，fallback 到 `content`，支持数组格式的 content
- 增加调试日志：打印响应 JSON 的 keys 结构，方便排查问题

---

## [1.1.5] - 2026-07-29

### Bug 修复
- **严重**：修复 `main.py` 在使用 Agnes 模型时仍然检查 Ollama 服务的问题，导致容器因找不到 Ollama 而跳过所有文件处理
- `check_ollama_service()` 现在会根据 `LLM_PROVIDER` 判断，`agnes` 模式下直接跳过检查

### 影响
- 容器启动后将直接处理文件，不再等待 Ollama 服务
- 日志显示当前使用的 LLM 类型（如 `LLM: agnes`）

---

## [1.1.4] - 2026-07-29

### 功能优化
- 新增 `.env` 配置文件，默认启用 Agnes 云端模型（`LLM_PROVIDER=agnes`）
- 修改 `entrypoint.sh` 默认 LLM_PROVIDER 从 `ollama` 改为 `agnes`
- 修改 `docker-compose.yml` 默认 LLM_PROVIDER 从 `ollama` 改为 `agnes`

### 影响
- 容器启动时不再等待本地 Ollama 服务，直接调用 Agnes API
- 用户可通过修改 `.env` 中的 `LLM_PROVIDER=ollama` 切换回本地模型

---

## [1.1.3] - 2026-07-29

### Bug 修复
- 将 Agnes API 域名从 `apihub.agnes-ai.com` 更新为 `apihub.agnes-ai.cn`（覆盖 6 个文件：config.json、process_articles.py、.env.example、.env.example.docker、DOCKER.md、config.readme.md）

### 不兼容变更
- 无（仅域名替换，路径与参数完全一致）

---

## [1.1.2] - 2026-07-29

### Bug 修复
- **严重**：修复 `build_prompt()` 未加载 `standard-template.txt` 实际内容的问题——之前仅将文件名字符串放入 Prompt，导致 LLM 完全不知道标准模块结构
- **严重**：修复 `build_prompt()` 未将 `required_sections_after_body`（【可转发理由】/【留言互动】详细要求）注入 Prompt 的问题
- 修复 `entrypoint.sh` 中 OLLAMA_HOST/OLLAMA_PORT 默认值无注释说明与 config.json 同步关系的问题

### 优化
- `build_prompt()` 新增 `{standard_template}` 和 `{required_sections_block}` 占位符，确保 config 的所有配置都能完整传递到 Prompt
- `config.readme.md` 的 prompt 章节更新，明确 `standard_template_ref` 的行为是"读取文件内容"而非"引用文件名"

### 不兼容变更
- 无（功能增强，向下兼容）

---

## [1.1.1] - 2026-07-29

### Bug 修复
- **严重**：修复 Dockerfile 未将 `config.json` / `config.readme.md` 拷贝进镜像的问题。容器将默认 fallback 到代码内嵌默认值，导致 `config.json` 的作用完全失效
- 修复 `call_ollama_api()` 中 URL、model、timeout 全部硬编码，忽略 `OLLAMA_API_URL` / `OLLAMA_MODEL` 环境变量的**功能级 bug**（即使改了 `.env` 也不会生效）
- 修复 `call_agnes_api()` 中 timeout / max_tokens / temperature / thinking 硬编码，忽略 config.agnes 的问题
- 修复 Prompt 模板过于精简导致丢失原有完整指令（6 条内容规则 + 7 条禁止事项）的问题，已完整还原至 config.prompt.*
- 修复 `build_prompt()` 中旧模板占位符与实际传递参数不匹配导致 KeyError 的问题
- 修复 `call_agnes_api()` 未将 `default_system_prompt` 与 `call_ollama_api()` 的角色定义统一的问题

### 功能优化
- Prompt 结构从单模板改为分块（role / style_rules / company_background / standard_template_ref），方便单独调整某段而不破坏整体
- 新增 `build_prompt()` 动态插入的运行期规则：标题前缀 + 最低利益条数要求，直接进入 Prompt 最后一段，提升 LLM 遵从度
- `config.readme.md` 的 prompt 章节同步新增 `role`、`standard_template_ref` 字段说明，占位符列表更新

### 不兼容变更
- 无（仅修复 bug，配置 schema 向下兼容）

---

## [1.1.0] - 2026-07-29

### 新增功能
- 新增 [config.json](./config.json) 集中配置文件，所有业务常量（IP、端口、模型名、超时、重试次数、Prompt 模板、利益关键词、风格规则等）全部迁移至此文件
- 新增 [config.readme.md](./config.readme.md) 配置说明文档，覆盖 config.json 全部字段的字段名、类型、默认值、用途、修改约定
- 新增项目级 [AGENTS.md](./AGENTS.md)，记录本项目特有的 Docker / LLM / 文件处理 / 硬编码黑名单等约束
- [main.py](./main.py) 与 [process_articles.py](./process_articles.py) 新增 `load_config()` + `cfg_get()` 通用配置加载器，支持 config.json 损坏时 fallback 到内嵌默认值
- Prompt 组装逻辑重构为 `build_prompt()`，所有 Prompt 片段从 config.prompt 目录组装
- Dockerfile 同步将 `config.json` / `config.readme.md` 拷贝进镜像

### 功能优化
- 移除业务代码中的硬编码常量（192.168.*、11434、3600、300、10、60、2、3、4096、0.7、qwen3.5:latest、agnes-2.0-flash、Prompt 模板、利益关键词、系统提示词等）
- Ollama / Agnes 的超时、Temperature、MaxTokens、Thinking 开关、System Prompt 全部可通过 config.json 调整

### Bug 修复
- **严重**：修复 `call_ollama_api()` 中 URL 硬编码，完全绕过 `OLLAMA_HOST` / `OLLAMA_PORT` 环境变量的问题
- 修复 `call_agnes_api()` 中参数硬编码问题
- 修复 Prompt 结构中存在的冗余与字段不一致问题

### 不兼容变更
- 配置 schema 变更：旧版 Prompt 相关字段散落代码中，新版集中于 `config.json`；未迁移的字段已在代码侧保留等价默认值

---

## [1.0.0] - 2026-07-29

### 新增功能（已归档）
- 初始化版本号与变更日志体系（首版）
- 基于 Ollama 的本地文章改写流水线
- 统一 LLM 调用入口 `call_llm_api()`，支持 Ollama / Agnes 双后端
- 5 类客户群体关键词识别、标题前缀、YAML frontmatter
- 改写质量校验 + 自动重试
- Docker 化部署（非 root 运行、外部网络、资源限制、restart=always）
- entrypoint.sh 加载 .env、等待 Ollama、切非 root

### Bug 修复
- （首版，无历史记录）

### 不兼容变更
- （首版）
