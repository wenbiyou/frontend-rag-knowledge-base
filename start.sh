#!/bin/bash

# 前端知识库启动脚本
# 同时启动后端和前端服务

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║         🧠 前端知识库 - AI 问答助手                          ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 获取项目目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 检查环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 Python3${NC}"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: 未找到 Node.js${NC}"
    exit 1
fi

# 启动后端
echo -e "${YELLOW}▶ 启动后端服务...${NC}"
cd "$PROJECT_DIR/backend"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${BLUE}  创建 Python 虚拟环境...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 检查依赖
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${BLUE}  安装 Python 依赖...${NC}"
    pip install -r requirements.txt
fi

# 检查环境变量
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ 警告: 未找到 .env 文件${NC}"
    echo -e "${BLUE}  正在从模板创建...${NC}"
    cp .env.example .env
    echo -e "${RED}  请先编辑 .env 文件，填入你的 DeepSeek API Key${NC}"
    echo -e "${YELLOW}  获取地址: https://platform.deepseek.com/${NC}"
    exit 1
fi

# 检查 API Key
if ! grep -q "DEEPSEEK_API_KEY=sk-" .env; then
    echo -e "${RED}⚠ 警告: 请在 .env 文件中配置有效的 DEEPSEEK_API_KEY${NC}"
    exit 1
fi

# 启动后端（后台运行）
echo -e "${GREEN}✓ 后端服务启动中...${NC}"
python main.py &
BACKEND_PID=$!

# 等待后端启动
sleep 2

# 启动前端
echo -e "${YELLOW}▶ 启动前端服务...${NC}"
cd "$PROJECT_DIR/frontend"

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}  安装 Node.js 依赖...${NC}"
    npm install
fi

echo -e "${GREEN}✓ 前端服务启动中...${NC}"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  服务已启动！${NC}"
echo ""
echo -e "  ${BLUE}前端界面:${NC} http://localhost:3000"
echo -e "  ${BLUE}后端 API:${NC} http://localhost:8000"
echo -e "  ${BLUE}API 文档:${NC} http://localhost:8000/docs"
echo ""
echo -e "  ${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo ""

# 捕获中断信号
trap "echo ''; echo -e '${YELLOW}正在停止服务...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

# 等待
wait
