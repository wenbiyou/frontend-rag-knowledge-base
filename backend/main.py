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
- POST /api/webhook/github : GitHub Webhook 端点
- GET  /api/repos        : 仓库管理 API
"""
from typing import List, Optional, Dict
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import json
import hmac
import hashlib
from datetime import datetime

from config import HOST, PORT, GITHUB_WEBHOOK_SECRET, GITHUB_REPOS
from rag_engine import get_rag_engine, ChatSession
from sync_service import (
    OfficialDocSyncer,
    GitHubSyncer,
    DocumentImporter,
    run_full_sync
)
from database import get_vector_store
from deepseek_client import get_llm_client
import github_db

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


# ==================== GitHub Webhook 和仓库管理 API ====================

class RepoAddRequest(BaseModel):
    """添加仓库请求"""
    repo_name: str
    auto_sync: bool = True


class RepoUpdateRequest(BaseModel):
    """更新仓库请求"""
    enabled: Optional[bool] = None
    auto_sync: Optional[bool] = None


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """验证 GitHub Webhook 签名"""
    if not GITHUB_WEBHOOK_SECRET:
        return True

    expected_signature = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected_signature}", signature)


def sync_repo_background(repo_name: str, triggered_by: str = "webhook"):
    """后台同步仓库"""
    try:
        syncer = GitHubSyncer(repo=repo_name)
        result = syncer.sync_repo_docs()

        if "error" in result:
            github_db.update_repo(
                repo_name,
                last_sync_status="failed"
            )
        else:
            github_db.update_repo(
                repo_name,
                last_sync_status="success",
                last_sync_at=datetime.now().isoformat()
            )

    except Exception as e:
        print(f"后台同步失败: {repo_name} - {e}")
        github_db.update_repo(
            repo_name,
            last_sync_status="failed"
        )


@app.post("/api/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    GitHub Webhook 端点
    
    支持 Push 和 Pull Request 事件
    """
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_webhook_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    payload_json = json.loads(payload)

    repo_full_name = payload_json.get("repository", {}).get("full_name", "")

    if not repo_full_name:
        return {"status": "ignored", "reason": "No repository info"}

    event = github_db.add_webhook_event(
        repo_name=repo_full_name,
        event_type=event_type,
        action=payload_json.get("action", ""),
        payload=payload_json
    )

    if event_type == "push":
        repo = github_db.get_repo(repo_full_name)
        if repo and repo.get("auto_sync"):
            background_tasks.add_task(
                sync_repo_background,
                repo_full_name,
                "push"
            )
            github_db.mark_webhook_processed(event["id"])
            return {"status": "accepted", "action": "sync_triggered"}

    elif event_type == "pull_request":
        action = payload_json.get("action", "")
        pr = payload_json.get("pull_request", {})
        merged = pr.get("merged", False)

        if action == "closed" and merged:
            repo = github_db.get_repo(repo_full_name)
            if repo and repo.get("auto_sync"):
                background_tasks.add_task(
                    sync_repo_background,
                    repo_full_name,
                    "pr_merge"
                )
                github_db.mark_webhook_processed(event["id"])
                return {"status": "accepted", "action": "sync_triggered"}

    return {"status": "accepted", "action": "no_action"}


@app.get("/api/repos")
def get_repos():
    """获取所有配置的仓库列表"""
    repos = github_db.get_all_repos()

    for repo in repos:
        if repo["repo_name"] not in GITHUB_REPOS:
            repo["from_env"] = False
        else:
            repo["from_env"] = True

    return {
        "repos": repos,
        "env_repos": GITHUB_REPOS,
        "total": len(repos)
    }


@app.post("/api/repos")
def add_repo(request: RepoAddRequest):
    """添加新仓库"""
    result = github_db.add_repo(
        request.repo_name,
        auto_sync=request.auto_sync
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "success": True,
        "message": f"仓库 {request.repo_name} 添加成功",
        "repo": result
    }


@app.get("/api/repos/{repo_name}")
def get_repo_detail(repo_name: str):
    """获取仓库详情"""
    repo = github_db.get_repo(repo_name)

    if not repo:
        raise HTTPException(status_code=404, detail="仓库不存在")

    history = github_db.get_sync_history(repo_name, limit=10)

    return {
        "repo": repo,
        "sync_history": history
    }


@app.put("/api/repos/{repo_name}")
def update_repo_config(repo_name: str, request: RepoUpdateRequest):
    """更新仓库配置"""
    updates = {}
    if request.enabled is not None:
        updates["enabled"] = request.enabled
    if request.auto_sync is not None:
        updates["auto_sync"] = request.auto_sync

    if not updates:
        raise HTTPException(status_code=400, detail="没有要更新的内容")

    success = github_db.update_repo(repo_name, **updates)

    if not success:
        raise HTTPException(status_code=404, detail="仓库不存在")

    return {
        "success": True,
        "message": "更新成功"
    }


@app.delete("/api/repos/{repo_name}")
def delete_repo_config(repo_name: str):
    """删除仓库配置"""
    if repo_name in GITHUB_REPOS:
        raise HTTPException(
            status_code=400,
            detail="无法删除环境变量配置的仓库"
        )

    success = github_db.delete_repo(repo_name)

    if not success:
        raise HTTPException(status_code=404, detail="仓库不存在")

    return {
        "success": True,
        "message": f"仓库 {repo_name} 已删除"
    }


@app.post("/api/repos/{repo_name}/sync")
def trigger_repo_sync(repo_name: str, background_tasks: BackgroundTasks):
    """手动触发仓库同步"""
    repo = github_db.get_repo(repo_name)

    if not repo:
        raise HTTPException(status_code=404, detail="仓库不存在")

    if not repo.get("enabled"):
        raise HTTPException(status_code=400, detail="仓库已禁用")

    background_tasks.add_task(
        sync_repo_background,
        repo_name,
        "manual"
    )

    return {
        "success": True,
        "message": f"仓库 {repo_name} 同步已触发"
    }


@app.get("/api/repos/{repo_name}/history")
def get_repo_sync_history(repo_name: str, limit: int = 50):
    """获取仓库同步历史"""
    history = github_db.get_sync_history(repo_name, limit=limit)

    return {
        "repo_name": repo_name,
        "history": history,
        "total": len(history)
    }


# ==================== 文档管理 API ====================

class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: List[Dict]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentStatsResponse(BaseModel):
    """文档统计响应"""
    total_documents: int
    total_chunks: int
    total_chars: int
    by_type: Dict[str, int]


@app.get("/api/documents", response_model=DocumentListResponse)
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    """
    获取文档列表（分页）

    参数：
    - page: 页码
    - page_size: 每页数量
    - source_type: 来源类型筛选 (document/github/official)
    - status: 状态筛选 (active/deleted)
    - search: 搜索关键词
    """
    from document_manager import get_document_manager

    manager = get_document_manager()
    result = manager.list_documents(
        page=page,
        page_size=page_size,
        source_type=source_type,
        status=status,
        search=search
    )

    return DocumentListResponse(**result)


@app.get("/api/documents/stats", response_model=DocumentStatsResponse)
def get_document_stats():
    """获取文档统计信息"""
    from document_manager import get_document_manager

    manager = get_document_manager()
    stats = manager.get_stats()

    return DocumentStatsResponse(**stats)


@app.get("/api/documents/{source:path}")
def get_document_detail(source: str):
    """获取单个文档详情"""
    from document_manager import get_document_manager

    manager = get_document_manager()
    doc = manager.get_document(source)

    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    return doc


@app.delete("/api/documents/{source:path}")
def delete_document(source: str):
    """
    删除文档

    同时从向量数据库和文档管理数据库中删除
    """
    from document_manager import get_document_manager
    from database import get_vector_store

    manager = get_document_manager()
    vector_store = get_vector_store()

    doc = manager.get_document(source)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    vector_store.delete_by_source(source)
    manager.delete_document(source)

    return {
        "success": True,
        "message": f"文档 '{source}' 已删除"
    }


@app.post("/api/documents/sync")
def sync_documents_from_vector_store():
    """从向量数据库同步文档信息到管理数据库"""
    from document_manager import get_document_manager
    from database import get_vector_store

    manager = get_document_manager()
    vector_store = get_vector_store()

    count = manager.sync_from_vector_store(vector_store)

    return {
        "success": True,
        "message": f"已同步 {count} 个文档",
        "count": count
    }


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
