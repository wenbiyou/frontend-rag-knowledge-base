# 前端知识库 - AI 问答助手

基于 RAG（检索增强生成）的前端开发知识库系统，支持官方文档、GitHub 仓库和本地文档的智能问答。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           前端层 (Next.js 14)                            │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ 首页问答  │  │ 管理后台  │  │ 登录认证  │  │ 主题切换  │  │ 会话管理  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          API 网关层 (FastAPI)                            │
├─────────────────────────────────────────────────────────────────────────┤
│  认证 API │ 对话 API │ 文档 API │ 同步 API │ 管理 API │ 开放 API        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           服务层 (Business Logic)                        │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ RAG Engine  │  │ AI Mentor   │  │ Sync Service│  │ Analytics   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Code Analyzer│ │ Knowledge   │  │ Recommend   │  │ Community   │    │
│  │             │  │ Graph       │  │ Engine      │  │ Manager     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           数据层 (Data Layer)                            │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ ChromaDB    │  │ SQLite      │  │ DeepSeek    │  │ GitHub API  │    │
│  │ (向量存储)   │  │ (关系数据)   │  │ (LLM)       │  │ (仓库同步)   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

## 功能特点

- 🤖 **智能问答**：基于 DeepSeek AI，支持自然语言提问
- 📚 **多源知识**：整合 React、Vue、TypeScript、Python、Node.js 等官方文档
- 🔄 **自动同步**：每周自动更新官方文档，GitHub 仓库实时同步
- 📄 **文档上传**：支持 Markdown、PDF、TXT 格式
- 🔍 **来源溯源**：每个回答都标注参考来源
- 💬 **流式响应**：打字机效果，实时显示生成内容
- 👥 **多用户支持**：用户认证、权限管理、数据隔离
- 📊 **数据分析**：使用统计、热门问题、知识覆盖率
- 🧠 **AI 导师**：学习计划、技能评估、成长记录
- 🔗 **知识图谱**：技术关联可视化、学习路径推荐

## 项目结构

```
frontend-rag-knowledge-base/
├── README.md                 # 本文档
├── start.sh / start.ps1     # 一键启动脚本
│
├── backend/                 # Python 后端
│   ├── main.py             # FastAPI 主应用入口
│   ├── config.py           # 配置管理
│   │
│   ├── core/               # 核心模块
│   │   ├── __init__.py
│   │   ├── database.py         # ChromaDB 向量数据库
│   │   ├── document_processor.py  # 文档处理
│   │   ├── rag_engine.py       # RAG 核心引擎
│   │   └── rag_optimizer.py    # RAG 优化器
│   │
│   ├── ai/                 # AI 模块
│   │   ├── __init__.py
│   │   ├── deepseek_client.py  # DeepSeek API 封装
│   │   ├── ai_mentor.py        # AI 导师系统
│   │   ├── recommendation.py   # 智能推荐引擎
│   │   └── knowledge_graph.py  # 知识图谱
│   │
│   ├── sync/               # 同步模块
│   │   ├── __init__.py
│   │   ├── sync_service.py     # 文档同步服务
│   │   └── sync_cloud.py       # 云端同步
│   │
│   ├── admin/              # 管理模块
│   │   ├── __init__.py
│   │   ├── auth.py             # 用户认证
│   │   ├── api_keys.py         # API Key 管理
│   │   ├── chat_history.py     # 对话历史
│   │   ├── document_manager.py # 文档管理
│   │   ├── analytics.py        # 统计分析
│   │   ├── feedback.py         # 反馈系统
│   │   ├── github_db.py        # GitHub 仓库管理
│   │   └── code_analyzer.py    # 代码分析
│   │
│   ├── community/          # 社区模块
│   │   ├── __init__.py
│   │   └── community.py        # 社区贡献管理
│   │
│   ├── requirements.txt    # Python 依赖
│   └── .env.example        # 环境变量模板
│
├── frontend/                # Next.js 前端
│   ├── app/                # Next.js 应用目录
│   │   ├── page.tsx       # 首页（问答界面）
│   │   ├── layout.tsx     # 根布局
│   │   ├── login/         # 登录页面
│   │   └── admin/         # 管理后台
│   │       ├── analytics/  # 数据分析
│   │       ├── api-keys/   # API Key 管理
│   │       ├── documents/  # 文档管理
│   │       └── sync/       # 同步管理
│   ├── components/         # 组件
│   │   ├── AdminLayout.tsx
│   │   ├── ChatInput.tsx
│   │   ├── MessageList.tsx
│   │   ├── Sidebar.tsx
│   │   ├── ThemeProvider.tsx
│   │   └── ...
│   ├── hooks/              # 自定义 Hooks
│   │   └── useChat.ts
│   ├── contexts/           # React Context
│   │   └── AuthContext.tsx
│   ├── lib/                # 工具库
│   │   └── api/            # API 客户端模块
│   │       ├── index.ts        # 统一导出
│   │       ├── types.ts        # 类型定义
│   │       ├── config.ts       # 配置和认证
│   │       ├── chat.ts         # 对话相关 API
│   │       ├── documents.ts    # 文档相关 API
│   │       ├── sync.ts         # 同步相关 API
│   │       └── analytics.ts    # 统计分析 API
│   └── package.json
│
├── docs/                    # 详细文档
│   ├── README.md           # 文档总览
│   ├── 01-快速上手指册.md   # 5分钟快速开始
│   ├── 02-维护手册.md      # 系统维护指南
│   ├── 03-功能路线图.md    # 未来发展规划
│   ├── 04-测试报告.md      # 测试报告
│   └── 05-UI优化报告.md    # UI 优化报告
│
└── prompt/                  # Prompt 模板
    ├── prompt.cto.md       # CTO 角色提示词
    ├── prompt.test.md      # 测试提示词
    └── prompt.ui.md        # UI 设计提示词
```

## 后端模块说明

### 核心模块 (core/)
| 模块 | 文件 | 职责 |
|------|------|------|
| 配置管理 | config.py | 环境变量、系统配置 |
| 向量数据库 | core/database.py | ChromaDB 封装、向量存储 |
| 文档处理 | core/document_processor.py | 文档分块、向量化 |
| RAG 引擎 | core/rag_engine.py | 检索增强生成核心逻辑 |
| RAG 优化 | core/rag_optimizer.py | 查询优化、重排序 |

### AI 模块 (ai/)
| 模块 | 文件 | 职责 |
|------|------|------|
| LLM 客户端 | ai/deepseek_client.py | DeepSeek API 封装 |
| AI 导师 | ai/ai_mentor.py | 学习计划、技能评估 |
| 推荐引擎 | ai/recommendation.py | 个性化推荐 |
| 知识图谱 | ai/knowledge_graph.py | 技术关联、学习路径 |

### 同步模块 (sync/)
| 模块 | 文件 | 职责 |
|------|------|------|
| 文档同步 | sync/sync_service.py | 官方文档、GitHub 同步 |
| 云端同步 | sync/sync_cloud.py | 数据导出/导入 |

### 管理模块 (admin/)
| 模块 | 文件 | 职责 |
|------|------|------|
| 用户认证 | admin/auth.py | 登录、注册、权限 |
| API Key | admin/api_keys.py | API Key 生成、验证 |
| 对话历史 | admin/chat_history.py | 会话持久化 |
| 文档管理 | admin/document_manager.py | 文档 CRUD |
| 统计分析 | admin/analytics.py | 使用统计 |
| 反馈系统 | admin/feedback.py | 点赞、错误标记 |
| GitHub 管理 | admin/github_db.py | 仓库配置、Webhook |
| 代码分析 | admin/code_analyzer.py | 代码文件分析 |

### 社区模块 (community/)
| 模块 | 文件 | 职责 |
|------|------|------|
| 社区管理 | community/community.py | 提示词分享、配置分享、最佳实践 |

## API 端点分类

### 认证 API
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/me` | GET | 获取当前用户 |
| `/api/auth/change-password` | POST | 修改密码 |

### 对话 API
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 非流式对话 |
| `/api/chat/stream` | POST | 流式对话（SSE） |
| `/api/sessions` | GET | 获取会话列表 |
| `/api/sessions/{id}/messages` | GET | 获取会话消息 |
| `/api/suggestions` | GET | 搜索建议 |

### 文档 API
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/documents` | GET | 文档列表（分页） |
| `/api/documents/{source}` | GET | 文档详情 |
| `/api/documents/{source}` | DELETE | 删除文档 |
| `/api/upload` | POST | 上传文档 |

### 同步 API
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/sync` | POST | 触发文档同步 |
| `/api/sync/status` | GET | 同步状态 |
| `/api/repos` | GET | 仓库列表 |
| `/api/repos` | POST | 添加仓库 |
| `/api/webhook/github` | POST | GitHub Webhook |

### 管理 API
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/stats` | GET | 知识库统计 |
| `/api/sources` | GET | 文档来源列表 |
| `/api/keys` | GET/POST | API Key 管理 |
| `/api/analytics/*` | GET | 统计分析 |

### AI 功能 API
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/rag/optimize` | POST | 查询优化 |
| `/api/rag/enhanced-search` | POST | 增强搜索 |
| `/api/mentor/*` | * | AI 导师功能 |
| `/api/graph/*` | * | 知识图谱 |
| `/api/recommendations/*` | * | 智能推荐 |
| `/api/code/*` | * | 代码分析 |

### 社区 API
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/community/prompts` | GET/POST | 提示词分享 |
| `/api/community/configs` | GET/POST | 配置分享 |
| `/api/community/practices` | GET/POST | 最佳实践 |
| `/api/community/like` | POST | 点赞 |

## 技术栈

### 后端
- **Python 3.10+**
- **FastAPI** - Web 框架
- **ChromaDB** - 向量数据库
- **DeepSeek API** - 大语言模型
- **LangChain** - RAG 框架
- **SQLite** - 关系数据存储

### 前端
- **Next.js 14** - React 框架
- **React 18** - UI 库
- **TypeScript** - 类型安全
- **Tailwind CSS** - 样式框架
- **Lucide Icons** - 图标库

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

#### 1. 配置后端

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

获取 DeepSeek API Key：https://platform.deepseek.com/

#### 2. 配置前端

```bash
cd ../frontend

# 安装依赖
npm install

# 开发模式启动
npm run dev
```

#### 3. 启动服务

**终端 1 - 启动后端：**

```bash
cd backend
source venv/bin/activate
python main.py
```

**终端 2 - 启动前端：**

```bash
cd frontend
npm run dev
```

#### 4. 访问应用

- 前端界面：http://localhost:3001
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 开发指南

### 后端开发规范

1. **模块职责单一**：每个 Python 文件负责一个明确的功能领域
2. **依赖注入**：使用 `get_xxx()` 函数获取单例实例
3. **错误处理**：返回 `{"error": "message"}` 或抛出 HTTPException
4. **类型注解**：使用 Pydantic 模型定义请求/响应结构

### 前端开发规范

1. **组件化**：可复用组件放在 `components/` 目录
2. **类型安全**：所有组件使用 TypeScript
3. **样式规范**：使用 Tailwind CSS 原子类
4. **API 调用**：统一通过 `lib/api.ts` 封装

### Git 提交规范

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
refactor: 代码重构
test: 测试相关
chore: 构建/工具相关
```

## 详细文档

- [快速上手指册](./docs/01-快速上手指册.md) - 5分钟快速开始使用
- [维护手册](./docs/02-维护手册.md) - 系统维护、故障排查、配置管理
- [功能路线图](./docs/03-功能路线图.md) - 未来功能规划和发展方向

## 版本历史

### v2.0 ✅

- ✅ 多用户支持（登录/权限管理）
- ✅ 云端同步
- ✅ API 开放平台
- ✅ RAG 优化（重排序、意图识别）
- ✅ 代码分析
- ✅ AI 导师系统
- ✅ 知识图谱
- ✅ 智能推荐
- ✅ 社区贡献

### v1.0 ✅

- ✅ 基础问答功能（DeepSeek + RAG）
- ✅ 官方文档自动同步
- ✅ 本地文档上传
- ✅ 流式响应
- ✅ 来源引用

查看 [功能路线图](./docs/03-功能路线图.md) 了解未来规划。

## 常见问题

**Q: DeepSeek API 如何收费？**
A: DeepSeek 按 token 计费，具体价格参考官方文档。一般 10 人团队轻度使用每月约 ¥30-50。

**Q: 可以离线使用吗？**
A: 目前需要联网调用 DeepSeek API。后续可以考虑接入本地大模型实现完全离线。

**Q: 支持哪些文档格式？**
A: 目前支持 Markdown、TXT、PDF、ZIP（批量导入）。

**Q: 文档同步失败怎么办？**
A: 检查网络连接，如果是 GitHub 同步失败，确认 GITHUB_TOKEN 是否有权限访问对应仓库。

## 贡献

欢迎提交 Issue 和 PR！

## 许可证

MIT License
