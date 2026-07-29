# AGENTS.md —— 项目级 AI 协作规则

> 本文件是项目 AI 辅助开发的**本地规则入口**，与全局 AGENTS.md 保持一致，补充本项目特有的约束。
> 全局规则（版本号、CHANGELOG、敏感信息、config 集中化）以全局 AGENTS.md 为准；本文件仅记录项目特有约定。

---

## 1. 项目基础信息

- **项目名**：26-ollama-prompt-autowrite
- **技术栈**：Python 3.11 + requests + Docker Compose
- **入口文件**：main.py（监控循环）、process_articles.py（单次改写）、entrypoint.sh（容器入口）
- **配置入口**：config.json（所有常量）+ .env（敏感值，**禁止入库**）

## 2. 目录约定

```
/
├── main.py              # 监控守护进程
├── process_articles.py  # 单次改写逻辑
├── entrypoint.sh        # Docker 入口（加载 .env、等待 Ollama、切非 root）
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── config.json          # ★ 集中配置，所有业务固定值的唯一起点
├── config.readme.md     # ★ config.json 的强制配套文档
├── customer_segments.json  # 客户群体识别规则（非敏感）
├── standard-template.txt   # 改写结构模板（非敏感）
├── VERSION.txt
├── CHANGELOG.md
├── .env                 # 敏感值（必须 .gitignore）
├── .env.example         # 本地开发模板
├── .env.example.docker  # Docker 部署模板
├── new/                 # 待处理源文件
├── old/                 # 已处理源文件备份
├── output/              # 改写后输出
└── logs/                # 运行日志（monitor.log / .monitor.lock）
```

## 3. Docker 约束（强制）

1. 外部网络 `biz-net`（`external: true`），不得自建 bridge
2. restart 策略：`always`（与正式环境其他服务一致）
3. **不使用 healthcheck**（避免与正式环境不一致）
4. 资源上限：`cpus: "0.5"`、`memory: "1G"`
5. `.env` 以 `ro`（只读）方式挂载 `/app/.env:ro`
6. entrypoint 使用 `gosu appuser` 切非 root 运行；无法切换则回退 root（有明确警告日志）

## 4. LLM 路由规则

1. 单一入口 `call_llm_api(prompt)`，不允许直接在业务代码中调用 Ollama / Agnes
2. Provider 路由依据 `LLM_PROVIDER` 环境变量（或 `config.llm.provider_env` 指定的变量名）
3. 敏感值（`AGNES_API_KEY`）**只能**从环境变量读取，config.json 中仅出现变量名
4. Ollama 的 `host/port/model` 支持环境变量覆盖；配置项中的默认值仅作兜底

## 5. 文件处理规则

1. `new/` → 处理 → `output/` + 备份到 `old/`（保持相对路径结构）
2. 跨设备文件移动**必须**用 `shutil.copy2 + os.remove`，禁止 `shutil.move` 直接跨挂载
3. 支持 `.md` 和 `.json` 两种源文件（`.json` 会自动转换为 `.md` 输出）
4. 运行锁 `.monitor.lock` 超时 **3600 秒**（与 `monitor.lock_max_age_seconds` 一致）

## 6. 硬编码黑名单（项目特有）

以下常量**禁止**在业务代码中出现，必须从 `config.json` 读取：

- 时间相关：3600、300、10、60（秒）
- 网络相关：`192.168.*.*`、`11434`、`:11434`
- 模型相关：`qwen3.5:latest`、`agnes-2.0-flash`
- 参数相关：`4096`（max_tokens）、`0.7`（temperature）、`2`（重试次数）、`3`（最低利益点）
- Prompt 模板、系统提示词、风格规则、公司背景
- 业务常量（`BENEFIT_KEYWORDS` 列表）

## 7. 提交前 Checklist（项目补充）

- [ ] 新增/修改 `config.json` 时同步更新 `config.readme.md`
- [ ] `entrypoint.sh` 中的默认值已与 `config.json` 保持一致
- [ ] Dockerfile 镜像版本在 `.env.example.docker` 中已标注
- [ ] 业务代码无裸 IP / 裸端口 / 裸模型名
- [ ] 运行锁过期时间 >= process 超时时间

## 8. 违规处理

- **首次**：AI 提示并给出修复方案
- **二次**：阻塞提交，必须修复后再继续
- **三次**：上报，评估是否需要引入 `pre-commit` 钩子扫描硬编码

---

> 全局规则以 IDE 内置 AGENTS.md 为准；本文件仅补充项目特有约束。两者冲突时**以全局规则为准**。
