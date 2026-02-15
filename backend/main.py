"""
FastAPI 主应用
提供 RESTful API 接口供前端调用

主要端点：
- POST /api/chat         : 对话问答（流式/非流式）
- POST /api/upload       : 上传文档
- GET  /api/sources      : 获取所有文档来源
- POST /api/sync         : 触发文档同步
- GET  /api/stats        : 获取知识库统计
- GET  /health           : 健康检查
"""
from typing import List, Optional, Dict
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import json

from config import HOST, PORT
from rag_engine import get_rag_engine, ChatSession
from sync_service import (
    OfficialDocSyncer,
    GitHubSyncer,
    DocumentImporter,
    run_full_sync
)
from database import get_vector_store
from deepseek_client import get_llm_client

# 创建 FastAPI 应用
app = FastAPI(
    title="前端知识库 API",
    description="基于 RAG 的前端开发知识库系统",
    version="1.0.0"
)

# 配置 CORS（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # 前端开发服务器地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 内存中的会话存储（生产环境应使用 Redis 等）
sessions: dict = {}

# ==================== 数据模型 ====================

class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = None
    source_filter: Optional[str] = None  # 可选过滤条件，如 "official", "github", "document"
    stream: bool = False  # 是否流式返回

class ChatResponse(BaseModel):
    """对话响应"""
    answer: str
    sources: List[dict]
    session_id: str

class SyncRequest(BaseModel):
    """同步请求"""
    source: Optional[str] = None  # "official", "github", "all"

class SyncResponse(BaseModel):
    """同步响应"""
    success: bool
    message: str
    details: Optional[dict] = None

class SourceInfo(BaseModel):
    """文档来源信息"""
    name: str
    type: str
    count: int

class StatsResponse(BaseModel):
    """统计信息"""
    total_documents: int
    sources: List[str]

# ==================== API 端点 ====================

@app.get("/health")
def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "frontend-rag-knowledge-base",
        "version": "1.0.0"
    }

@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    """获取知识库统计信息"""
    vector_store = get_vector_store()
    stats = vector_store.get_stats()
    sources = vector_store.list_sources()

    return StatsResponse(
        total_documents=stats["total_documents"],
        sources=sources
    )

@app.get("/api/sources")
def get_sources():
    """获取所有文档来源及其统计"""
    vector_store = get_vector_store()
    all_data = vector_store.collection.get()

    # 统计各来源的文档数
    source_stats = {}
    for meta in all_data.get("metadatas", []):
        if not meta:
            continue

        source = meta.get("source", "未知")
        source_type = meta.get("source_type", "document")

        key = f"{source_type}:{source}"
        if key not in source_stats:
            source_stats[key] = {
                "source": source,
                "type": source_type,
                "count": 0,
                "title": meta.get("title", "未命名")
            }
        source_stats[key]["count"] += 1

    return {
        "sources": list(source_stats.values()),
        "total": len(source_stats)
    }

@app.post("/api/chat")
def chat(request: ChatRequest):
    """
    对话问答（非流式）

    示例请求：
    {
        "message": "Vue3 的 ref 和 reactive 有什么区别？",
        "session_id": "可选，不传则创建新会话",
        "source_filter": "可选，如 'official' 只查官方文档"
    }
    """
    try:
        # 获取或创建会话
        if request.session_id and request.session_id in sessions:
            session = sessions[request.session_id]
        else:
            session = ChatSession()
            sessions[session.session_id] = session

        # 执行对话
        result = session.chat(request.message, request.source_filter)

        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            session_id=session.session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest):
    """
    对话问答（流式，打字机效果）

    返回 SSE (Server-Sent Events) 格式的流数据
    """
    def generate():
        try:
            rag_engine = get_rag_engine()

            # 先检索上下文（同步完成）
            import asyncio

            docs, metas = rag_engine._retrieve(request.message, request.source_filter)
            print('docs', docs)

            if not docs:
                yield f"data: {json.dumps({'type': 'content', 'data': '根据现有知识库，我暂时没有找到与您问题相关的信息。'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                return

            # 构建提示词
            messages = rag_engine._build_prompt(request.message, docs, metas)

            # 发送来源信息（前端可以先展示）
            sources = []
            seen = set()
            for meta in metas:
                key = f"{meta.get('source')}:{meta.get('title')}"
                if key not in seen:
                    seen.add(key)
                    sources.append({
                        "title": meta.get("title", "未命名"),
                        "source": meta.get("source", "未知")
                    })

            yield f"data: {json.dumps({'type': 'sources', 'data': sources}, ensure_ascii=False)}\n\n"

            # 流式生成回答
            for chunk in rag_engine.llm_client.chat_stream(messages):
                yield f"data: {json.dumps({'type': 'content', 'data': chunk}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.post("/api/upload")
def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    description: Optional[str] = None
):
    """
    上传文档到知识库

    支持格式：.md, .markdown, .txt, .pdf
    """
    import shutil
    from pathlib import Path

    # 检查文件格式
    allowed_extensions = {".md", ".markdown", ".txt", ".pdf"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}。支持: {', '.join(allowed_extensions)}"
        )

    # 保存上传的文件
    upload_dir = Path("./uploads")
    upload_dir.mkdir(exist_ok=True)

    file_path = upload_dir / file.filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 导入文档
        importer = DocumentImporter()
        metadata = {
            "title": title or file.filename,
            "description": description or "",
            "filename": file.filename,
            "uploaded_at": str(Path(file_path).stat().st_mtime)
        }

        result = importer.import_file(str(file_path), metadata)

        # 清理上传的临时文件
        file_path.unlink()

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "message": f"文档 '{file.filename}' 导入成功",
            "chunks": result["chunks"],
            "total_chars": result["total_chars"]
        }

    except Exception as e:
        # 清理临时文件
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync", response_model=SyncResponse)
def sync_documents(request: SyncRequest):
    """
    触发文档同步

    source 参数：
    - "official": 只同步官方文档
    - "github": 只同步 GitHub 仓库
    - "all": 全部同步（默认）
    """
    try:
        source = request.source or "all"

        if source == "official":
            syncer = OfficialDocSyncer()
            results = syncer.sync_all()
            return SyncResponse(
                success=True,
                message=f"官方文档同步完成",
                details={"results": results}
            )

        elif source == "github":
            syncer = GitHubSyncer()
            result = syncer.sync_repo_docs()
            return SyncResponse(
                success=True,
                message=f"GitHub 文档同步完成",
                details=result
            )

        elif source == "all":
            result = run_full_sync()
            return SyncResponse(
                success=True,
                message="全部文档同步完成",
                details=result
            )

        else:
            raise HTTPException(status_code=400, detail=f"未知的同步源: {source}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/session/{session_id}")
def clear_session(session_id: str):
    """清空指定会话的历史"""
    from chat_history import get_history_manager

    # 从内存中移除
    if session_id in sessions:
        session = sessions[session_id]
        session.clear_history()
        del sessions[session_id]

    # 从数据库中删除
    history_manager = get_history_manager()
    history_manager.delete_session(session_id)

    return {"success": True, "message": "会话已清除"}


# ==================== 对话历史管理 API ====================

class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: List[Dict]
    total: int


class SessionRenameRequest(BaseModel):
    """重命名会话请求"""
    title: str


@app.get("/api/sessions", response_model=SessionListResponse)
def get_sessions(limit: int = 50):
    """获取所有会话列表（按最近更新时间排序）"""
    from chat_history import get_history_manager

    history_manager = get_history_manager()
    sessions_list = history_manager.get_all_sessions(limit=limit)

    return SessionListResponse(
        sessions=sessions_list,
        total=len(sessions_list)
    )


@app.get("/api/sessions/{session_id}/messages")
def get_session_messages(session_id: str):
    """获取指定会话的所有消息"""
    from chat_history import get_history_manager

    history_manager = get_history_manager()
    messages = history_manager.get_session_messages(session_id)

    return {
        "session_id": session_id,
        "messages": messages
    }


@app.put("/api/sessions/{session_id}/rename")
def rename_session(session_id: str, request: SessionRenameRequest):
    """重命名会话"""
    from chat_history import get_history_manager

    history_manager = get_history_manager()
    success = history_manager.rename_session(session_id, request.title)

    return {
        "success": success,
        "message": "重命名成功" if success else "会话不存在"
    }


@app.get("/api/chat-stats")
def get_chat_stats():
    """获取对话统计信息"""
    from chat_history import get_history_manager

    history_manager = get_history_manager()
    stats = history_manager.get_stats()

    return stats


# ==================== 搜索建议 API ====================

# 预设的常见前端问题模板
COMMON_QUESTIONS = [
    "React hooks 有哪些？",
    "useEffect 的依赖数组怎么写？",
    "useState 和 useReducer 有什么区别？",
    "Vue3 的 Composition API 怎么用？",
    "ref 和 reactive 有什么区别？",
    "TypeScript 泛型怎么用？",
    "interface 和 type 有什么区别？",
    "Tailwind CSS 怎么自定义配置？",
    "Next.js 的 SSR 和 SSG 有什么区别？",
    "React 的 useMemo 和 useCallback 有什么区别？",
    "前端性能优化有哪些方法？",
    "CSS 的 BEM 命名规范是什么？",
    "JavaScript 的闭包是什么？",
    "Promise 和 async/await 有什么区别？",
    "Event Loop 事件循环机制是什么？",
]


@app.get("/api/suggestions")
def get_suggestions(
    query: str = Query(..., description="用户输入的查询关键字"),
    limit: int = Query(5, description="返回建议数量")
):
    """
    获取搜索建议

    基于用户输入返回相关的问题建议
    """
    if not query or len(query.strip()) < 2:
        return {"suggestions": [], "query": query}

    try:
        # 1. 从向量数据库检索相关内容
        rag_engine = get_rag_engine()
        docs, metas = rag_engine._retrieve(query, top_k=limit)

        suggestions = []
        seen = set()

        # 2. 从检索结果生成建议
        for doc, meta in zip(docs, metas):
            # 使用文档标题作为建议
            title = meta.get("title", "")
            if title and title not in seen:
                seen.add(title)
                suggestions.append({
                    "text": f"关于 {title} 的相关问题",
                    "type": "document",
                    "source": meta.get("source", "unknown")
                })

        # 3. 从预设问题中匹配
        query_lower = query.lower()
        for q in COMMON_QUESTIONS:
            if query_lower in q.lower() and q not in seen:
                seen.add(q)
                suggestions.append({
                    "text": q,
                    "type": "common"
                })
                if len(suggestions) >= limit:
                    break

        return {
            "suggestions": suggestions[:limit],
            "query": query
        }

    except Exception as e:
        # 出错时返回空建议
        return {"suggestions": [], "query": query, "error": str(e)}


# ==================== 启动入口 ====================

def main():
    """启动服务"""
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║         🧠 前端知识库 API 服务                               ║
    ║                                                              ║
    ║   访问地址: http://{HOST}:{PORT}                           ║
    ║   API 文档: http://{HOST}:{PORT}/docs                      ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True,  # 开发模式自动重载
        log_level="info"
    )

if __name__ == "__main__":
    main()
