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
if [ "${LLM_PROVIDER:-ollama}" = "ollama" ]; then
    OLLAMA_HOST=${OLLAMA_HOST:-host.docker.internal}
    OLLAMA_PORT=${OLLAMA_PORT:-11434}
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
echo "[entrypoint] 启动命令: $@"
exec "$@"
