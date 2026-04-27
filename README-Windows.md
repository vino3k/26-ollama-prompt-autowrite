# Ollama 文章改写项目（Windows 环境）

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

1. 打开命令提示符或 PowerShell
2. 运行以下命令克隆项目：
   ```powershell
   git clone <your-repository-url>
   cd ollama-prompt-autowrite
   ```

3. 创建虚拟环境：
   ```powershell
   python -m venv venv
   ```

4. 激活虚拟环境：
   ```powershell
   # PowerShell
   .\venv\Scripts\Activate.ps1
   
   # 命令提示符
   .\venv\Scripts\activate.bat
   ```

5. 安装依赖：
   ```powershell
   pip install requests
   ```

## 监控模式

### 自动监控

除了手动运行脚本外，您还可以使用 `main.py` 启动自动监控模式。该模式会每600秒检查一次new目录，当发现有新文件或文件有变化时，自动执行处理脚本。

#### 前台运行

```powershell
# 激活虚拟环境（如果尚未激活）
.\venv\Scripts\Activate.ps1  # PowerShell

# 运行监控脚本
python main.py
```

#### 后台运行

```powershell
# 激活虚拟环境（如果尚未激活）
.\venv\Scripts\Activate.ps1

# 后台运行监控脚本
Start-Job -ScriptBlock {
    cd "E:\00.AIGC\26-ollama-prompt-autowrite"
    python main.py
} -Name "OllamaMonitor"

# 查看后台任务状态
Get-Job

# 查看任务输出
Receive-Job -Name "OllamaMonitor"
```

#### 监控功能说明

- **定时检查**：每60秒检查一次new目录
- **自动检测**：通过文件哈希值检测新文件或文件变化
- **自动处理**：检测到变化后自动执行 `process_articles.py`
- **Ollama服务检查**：处理前会检查Ollama服务是否可用
- **日志记录**：所有操作都会显示在控制台

## 运行方法

### 1. 准备文章

将需要改写的文章放入 `new` 目录中，文章格式应为 Markdown 文件。

### 2. 运行脚本

#### 前台运行

```powershell
# 激活虚拟环境（如果尚未激活）
.\venv\Scripts\Activate.ps1  # PowerShell
# 或
.\venv\Scripts\activate.bat   # 命令提示符

# 运行脚本
python process_articles.py
```

#### 后台运行

```powershell
# 激活虚拟环境（如果尚未激活）
.\venv\Scripts\Activate.ps1

# 后台运行脚本
Start-Job -ScriptBlock {
    cd "C:\path\to\ollama-prompt-autowrite"
    python process_articles.py
} -Name "OllamaProcess"

# 查看后台任务状态
Get-Job

# 查看任务输出
Receive-Job -Name "OllamaProcess"
```

### 3. 查看结果

- 改写后的文章会保存在 `output` 目录中，使用原文件名
- 原文章会被移动到 `old` 目录中

## Git 推送步骤

### 1. 初始化 Git 仓库（如果尚未初始化）

```powershell
# 初始化 Git 仓库
git init

# 添加文件
git add .

# 提交修改
git commit -m "Initial commit"

# 添加远程仓库
git remote add origin <your-repository-url>

# 推送代码
git push -u origin main
```

### 2. 推送更新

```powershell
# 查看修改
git status

# 添加修改
git add .

# 提交修改
git commit -m "Update: 完善功能"

# 推送修改
git push
```

## 定时执行

### 使用任务计划程序

1. 打开「任务计划程序」
2. 点击「创建基本任务」
3. 填写任务名称和描述
4. 选择执行频率（如每天、每周）
5. 选择「启动程序」
6. 程序/脚本：`python.exe`
7. 添加参数：`process_articles.py`
8. 起始于：项目目录路径（如 `C:\path\to\ollama-prompt-autowrite`）
9. 完成向导并启用任务

## 注意事项

1. 确保 Ollama 服务正常运行
2. 确保 qwen3.5 模型已成功拉取
3. `new` 目录中的文章格式应为 Markdown 文件
4. 脚本会自动处理 `new` 目录中的所有文件
5. 处理完成后，原文件会被移动到 `old` 目录，改写后的文章会保存到 `output` 目录

## 故障排除

### 1. 权限问题

确保当前用户对项目目录有读写权限。

### 2. Python 路径问题

确保 Python 已添加到系统环境变量中。

### 3. Ollama API 连接问题

- 确保 Ollama 服务正在运行
- 确保 qwen3.5 模型已安装
- 检查 API 地址是否正确：`http://localhost:11434/api/generate`

## 联系方式

如有问题，请联系项目维护者。
