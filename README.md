# Ollama 文章改写项目

## 项目功能

本项目使用 Ollama 本地大模型（如 qwen3.5）按照标准模块构成自动改写文章，主要功能包括：

1. **自动处理文章**：遍历 `new` 目录中的所有文章文件
2. **标准模块改写**：按照 `01-标准模块构成.txt` 中的规范改写文章
3. **文件管理**：处理完成后将原文件移动到 `old` 目录，改写后的文章保存到 `output` 目录
4. **多文件支持**：支持同时处理多个文章文件
5. **按原文件名命名**：改写后的文章使用原文件名保存

## 目录结构

```
.
├── 01-标准模块构成.txt  # 文章改写的标准模块构成
├── new/              # 存放待处理的文章
├── old/              # 存放已处理的原文章
├── output/           # 存放改写后的文章
├── process_articles.py  # 主处理脚本
├── README.md         # Linux 环境说明
└── README-Windows.md # Windows 环境说明
```

## 环境要求

- Python 3.7+
- Ollama 本地服务
- qwen3.5 模型

## 安装步骤

### 1. 克隆项目

```bash
# 克隆项目到本地
git clone <your-repository-url>
cd ollama-prompt-autowrite

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install requests
```



## 运行方法

### 1. 准备文章

将需要改写的文章放入 `new` 目录中，文章格式应为 Markdown 文件或 JSON 文件（JSON文件需包含text字段）。

### 2. 配置 Ollama API

确保 Ollama 服务正在运行，并且 qwen3.5 模型已安装。脚本会自动连接到本地 Ollama API 服务：

- API 地址：`http://localhost:11434/api/generate`
- 使用模型：`qwen3.5:latest`
- 超时设置：300秒（5分钟）

### 3. 运行脚本

#### 前台运行

```bash
# 激活虚拟环境（如果尚未激活）
source venv/bin/activate

# 运行脚本
python process_articles.py
```

#### 后台运行

```bash
# 激活虚拟环境（如果尚未激活）
source venv/bin/activate

# 后台运行脚本
nohup python process_articles.py > process.log 2>&1 &

# 查看运行状态
ps aux | grep process_articles.py

# 查看日志
tail -f process.log
```

### 4. 查看结果

- 改写后的文章会保存在 `output` 目录中，使用原文件名
- 原文章会被移动到 `old` 目录中

## Git 推送步骤

### 1. 初始化 Git 仓库（如果尚未初始化）

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repository-url>
git push -u origin main
```

### 2. 推送更新

```bash
# 查看修改
git status

# 添加修改
git add .

# 提交修改
git commit -m "Update: 完善功能"

# 推送修改
git push
```

## CentOS 正式环境部署

### 1. 环境准备

```bash
# 安装 Python 3
sudo yum install python3 python3-pip python3-venv -y

# 安装 Git
sudo yum install git -y

# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

sudo systemctl start ollama
sudo systemctl enable ollama

# 拉取 qwen3.5 模型
ollama pull qwen3.5
```

### 2. 拉取项目

```bash
# 创建项目目录
sudo mkdir -p /opt/ollama-prompt-autowrite
sudo chown $USER:$USER /opt/ollama-prompt-autowrite

# 克隆项目
cd /opt/ollama-prompt-autowrite
git clone <your-repository-url> .

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖（如果需要）
pip install -r requirements.txt
```

### 3. 配置定时任务

```bash
# 编辑定时任务
crontab -e

# 添加定时任务（每小时执行一次）
0 * * * * cd /opt/ollama-prompt-autowrite && source venv/bin/activate && python process_articles.py >> /var/log/ollama-process.log 2>&1

# 查看定时任务
crontab -l
```

### 4. 监控日志

```bash
# 查看执行日志
tail -f /var/log/ollama-process.log

# 查看 Ollama 服务状态
sudo systemctl status ollama
```

## 注意事项

1. 确保 Ollama 服务正常运行
2. 确保 qwen3.5 模型已成功拉取
3. `new` 目录中的文章格式应为 Markdown 文件
4. 脚本会自动处理 `new` 目录中的所有文件
5. 处理完成后，原文件会被移动到 `old` 目录，改写后的文章会保存到 `output` 目录

## 故障排除

### 1. Ollama 服务未启动

```bash
# 启动 Ollama 服务
sudo systemctl start ollama

# 检查服务状态
sudo systemctl status ollama
```

### 2. 模型未拉取

```bash
# 拉取 qwen3.5 模型
ollama pull qwen3.5

# 查看已安装的模型
ollama list
```

### 3. 权限问题

```bash
# 确保目录权限正确
sudo chown -R $USER:$USER /opt/ollama-prompt-autowrite
```

## 联系方式

如有问题，请联系项目维护者。
