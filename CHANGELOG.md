# 更新日志

> 本项目遵循 [AGENTS.md](./AGENTS.md) 规范，按语义化版本号（X.Y.Z）管理。
> - X：不兼容的架构变更
> - Y：新增功能、模块
> - Z：bug 修复、小优化
> - 所有可配置常量统一在 [config.json](./config.json) 管理，配套文档 [config.readme.md](./config.readme.md)。

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
