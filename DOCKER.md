# Docker / Docker Compose 部署指南

> 本项目支持 Docker Compose 一键部署。所有运行时数据（`new/old/output/logs`）通过 **Volume 挂载到宿主机**，保证数据持久化，容器重建不丢失。

---

## 一、前置条件

### 1. 宿主环境

| 组件 | 版本 | 用途 |
|---|---|---|
| Docker | ≥ 20.10 | 容器运行时 |
| Docker Compose | ≥ v2.0 | 编排工具 |
| Ollama | ≥ 0.3.0（可选） | 本地 LLM 服务 |

### 2. 项目代码

```bash
# 从 Git 仓库拉取（以你的仓库地址为准）
git clone ssh://vino@192.168.2.27/data/git-share/26-ollama-prompt-autowrite.git
cd 26-ollama-prompt-autowrite
```

### 3. 准备 .env 文件

```bash
# 复制模板（Docker 版）
cp .env.example.docker .env

# 编辑 .env，填入真实值
vim .env
```

`.env` 关键配置说明：

| 变量 | 必填 | 说明 |
|---|---|---|
| `LLM_PROVIDER` | 是 | `ollama`（默认，访问宿主 Ollama） / `agnes`（云端 API） |
| `OLLAMA_HOST` | 仅 ollama | Docker 容器内访问宿主机 Ollama 的地址，一般用 `host.docker.internal` |
| `OLLAMA_PORT` | 仅 ollama | Ollama 端口，默认 `11434` |
| `AGNES_API_KEY` | 仅 agnes | 在 https://apihub.agnes-ai.cn/ 申请的 API Key |

---

## 二、部署步骤

### 步骤 1：构建镜像

```bash
docker compose build
```

> **首次构建**会下载 `python:3.11-slim` 基础镜像并安装依赖，耗时约 2-5 分钟。

### 步骤 2：启动容器

```bash
# 后台启动
docker compose up -d

# 查看实时日志（推荐调试时使用）
docker compose logs -f
```

### 步骤 3：验证部署

```bash
# 查看容器状态（应显示 "Up" 和 "(healthy)"）
docker compose ps

# 查看应用日志
docker compose logs --tail=100 app

# 进入容器调试
docker compose exec app bash
```

正常日志应包含：

```
[entrypoint] 启动时间: 2026-XX-XX XX:XX:XX
[entrypoint] 加载 .env 环境变量
[entrypoint] LLM_PROVIDER=ollama
[entrypoint] 等待 Ollama 服务就绪: http://host.docker.internal:11434/api/tags
[entrypoint] Ollama 服务就绪
[entrypoint] 启动命令: python -u main.py
[2026-XX-XX XX:XX:XX] Ollama 文章处理监控系统启动
[2026-XX-XX XX:XX:XX] 当前文件数: 0
```

---

## 三、关键设计

### 1. 数据持久化

`docker-compose.yml` 中通过 volumes 把容器内目录映射到宿主机：

| 容器内 | 宿主机 | 用途 |
|---|---|---|
| `/app/new` | `./files/26-ollama-prompt-autowrite/00_new` | 待处理文件输入 |
| `/app/old` | `./files/26-ollama-prompt-autowrite/01_old` | 已处理文件备份 |
| `/app/output` | `./files/26-ollama-prompt-autowrite/02_output` | 改写后的 md 输出 |
| `/app/logs` | `./logs/26-ollama-prompt-autowrite` | 应用日志和锁文件 |
| `/app/.env` | `./.env` | 配置（**只读**挂载） |

**数据卷命名规范**（与正式环境 `biz-net` 网络下的所有服务保持一致）：
- `files/<服务名>/00_new/`、`01_old/`、`02_output/` — 业务数据
- `logs/<服务名>/` — 日志和运行时文件

**好处**：
- 容器重建不丢失数据
- 宿主机可以直接查看/编辑文件
- 共享同一个数据目录，团队协作方便

### 2. 访问宿主 Ollama

`docker-compose.yml` 关键配置：

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

**作用**：让容器内 `host.docker.internal` 解析为宿主机网关 IP，从而访问宿主机上的 Ollama 服务。

**Linux 注意**：`host.docker.internal` 是 Docker Desktop (Mac/Windows) 默认支持的；Linux 平台 Docker 20.10+ 通过 `host-gateway` 自动支持。如果你的环境不支持，需要：
- 改用宿主机局域网 IP（如 `OLLAMA_HOST=192.168.2.111`）
- 或将 Ollama 也容器化，加入同一个 docker network

### 3. 应用代码

- **基础镜像**：`python:3.11-slim`（体积约 120MB）
- **非 root 运行**：创建 `appuser` 用户运行应用
- **自动重启**：`restart: always` 策略（与正式环境其他服务保持一致）
- **时区**：`Asia/Shanghai`
- **网络**：使用外部网络 `biz-net`（与正式环境 nginx/mysql/redis 等服务互通）

### 4. 资源限制

正式环境采用保守资源限制（防止单服务占用过多资源影响其他服务）：

```yaml
deploy:
  resources:
    limits:
      cpus: "0.5"
      memory: "1G"
```

如果业务量大，可在 docker-compose.yml 中调整。

---

## 四、常用运维命令

### 启动 / 停止

```bash
docker compose up -d          # 后台启动
docker compose stop           # 停止（不删除）
docker compose start          # 启动已停止的容器
docker compose restart        # 重启
docker compose down           # 停止并删除容器（数据卷保留）
```

### 查看日志

```bash
docker compose logs -f                # 实时跟踪
docker compose logs --tail=200 app    # 最近 200 行
docker compose logs --since 1h app    # 最近 1 小时
```

### 一次性手动处理

```bash
# 进入容器执行一次 process_articles.py
docker compose exec app python -u process_articles.py

# 跑完后可继续由 main.py 监控
```

### 数据备份

```bash
# 备份生成的文章
tar -czf backup-$(date +%Y%m%d).tar.gz ./output ./old

# 恢复
tar -xzf backup-20260428.tar.gz
```

### 切换 LLM 提供方

```bash
# 1. 修改 .env
sed -i 's/LLM_PROVIDER=ollama/LLM_PROVIDER=agnes/' .env

# 2. 重启容器
docker compose restart

# 3. 查看日志确认切换成功
docker compose logs --tail=20
```

### 更新代码

```bash
# 1. 拉取最新代码
git pull origin master

# 2. 重新构建（仅当依赖/脚本有变化时）
docker compose build

# 3. 重启容器
docker compose up -d
```

---

## 四、集成到正式环境

你的正式环境采用统一的 docker-compose 编排，所有服务共享外部网络 `biz-net`。本服务的 `docker-compose.yml` 已经是正式环境风格：

### 1. 与其他服务的关系

- **网络**：使用与 nginx/mysql/redis/46todolist_wisdom 等服务相同的 `biz-net` 外部网络
- **数据卷**：与 `16-dingtalk-daily-info` 一样的 `files/<服务名>/00_xxx`、`logs/<服务名>/` 规范
- **重启策略**：`always`（与正式环境所有服务保持一致）
- **资源限制**：保守 0.5 CPU / 1G 内存（参考 `46todolist_wisdom` 的 0.3/512M）

### 2. 部署到正式环境

假设正式环境 `biz-net` 已存在，部署步骤：

```bash
# 1. 进入项目目录
cd /data/26-ollama-prompt-autowrite

# 2. 准备数据卷目录
mkdir -p files/26-ollama-prompt-autowrite/{00_new,01_old,02_output}
mkdir -p logs/26-ollama-prompt-autowrite

# 3. 准备 .env
cp .env.example.docker .env
vim .env   # 填入 AGNES_API_KEY 等

# 4. 启动（注意：因使用外部网络，需先确保 biz-net 已存在）
docker compose up -d

# 5. 验证
docker compose ps
docker compose logs --tail=50
```

### 3. 与正式环境其他服务共存

如果 `biz-net` 网络是某个父级 docker-compose 创建的，子服务需要使用 `external: true`：

```yaml
# 本服务 docker-compose.yml 已正确配置
networks:
  biz-net:
    external: true
```

这样你**不需要**修改父级 docker-compose，只需在项目目录下 `docker compose up -d` 即可加入 `biz-net`。

### 4. 数据卷目录说明

正式环境下数据卷结构：

```
/data/26-ollama-prompt-autowrite/
├── docker-compose.yml
├── .env
├── files/
│   └── 26-ollama-prompt-autowrite/
│       ├── 00_new/        # 待处理文章
│       ├── 01_old/        # 已处理原文
│       └── 02_output/     # 改写输出
└── logs/
    └── 26-ollama-prompt-autowrite/
        ├── monitor.log
        └── .monitor.lock
```

---

## 五、CentOS 7 部署示例

### 1. 安装 Docker

```bash
# 卸载旧版
sudo yum remove -y docker docker-client docker-client-latest \
    docker-common docker-latest docker-engine

# 安装依赖
sudo yum install -y yum-utils device-mapper-persistent-data lvm2

# 添加 Docker 仓库
sudo yum-config-manager --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 验证
docker --version
docker compose version
```

### 2. 配置镜像加速（可选，国内服务器）

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://hub-mirror.c.163.com"
  ]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 3. 部署项目

```bash
# 进入工作目录
cd /data/26-ollama-prompt-autowrite

# 准备 .env
cp .env.example.docker .env
vim .env   # 填入 AGNES_API_KEY 等

# 构建并启动
docker compose build
docker compose up -d

# 验证
docker compose ps
docker compose logs --tail=50
```

### 4. 防火墙（如果需要远程访问）

```bash
# 开放 22（SSH）和 11434（Ollama 远程访问，可选）
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=11434/tcp
sudo firewall-cmd --reload
```

---

## 六、常见问题

### Q1：容器启动后日志显示 "Ollama 30 秒内未就绪"

**原因**：宿主机 Ollama 未启动，或 `host.docker.internal` 无法解析。

**排查**：
```bash
# 1. 宿主机测试 Ollama 是否运行
curl http://localhost:11434/api/tags

# 2. 容器内测试能否访问
docker compose exec app curl -v http://host.docker.internal:11434/api/tags

# 3. 如果不通，改用宿主机局域网 IP
echo "OLLAMA_HOST=192.168.2.111" >> .env
docker compose restart
```

### Q2：切换到 Agnes 后报错 "AGNES_API_KEY not set"

**排查**：
```bash
# 进入容器查看环境变量
docker compose exec app env | grep AGNES

# 如果未设置，检查 .env 挂载
docker compose exec app cat /app/.env
```

### Q3：如何查看 OLLAMA 实时处理进度

```bash
# 1. 实时跟踪日志
docker compose logs -f app

# 2. 进入容器查看文件变化
docker compose exec app ls -la new/ old/ output/
```

### Q4：容器内时间和宿主机时间不一致

容器内时区已设置为 `Asia/Shanghai`。如仍有偏差：

```bash
# 进入容器确认
docker compose exec app date

# 宿主机时间
date
```

### Q5：磁盘空间不足

```bash
# 清理无用 Docker 资源
docker system prune -a

# 清理已停止的容器
docker container prune
```

---

## 七、目录结构（部署后）

```
26-ollama-prompt-autowrite/          # 项目根目录
├── .env                             # 运行时配置（API Key 等）
├── .env.example.docker              # 配置模板
├── docker-compose.yml               # Compose 配置
├── Dockerfile                       # 镜像构建文件
├── requirements.txt                 # Python 依赖
├── entrypoint.sh                    # 容器入口脚本
├── main.py                          # 监控脚本
├── process_articles.py              # 处理脚本
├── customer_segments.json           # 客户群体配置
├── standard-template.txt            # 改写模板
├── new/                             # 待处理文件（挂载）
│   └── 01_first_level/
├── old/                             # 已处理文件（挂载）
├── output/                          # 生成的文章（挂载）
└── logs/                            # 日志（挂载）
    ├── monitor.log
    └── process_articles_*.log
```

---

## 八、文件传输

从本地 Windows 上传文件到服务器后，需要修复换行符：

```bash
# Linux/CentOS 服务器上
dos2unix entrypoint.sh
# 或
sed -i 's/\r$//' entrypoint.sh
chmod +x entrypoint.sh
```

> Windows 推送的 shell 脚本会带 `CRLF` 换行符，Linux 运行会报 `\r command not found`。
