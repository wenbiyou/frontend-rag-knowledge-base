# 前端知识库启动脚本 (Windows PowerShell)
# 同时启动后端和前端服务

$GREEN = "Green"
$BLUE = "Cyan"
$YELLOW = "Yellow"
$RED = "Red"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor $BLUE
Write-Host "║                                                              ║" -ForegroundColor $BLUE
Write-Host "║         🧠 前端知识库 - AI 问答助手                          ║" -ForegroundColor $BLUE
Write-Host "║                                                              ║" -ForegroundColor $BLUE
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor $BLUE
Write-Host ""

# 获取项目目录
$PROJECT_DIR = $PSScriptRoot

# 检查环境
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "错误: 未找到 Python" -ForegroundColor $RED
    exit 1
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "错误: 未找到 Node.js" -ForegroundColor $RED
    exit 1
}

# 启动后端
Write-Host "▶ 启动后端服务..." -ForegroundColor $YELLOW
Set-Location "$PROJECT_DIR\backend"

# 检查虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "  创建 Python 虚拟环境..." -ForegroundColor $BLUE
    python -m venv venv
}

# 激活虚拟环境
& .\venv\Scripts\Activate.ps1

# 检查依赖
$pythonCheck = python -c "import fastapi" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  安装 Python 依赖..." -ForegroundColor $BLUE
    pip install -r requirements.txt
}

# 检查环境变量
if (-not (Test-Path ".env")) {
    Write-Host "⚠ 警告: 未找到 .env 文件" -ForegroundColor $YELLOW
    Write-Host "  正在从模板创建..." -ForegroundColor $BLUE
    Copy-Item .env.example .env
    Write-Host "  请先编辑 .env 文件，填入你的 DeepSeek API Key" -ForegroundColor $RED
    Write-Host "  获取地址: https://platform.deepseek.com/" -ForegroundColor $YELLOW
    exit 1
}

# 启动后端
Write-Host "✓ 后端服务启动中..." -ForegroundColor $GREEN
$BACKEND_JOB = Start-Job -ScriptBlock {
    Set-Location $using:PROJECT_DIR\backend
    & .\venv\Scripts\python.exe main.py
}

# 等待后端启动
Start-Sleep -Seconds 3

# 启动前端
Write-Host "▶ 启动前端服务..." -ForegroundColor $YELLOW
Set-Location "$PROJECT_DIR\frontend"

# 检查依赖
if (-not (Test-Path "node_modules")) {
    Write-Host "  安装 Node.js 依赖..." -ForegroundColor $BLUE
    npm install
}

Write-Host "✓ 前端服务启动中..." -ForegroundColor $GREEN
$FRONTEND_JOB = Start-Job -ScriptBlock {
    Set-Location $using:PROJECT_DIR\frontend
    npm run dev
}

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor $GREEN
Write-Host "  服务已启动！" -ForegroundColor $GREEN
Write-Host ""
Write-Host "  前端界面: http://localhost:3000" -ForegroundColor $BLUE
Write-Host "  后端 API: http://localhost:8000" -ForegroundColor $BLUE
Write-Host "  API 文档: http://localhost:8000/docs" -ForegroundColor $BLUE
Write-Host ""
Write-Host "  按 Ctrl+C 停止所有服务" -ForegroundColor $YELLOW
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor $GREEN
Write-Host ""

# 等待用户中断
try {
    while ($true) {
        Start-Sleep -Seconds 1

        # 检查任务状态
        $backendStatus = Receive-Job -Job $BACKEND_JOB
        $frontendStatus = Receive-Job -Job $FRONTEND_JOB

        if ($backendStatus) { Write-Host "[后端] $backendStatus" }
        if ($frontendStatus) { Write-Host "[前端] $frontendStatus" }
    }
}
finally {
    Write-Host ""
    Write-Host "正在停止服务..." -ForegroundColor $YELLOW
    Stop-Job -Job $BACKEND_JOB, $FRONTEND_JOB
    Remove-Job -Job $BACKEND_JOB, $FRONTEND_JOB
    Write-Host "服务已停止" -ForegroundColor $GREEN
}
