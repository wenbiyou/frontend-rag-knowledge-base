# 前端知识库 - AI 问答助手

基于 RAG（检索增强生成）的前端开发知识库系统，支持官方文档、GitHub 仓库和本地文档的智能问答。

## 功能特点

- 🤖 **智能问答**：基于 DeepSeek AI，支持自然语言提问
- 📚 **多源知识**：整合 React、Vue、TypeScript 等官方文档
- 🔄 **自动同步**：每周自动更新官方文档，GitHub 仓库实时同步
- 📄 **文档上传**：支持 Markdown、PDF、TXT 格式
- 🔍 **来源溯源**：每个回答都标注参考来源
- 💬 **流式响应**：打字机效果，实时显示生成内容

## 项目结构

```
frontend-rag-knowledge-base/
├── README.md                 # 本文档
├── start.sh / start.ps1     # 一键启动脚本
├── backend/                 # Python 后端
│   ├── main.py             # FastAPI 主应用
│   ├── config.py           # 配置管理
│   ├── database.py         # ChromaDB 向量数据库
│   ├── document_processor.py  # 文档处理
│   ├── deepseek_client.py     # DeepSeek API 封装
│   ├── rag_engine.py       # RAG 核心引擎
│   ├── sync_service.py     # 文档同步服务
│   ├── requirements.txt    # Python 依赖
│   └── .env.example        # 环境变量模板
│
├── frontend/                # Next.js 前端
│   ├── app/                # Next.js 应用目录
│   ├── components/         # 组件
│   ├── hooks/              # 自定义 Hooks
│   ├── lib/                # 工具库
│   └── package.json
│
└── docs/                    # 📚 详细文档
    ├── README.md           # 文档总览
    ├── 01-快速上手指册.md   # 5分钟快速开始
    ├── 02-维护手册.md      # 系统维护指南
    └── 03-功能路线图.md    # 未来发展规划
```

## 📚 详细文档

- [📖 快速上手指册](./docs/01-快速上手指册.md) - 5分钟快速开始使用
- [🔧 维护手册](./docs/02-维护手册.md) - 系统维护、故障排查、配置管理
- [🚀 功能路线图](./docs/03-功能路线图.md) - 未来功能规划和发展方向

## 快速开始

### 方式一：一键启动（推荐）

配置好 API Keys 后，直接运行：

```bash
cd frontend-rag-knowledge-base
./start.sh  # Mac/Linux
# 或
.\start.ps1  # Windows
```

然后访问 http://localhost:3001 即可使用。

### 方式二：手动启动

#### 1. 配置环境

```bash
cd frontend-rag-knowledge-base
```

### 2. 配置后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 DeepSeek API Key
```

**必须配置的环境变量：**

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

获取 DeepSeek API Key：[https://platform.deepseek.com/](https://platform.deepseek.com/)

**可选配置：**
- `GITHUB_REPO` / `GITHUB_TOKEN`: 同步 GitHub 文档
- `OPENAI_API_KEY`: 如果使用 OpenAI 的 Embedding（DeepSeek 暂不支持）

### 3. 配置前端

```bash
cd ../frontend

# 安装依赖
npm install

# 开发模式启动
npm run dev
```

### 4. 启动服务

**终端 1 - 启动后端：**
```bash
cd backend
source venv/bin/activate
python main.py
# 或: uvicorn main:app --reload --port 8000
```

**终端 2 - 启动前端：**
```bash
cd frontend
npm run dev
```

### 5. 访问应用

打开浏览器访问：http://localhost:3000

## 使用指南

### 首次使用

1. 首次启动后，知识库是空的，需要先同步文档
2. 点击左侧边栏的"全部同步"按钮，等待同步完成
3. 同步完成后即可开始提问

### 日常问答

- 在输入框输入问题，按 Enter 发送
- 支持 Shift+Enter 换行
- AI 会基于知识库内容回答，并显示参考来源

### 文档管理

- **官方文档同步**：自动抓取 React、Vue、TypeScript 等官网
- **GitHub 同步**：同步指定仓库的 Markdown 文档
- **本地上传**：支持上传 Markdown、PDF、TXT 文件

### 筛选功能

点击左侧边栏的文档来源，可以只搜索特定类型的文档：
- 官方文档
- GitHub 文档
- 上传的文档

## API 文档

后端启动后，访问 http://localhost:8000/docs 查看完整的 API 文档。

主要接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 非流式对话 |
| `/api/chat/stream` | POST | 流式对话（SSE） |
| `/api/upload` | POST | 上传文档 |
| `/api/sync` | POST | 触发文档同步 |
| `/api/stats` | GET | 获取统计信息 |
| `/api/sources` | GET | 获取文档来源 |

## 技术栈

**后端：**
- Python 3.10+
- FastAPI - Web 框架
- ChromaDB - 向量数据库
- DeepSeek API - 大语言模型
- LangChain - RAG 框架

**前端：**
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Lucide Icons

## 版本历史

### v1.0 (2024-02-14) ✅
- ✅ 基础问答功能（DeepSeek + RAG）
- ✅ 官方文档自动同步（React、Vue、TypeScript、Tailwind、Next.js）
- ✅ 本地文档上传（Markdown、PDF、TXT）
- ✅ 流式响应（打字机效果）
- ✅ 来源引用和溯源
- ✅ 多种 Embedding 方案（本地/OpenAI/智谱）

查看 [功能路线图](./docs/03-功能路线图.md) 了解未来规划。

## 常见问题

**Q: DeepSeek API 如何收费？**
A: DeepSeek 按 token 计费，具体价格参考官方文档。一般 10 人团队轻度使用每月约 ¥30-50。

**Q: 可以离线使用吗？**
A: 目前需要联网调用 DeepSeek API。后续可以考虑接入本地大模型实现完全离线。

**Q: 支持哪些文档格式？**
A: 目前支持 Markdown、TXT、PDF。Word 和 Excel 可以通过导出为 PDF 后上传。

**Q: 文档同步失败怎么办？**
A: 检查网络连接，如果是 GitHub 同步失败，确认 GITHUB_TOKEN 是否有权限访问对应仓库。

## 贡献

欢迎提交 Issue 和 PR！

## 许可证

MIT License
