"""
配置管理模块
集中管理所有配置项，方便统一修改
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 配置 HuggingFace 镜像（国内访问）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 向量数据库配置
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "chroma_db"))

# 文档存储路径
DOCUMENTS_PATH = BASE_DIR / "documents"
DOCUMENTS_PATH.mkdir(exist_ok=True)

# 数据库统一配置
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATHS = {
    "core": DATA_DIR / "core.db",
    "knowledge": DATA_DIR / "knowledge.db",
    "ai": DATA_DIR / "ai.db",
    "community": DATA_DIR / "community.db",
    "sync": DATA_DIR / "sync.db",
}

CORE_DB_PATH = DB_PATHS["core"]
KNOWLEDGE_DB_PATH = DB_PATHS["knowledge"]
AI_DB_PATH = DB_PATHS["ai"]
COMMUNITY_DB_PATH = DB_PATHS["community"]
SYNC_DB_PATH = DB_PATHS["sync"]

# GitHub 配置
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# 支持多个仓库配置（逗号分隔）
# 格式：owner/repo1,owner/repo2
GITHUB_REPOS_STR = os.getenv("GITHUB_REPOS", "")
GITHUB_REPOS = [repo.strip() for repo in GITHUB_REPOS_STR.split(",") if repo.strip()]

# 向后兼容：如果配置了 GITHUB_REPO，添加到列表中
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
if GITHUB_REPO and GITHUB_REPO not in GITHUB_REPOS:
    GITHUB_REPOS.append(GITHUB_REPO)

# 官方文档源配置
# 定义支持的官方文档源及其配置
OFFICIAL_SOURCES = {
    "react": {
        "name": "React 官方文档",
        "base_url": "https://react.dev",
        "sitemap": "https://react.dev/sitemap.xml",
        "selectors": {
            "content": "article",
            "title": "h1",
            "code": "pre code"
        }
    },
    "vue": {
        "name": "Vue.js 官方文档",
        "base_url": "https://vuejs.org",
        "sitemap": "https://vuejs.org/sitemap.xml",
        "selectors": {
            "content": ".content",
            "title": "h1",
            "code": ".code-block"
        }
    },
    "typescript": {
        "name": "TypeScript 官方文档",
        "base_url": "https://www.typescriptlang.org",
        "sitemap": "https://www.typescriptlang.org/sitemap.xml",
        "selectors": {
            "content": "article",
            "title": "h1",
            "code": "pre"
        }
    },
    "tailwind": {
        "name": "Tailwind CSS 官方文档",
        "base_url": "https://tailwindcss.com",
        "sitemap": "https://tailwindcss.com/sitemap.xml",
        "selectors": {
            "content": "article",
            "title": "h1",
            "code": "pre"
        }
    },
    "nextjs": {
        "name": "Next.js 官方文档",
        "base_url": "https://nextjs.org",
        "sitemap": "https://nextjs.org/sitemap.xml",
        "selectors": {
            "content": "article",
            "title": "h1",
            "code": "pre"
        }
    },
    "python": {
        "name": "Python 官方文档",
        "base_url": "https://docs.python.org/3",
        "sitemap": "https://docs.python.org/3/sitemap.xml",
        "selectors": {
            "content": ".body",
            "title": "h1",
            "code": "pre"
        }
    },
    "nodejs": {
        "name": "Node.js 官方文档",
        "base_url": "https://nodejs.org/docs/latest/api",
        "sitemap": None,
        "selectors": {
            "content": "#apicontent",
            "title": "h1",
            "code": "pre"
        }
    }
}

# 支持的文档格式
SUPPORTED_EXTENSIONS = [".md", ".markdown", ".txt", ".pdf"]

# 文本分块配置
CHUNK_SIZE = 1000  # 每个文本块的最大字符数
CHUNK_OVERLAP = 200  # 文本块之间的重叠字符数，保证上下文连贯

# Embedding 配置
# DeepSeek 目前没有专门的 Embedding API，我们支持以下方案：
# - openai: OpenAI API（推荐，效果最好，需要 OPENAI_API_KEY）
# - zhipu: 智谱 AI（国内可选，需要 ZHIPU_API_KEY）
# - local: 本地模型（无需联网，需要安装 sentence-transformers）
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")

# Embedding 模型配置
EMBEDDING_MODELS = {
    "openai": "text-embedding-3-small",  # OpenAI 推荐模型
    "zhipu": "embedding-2",               # 智谱 Embedding 模型
    "local": "paraphrase-multilingual-MiniLM-L12-v2"  # 本地多语言模型
}

# LLM 配置
LLM_MODEL = "deepseek-chat"  # DeepSeek 的对话模型
LLM_TEMPERATURE = 0.3  # 较低的温度使回答更确定、更精确
LLM_MAX_TOKENS = 2000  # 最大回答长度

# 检索配置
TOP_K = 3  # 每次检索返回的最相关文档数量（优化：从5减少到3）
SIMILARITY_THRESHOLD = 0.1  # 相似度阈值，低于此值的结果会被过滤（本地模型建议设置较低，如0.1-0.2）

# 上下文优化配置
MAX_CONTEXT_LENGTH = 500  # 每个文档上下文最大字符数（优化：限制上下文长度）
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"  # 是否启用响应缓存
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))  # 缓存过期时间（秒），默认1小时

# 服务配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
