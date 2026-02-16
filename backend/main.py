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
- POST /api/auth/register : 用户注册
- POST /api/auth/login   : 用户登录
- GET  /api/auth/me      : 获取当前用户
"""
from typing import List, Optional, Dict
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request, BackgroundTasks, Depends
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

app = FastAPI(
    title="前端知识库 API",
    description="基于 RAG 的前端开发知识库系统",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# ==================== 认证相关模型 ====================

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    email: Optional[str]
    role: str
    created_at: str


class LoginResponse(BaseModel):
    """登录响应"""
    user: UserResponse
    token: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str


# ==================== 认证依赖 ====================

def get_current_user_optional(request: Request) -> Optional[Dict]:
    """获取当前用户（可选）"""
    from auth import get_current_user
    try:
        authorization = request.headers.get("Authorization")
        return get_current_user(authorization)
    except Exception:
        return None


def get_current_user_required(request: Request) -> Dict:
    """获取当前用户（必须登录）"""
    from auth import get_current_user
    authorization = request.headers.get("Authorization")
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或 Token 已过期")
    return user


# ==================== API 端点 ====================

@app.get("/health")
def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "frontend-rag-knowledge-base",
        "version": "2.0.0"
    }


# ==================== 认证 API ====================

@app.post("/api/auth/register", response_model=UserResponse)
def register(request: RegisterRequest):
    """用户注册"""
    from auth import get_user_manager

    if len(request.username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少 3 个字符")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 个字符")

    manager = get_user_manager()
    result = manager.create_user(
        username=request.username,
        password=request.password,
        email=request.email
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return UserResponse(**result)


@app.post("/api/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """用户登录"""
    from auth import get_user_manager, create_token

    manager = get_user_manager()
    user = manager.authenticate(request.username, request.password)

    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_token(user["id"], user["username"], user["role"])

    return LoginResponse(
        user=UserResponse(**user),
        token=token
    )


@app.get("/api/auth/me", response_model=UserResponse)
def get_me(user: Dict = Depends(get_current_user_required)):
    """获取当前用户信息"""
    return UserResponse(**user)


@app.post("/api/auth/change-password")
def change_password(
    request: ChangePasswordRequest,
    user: Dict = Depends(get_current_user_required)
):
    """修改密码"""
    from auth import get_user_manager

    manager = get_user_manager()
    result = manager.change_password(
        user_id=user["id"],
        old_password=request.old_password,
        new_password=request.new_password
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.get("/api/auth/users")
def list_users(user: Dict = Depends(get_current_user_required)):
    """获取用户列表（仅管理员）"""
    from auth import get_user_manager

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="无权限")

    manager = get_user_manager()
    return {"users": manager.list_users()}


@app.delete("/api/auth/users/{user_id}")
def delete_user(
    user_id: int,
    user: Dict = Depends(get_current_user_required)
):
    """删除用户（仅管理员）"""
    from auth import get_user_manager

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="无权限")

    manager = get_user_manager()
    success = manager.delete_user(user_id)

    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {"success": True, "message": "用户已删除"}

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
    import time
    from analytics import get_analytics_manager

    start_time = time.time()

    try:
        if request.session_id and request.session_id in sessions:
            session = sessions[request.session_id]
        else:
            session = ChatSession()
            sessions[session.session_id] = session

        result = session.chat(request.message, request.source_filter)

        response_time_ms = int((time.time() - start_time) * 1000)

        analytics = get_analytics_manager()
        analytics.log_question(
            question=request.message,
            session_id=session.session_id,
            source_filter=request.source_filter,
            has_answer=len(result.get("sources", [])) > 0,
            response_time_ms=response_time_ms
        )

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
    import time
    from analytics import get_analytics_manager

    start_time = time.time()
    sources_found = []

    def generate():
        nonlocal sources_found
        try:
            rag_engine = get_rag_engine()

            docs, metas = rag_engine._retrieve(request.message, request.source_filter)
            print('docs', docs)

            if not docs:
                yield f"data: {json.dumps({'type': 'content', 'data': '根据现有知识库，我暂时没有找到与您问题相关的信息。'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

                analytics = get_analytics_manager()
                response_time_ms = int((time.time() - start_time) * 1000)
                analytics.log_question(
                    question=request.message,
                    session_id=request.session_id,
                    source_filter=request.source_filter,
                    has_answer=False,
                    response_time_ms=response_time_ms
                )
                return

            messages = rag_engine._build_prompt(request.message, docs, metas)

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

            sources_found = sources
            yield f"data: {json.dumps({'type': 'sources', 'data': sources}, ensure_ascii=False)}\n\n"

            for chunk in rag_engine.llm_client.chat_stream(messages):
                yield f"data: {json.dumps({'type': 'content', 'data': chunk}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

            analytics = get_analytics_manager()
            response_time_ms = int((time.time() - start_time) * 1000)
            analytics.log_question(
                question=request.message,
                session_id=request.session_id,
                source_filter=request.source_filter,
                has_answer=len(sources_found) > 0,
                response_time_ms=response_time_ms
            )

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

    支持格式：.md, .markdown, .txt, .pdf, .zip
    ZIP 文件会自动解压并批量导入
    """
    import shutil
    import zipfile
    import tempfile
    from pathlib import Path

    allowed_extensions = {".md", ".markdown", ".txt", ".pdf", ".zip"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}。支持: {', '.join(allowed_extensions)}"
        )

    upload_dir = Path("./uploads")
    upload_dir.mkdir(exist_ok=True)

    file_path = upload_dir / file.filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if file_ext == ".zip":
            results = []
            total_chunks = 0
            total_chars = 0
            errors = []

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)

                doc_extensions = {".md", ".markdown", ".txt", ".pdf"}
                doc_files = []
                for ext in doc_extensions:
                    doc_files.extend(temp_path.rglob(f"*{ext}"))

                importer = DocumentImporter()

                for doc_file in doc_files:
                    try:
                        relative_path = doc_file.relative_to(temp_path)
                        metadata = {
                            "title": doc_file.stem,
                            "filename": str(relative_path),
                            "source": f"zip:{file.filename}:{relative_path}",
                            "uploaded_at": str(doc_file.stat().st_mtime)
                        }

                        result = importer.import_file(str(doc_file), metadata)

                        if "error" in result:
                            errors.append({
                                "file": str(relative_path),
                                "error": result["error"]
                            })
                        else:
                            results.append({
                                "file": str(relative_path),
                                "chunks": result["chunks"],
                                "chars": result["total_chars"]
                            })
                            total_chunks += result["chunks"]
                            total_chars += result["total_chars"]

                    except Exception as e:
                        errors.append({
                            "file": str(relative_path),
                            "error": str(e)
                        })

            file_path.unlink()

            return {
                "success": True,
                "message": f"批量导入完成：{len(results)} 个文件成功，{len(errors)} 个失败",
                "total_files": len(doc_files),
                "success_count": len(results),
                "error_count": len(errors),
                "total_chunks": total_chunks,
                "total_chars": total_chars,
                "results": results,
                "errors": errors
            }

        else:
            importer = DocumentImporter()
            metadata = {
                "title": title or file.filename,
                "description": description or "",
                "filename": file.filename,
                "uploaded_at": str(Path(file_path).stat().st_mtime)
            }

            result = importer.import_file(str(file_path), metadata)

            file_path.unlink()

            if "error" in result:
                raise HTTPException(status_code=500, detail=result["error"])

            return {
                "success": True,
                "message": f"文档 '{file.filename}' 导入成功",
                "chunks": result["chunks"],
                "total_chars": result["total_chars"]
            }

    except HTTPException:
        raise
    except Exception as e:
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
def clear_session(
    session_id: str,
    user: Optional[Dict] = Depends(get_current_user_optional)
):
    """清空指定会话的历史"""
    from chat_history import get_history_manager

    if session_id in sessions:
        session = sessions[session_id]
        session.clear_history()
        del sessions[session_id]

    history_manager = get_history_manager()
    user_id = user["id"] if user else None
    success = history_manager.delete_session(session_id, user_id=user_id)

    if not success:
        raise HTTPException(status_code=404, detail="会话不存在或无权限")

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
def get_sessions(
    limit: int = 50,
    user: Optional[Dict] = Depends(get_current_user_optional)
):
    """获取会话列表（按最近更新时间排序，支持用户隔离）"""
    from chat_history import get_history_manager

    history_manager = get_history_manager()
    user_id = user["id"] if user else None
    sessions_list = history_manager.get_all_sessions(limit=limit, user_id=user_id)

    return SessionListResponse(
        sessions=sessions_list,
        total=len(sessions_list)
    )


@app.get("/api/sessions/{session_id}/messages")
def get_session_messages(
    session_id: str,
    user: Optional[Dict] = Depends(get_current_user_optional)
):
    """获取指定会话的所有消息"""
    from chat_history import get_history_manager

    history_manager = get_history_manager()
    messages = history_manager.get_session_messages(session_id)

    return {
        "session_id": session_id,
        "messages": messages
    }


@app.put("/api/sessions/{session_id}/rename")
def rename_session(
    session_id: str,
    request: SessionRenameRequest,
    user: Optional[Dict] = Depends(get_current_user_optional)
):
    """重命名会话"""
    from chat_history import get_history_manager

    history_manager = get_history_manager()
    user_id = user["id"] if user else None
    success = history_manager.rename_session(session_id, request.title, user_id=user_id)

    return {
        "success": success,
        "message": "重命名成功" if success else "会话不存在或无权限"
    }


@app.get("/api/chat-stats")
def get_chat_stats(user: Optional[Dict] = Depends(get_current_user_optional)):
    """获取对话统计信息"""
    from chat_history import get_history_manager

    history_manager = get_history_manager()
    user_id = user["id"] if user else None
    stats = history_manager.get_stats(user_id=user_id)

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


# ==================== 云端同步 API ====================

class SyncConfigRequest(BaseModel):
    """同步配置请求"""
    provider: Optional[str] = None
    endpoint: Optional[str] = None
    credentials: Optional[Dict] = None
    auto_sync: bool = False


class ImportDataRequest(BaseModel):
    """导入数据请求"""
    data: Dict


@app.get("/api/sync/config")
def get_sync_config(user: Dict = Depends(get_current_user_required)):
    """获取同步配置"""
    from sync_cloud import get_sync_manager

    manager = get_sync_manager()
    config = manager.get_config(user["id"])

    return {"config": config}


@app.post("/api/sync/config")
def set_sync_config(
    request: SyncConfigRequest,
    user: Dict = Depends(get_current_user_required)
):
    """设置同步配置"""
    from sync_cloud import get_sync_manager

    manager = get_sync_manager()
    result = manager.set_config(
        user_id=user["id"],
        provider=request.provider,
        endpoint=request.endpoint,
        credentials=request.credentials,
        auto_sync=request.auto_sync
    )

    return result


@app.post("/api/sync/export")
def export_user_data(user: Dict = Depends(get_current_user_required)):
    """导出用户数据"""
    from sync_cloud import get_sync_manager

    manager = get_sync_manager()
    result = manager.export_data(user["id"])

    return result


@app.post("/api/sync/import")
def import_user_data(
    request: ImportDataRequest,
    user: Dict = Depends(get_current_user_required)
):
    """导入用户数据"""
    from sync_cloud import get_sync_manager

    manager = get_sync_manager()
    result = manager.import_data(user["id"], request.data)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.get("/api/sync/history")
def get_sync_history(
    limit: int = Query(20, ge=1, le=100),
    user: Dict = Depends(get_current_user_required)
):
    """获取同步历史"""
    from sync_cloud import get_sync_manager

    manager = get_sync_manager()
    history = manager.get_sync_history(user["id"], limit=limit)

    return {"history": history}


@app.get("/api/sync/exports")
def list_export_files(user: Dict = Depends(get_current_user_required)):
    """列出导出文件"""
    from sync_cloud import get_sync_manager

    manager = get_sync_manager()
    exports = manager.list_exports(user_id=user["id"])

    return {"exports": exports}


@app.get("/api/sync/download/{filename}")
def download_export_file(filename: str):
    """下载导出文件"""
    from sync_cloud import get_sync_manager
    from fastapi.responses import FileResponse

    manager = get_sync_manager()
    filepath = manager.get_export_file(filename)

    if not filepath:
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/json"
    )


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


# ==================== 统计分析 API ====================

class AnalyticsOverviewResponse(BaseModel):
    """统计总览响应"""
    total_questions: int
    unique_sessions: int
    active_days: int
    avg_response_time_ms: int
    today_questions: int
    week_questions: int


@app.get("/api/analytics/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview():
    """获取统计总览"""
    from analytics import get_analytics_manager

    manager = get_analytics_manager()
    stats = manager.get_overview()

    return AnalyticsOverviewResponse(**stats)


@app.get("/api/analytics/daily")
def get_analytics_daily(days: int = Query(30, ge=1, le=365)):
    """获取每日统计趋势"""
    from analytics import get_analytics_manager

    manager = get_analytics_manager()
    stats = manager.get_daily_stats(days=days)

    return {"days": days, "data": stats}


@app.get("/api/analytics/popular")
def get_analytics_popular(limit: int = Query(20, ge=1, le=100)):
    """获取热门问题排行"""
    from analytics import get_analytics_manager

    manager = get_analytics_manager()
    questions = manager.get_popular_questions(limit=limit)

    return {"questions": questions}


@app.get("/api/analytics/sources")
def get_analytics_sources():
    """获取来源使用统计"""
    from analytics import get_analytics_manager

    manager = get_analytics_manager()
    sources = manager.get_source_usage()

    return {"sources": sources}


@app.get("/api/analytics/hourly")
def get_analytics_hourly():
    """获取小时分布统计"""
    from analytics import get_analytics_manager

    manager = get_analytics_manager()
    distribution = manager.get_hourly_distribution()

    return {"distribution": distribution}


# ==================== API Key 管理 API ====================

class CreateAPIKeyRequest(BaseModel):
    """创建 API Key 请求"""
    name: str
    permissions: str = "read"


class APIKeyResponse(BaseModel):
    """API Key 响应"""
    id: int
    name: str
    key: Optional[str] = None
    key_prefix: str
    permissions: str
    is_active: bool
    created_at: str
    last_used: Optional[str] = None
    usage_count: int


@app.get("/api/keys")
def list_api_keys(user: Dict = Depends(get_current_user_required)):
    """获取用户的 API Keys 列表"""
    from api_keys import get_api_key_manager

    manager = get_api_key_manager()
    keys = manager.list_keys(user["id"])

    return {"keys": keys}


@app.post("/api/keys", response_model=APIKeyResponse)
def create_api_key(
    request: CreateAPIKeyRequest,
    user: Dict = Depends(get_current_user_required)
):
    """创建新的 API Key"""
    from api_keys import get_api_key_manager

    manager = get_api_key_manager()
    result = manager.create_key(
        user_id=user["id"],
        name=request.name,
        permissions=request.permissions
    )

    return APIKeyResponse(
        id=result["id"],
        name=result["name"],
        key=result["key"],
        key_prefix=result["key_prefix"],
        permissions=result["permissions"],
        is_active=True,
        created_at=result["created_at"]
    )


@app.delete("/api/keys/{key_id}")
def revoke_api_key(
    key_id: int,
    user: Dict = Depends(get_current_user_required)
):
    """撤销/删除 API Key"""
    from api_keys import get_api_key_manager

    manager = get_api_key_manager()
    success = manager.delete_key(key_id, user["id"])

    if not success:
        raise HTTPException(status_code=404, detail="API Key 不存在")

    return {"success": True, "message": "API Key 已删除"}


@app.get("/api/keys/stats")
def get_api_key_stats(user: Dict = Depends(get_current_user_required)):
    """获取 API Key 统计"""
    from api_keys import get_api_key_manager

    manager = get_api_key_manager()
    stats = manager.get_key_stats(user["id"])

    return stats


# ==================== 开放 API (需要 API Key 认证) ====================

def get_user_from_api_key(request: Request) -> Optional[Dict]:
    """从 API Key 或 Token 获取用户"""
    from api_keys import authenticate_with_api_key
    from auth import get_current_user

    api_key = request.headers.get("X-API-Key")
    if api_key:
        return authenticate_with_api_key(api_key)

    authorization = request.headers.get("Authorization")
    if authorization:
        return get_current_user(authorization)

    return None


@app.post("/api/v1/chat")
def api_v1_chat(
    request: ChatRequest,
    http_request: Request
):
    """开放 API: 对话问答（需要 API Key 或 Token）"""
    user = get_user_from_api_key(http_request)
    if not user:
        raise HTTPException(status_code=401, detail="需要有效的 API Key 或 Token")

    import time
    from analytics import get_analytics_manager

    start_time = time.time()

    try:
        rag_engine = get_rag_engine()
        docs, metas = rag_engine._retrieve(request.message, request.source_filter)

        if not docs:
            return {"answer": "根据现有知识库，我暂时没有找到与您问题相关的信息。", "sources": []}

        messages = rag_engine._build_prompt(request.message, docs, metas)
        answer = rag_engine.llm_client.chat(messages)

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

        response_time_ms = int((time.time() - start_time) * 1000)

        analytics = get_analytics_manager()
        analytics.log_question(
            question=request.message,
            session_id=f"api_{user['id']}",
            source_filter=request.source_filter,
            has_answer=len(sources) > 0,
            response_time_ms=response_time_ms
        )

        return {"answer": answer, "sources": sources}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/documents")
def api_v1_documents(http_request: Request):
    """开放 API: 获取文档列表"""
    user = get_user_from_api_key(http_request)
    if not user:
        raise HTTPException(status_code=401, detail="需要有效的 API Key 或 Token")

    from document_manager import get_document_manager

    manager = get_document_manager()
    stats = manager.get_stats()

    return stats


@app.get("/api/v1/sources")
def api_v1_sources(http_request: Request):
    """开放 API: 获取来源列表"""
    user = get_user_from_api_key(http_request)
    if not user:
        raise HTTPException(status_code=401, detail="需要有效的 API Key 或 Token")

    vector_store = get_vector_store()
    sources = vector_store.list_sources()

    return {"sources": sources}


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
