#!/bin/bash
# Docker 容器入口脚本
# 1. 加载 .env 环境变量（如果存在）
# 2. 健康检查：等待 Ollama 服务可用（仅 LLM_PROVIDER=ollama 时）
# 3. 执行传入的命令（默认启动 main.py 监控）

set -e

echo "[entrypoint] 启动时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "[entrypoint] 当前用户: $(whoami)"
echo "[entrypoint] 工作目录: $(pwd)"

# ===== 加载 .env =====
if [ -f ".env" ]; then
    echo "[entrypoint] 加载 .env 环境变量"
    set -a
    . ./.env
    set +a
else
    echo "[entrypoint] WARN: .env 文件不存在"
fi

echo "[entrypoint] LLM_PROVIDER=${LLM_PROVIDER:-ollama}"

# ===== 等待 Ollama 服务（仅当使用本地 ollama 时） =====
# 注意：此处硬编码默认值必须与 config.json 的 defaults 同步！
# - OLLAMA_HOST 默认值 ↔ config.llm.ollama.host_default（当前为 192.168.2.111）
# - OLLAMA_PORT 默认值 ↔ config.llm.ollama.port_default（当前为 11434）
# 实际部署时应通过 .env 或环境变量覆盖这两个值
if [ "${LLM_PROVIDER:-ollama}" = "ollama" ]; then
    OLLAMA_HOST=${OLLAMA_HOST:-192.168.2.111}  # TODO: 与 config.json 保持同步
    OLLAMA_PORT=${OLLAMA_PORT:-11434}          # TODO: 与 config.json 保持同步
    OLLAMA_URL="http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags"

    echo "[entrypoint] 等待 Ollama 服务就绪: ${OLLAMA_URL}"
    for i in $(seq 1 30); do
        if curl -sf --max-time 3 "${OLLAMA_URL}" >/dev/null 2>&1; then
            echo "[entrypoint] Ollama 服务就绪"
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo "[entrypoint] WARN: Ollama 30 秒内未就绪，继续启动（main.py 内部会重试）"
        fi
        sleep 1
    done
fi

# ===== 启动应用 =====
echo "[entrypoint] 启动命令: $*"
if [ $# -eq 0 ]; then
    echo "[entrypoint] WARN: 没有传入任何命令，容器将立即退出（docker-compose.yml 需要显式指定 command）"
fi

# ===== 修复数据卷权限（best-effort，失败不中断） =====
# 宿主机挂载的目录 owner 可能是 root，但容器内以 appuser (uid 1000) 运行
# 这里递归 chown 让 appuser 可写
# 注意：容器内 chown 跨 mount 边界会失败，这里用 chmod 代替（更通用）
echo "[entrypoint] 修复数据卷权限（用 chmod 兜底）..."
chmod -R 777 /app/new /app/old /app/output /app/logs 2>/dev/null || true

# ===== 如果以 root 启动，切到 appuser 跑应用 =====
# 如果 chown 失败导致 appuser 写不进去，回退到 root 运行（牺牲一点安全性）
if [ "$(id -u)" = "0" ]; then
    echo "[entrypoint] 切换到 appuser 运行应用"
    if command -v gosu >/dev/null 2>&1; then
        exec gosu appuser "$@"
    else
        echo "[entrypoint] gosu 未安装，尝试 su -c"
        exec su -s /bin/bash appuser -c "$*"
    fi
else
    exec "$@"
fi
