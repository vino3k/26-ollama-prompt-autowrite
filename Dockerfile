FROM python:3.11-slim

# ===== 基础环境 =====
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Asia/Shanghai \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ===== 系统依赖 =====
# 仅安装必要的 curl（healthcheck 用），无需编译工具
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && rm -rf /var/lib/apt/lists/*

# ===== 工作目录 =====
WORKDIR /app

# ===== 先复制依赖文件以利用 Docker 缓存 =====
COPY requirements.txt ./

# ===== 安装 Python 依赖 =====
RUN pip install --no-cache-dir -r requirements.txt

# ===== 复制应用代码 =====
COPY main.py            ./
COPY process_articles.py ./
COPY customer_segments.json ./
COPY standard-template.txt ./

# ===== 运行时目录 =====
# 这些目录是数据卷挂载点，容器启动时会被宿主机目录覆盖
# 但保留目录结构（即使挂载空目录也能 work）
RUN mkdir -p new old output logs

# ===== 入口脚本 =====
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ===== 非 root 用户运行（安全） =====
RUN useradd -m -u 1000 -s /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# ===== 启动入口 =====
ENTRYPOINT ["/entrypoint.sh"]
