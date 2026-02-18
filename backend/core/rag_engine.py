"""
RAG 核心引擎
RAG = Retrieval Augmented Generation（检索增强生成）

工作流程：
1. 接收用户问题
2. 将问题转为向量
3. 在向量数据库中检索相关文档
4. 将相关文档作为上下文，让 LLM 生成回答
5. 返回答案 + 引用来源

类比：像开卷考试，先查资料，再基于资料组织答案
"""
from typing import List, Dict, Tuple
from core.database import get_vector_store
from ai.deepseek_client import get_llm_client, get_embedding_client
from config import TOP_K, SIMILARITY_THRESHOLD, MAX_CONTEXT_LENGTH, ENABLE_CACHE, CACHE_TTL


class RAGEngine:
    """RAG 问答引擎"""

    # 系统提示词模板 - 定义 AI 的角色和回答规范
    SYSTEM_PROMPT = """你是一个专业的前端开发知识库助手，拥有丰富的前端技术经验和深厚的行业知识。

你的核心任务是：
- 帮助前端开发者快速查找和理解前端相关的技术知识
- 提供公司内部的技术规范、最佳实践和开发指南
- 解答前端技术问题，给出专业、准确、实用的建议

回答质量标准：
1. 准确性：严格基于提供的参考文档回答，不编造信息，不猜测
2. 完整性：回答要全面覆盖问题的所有方面，不遗漏重要信息
3. 实用性：提供具体、可操作的解决方案和代码示例
4. 清晰度：使用专业但易懂的语言，结构清晰，逻辑连贯
5. 权威性：引用权威来源，优先使用公司内部规范和官方文档

回答格式规范：
- 代码示例：使用 Markdown 代码块，附带必要的注释和说明
- 多方面问题：使用分点或标题结构，层次分明
- 技术概念：给出清晰的定义和实际应用场景
- 最佳实践：提供具体的实施建议和注意事项

参考文档使用要求：
- 必须基于【参考文档】中的内容回答
- 可以引用多个文档的内容，但要确保信息一致
- 如果文档中没有相关信息，明确告知用户并提供可能的解决方案
- 回答中可以适当添加个人专业见解，但必须基于文档内容

参考文档信息会在用户问题后以"【参考文档】"的形式提供。"""

    def __init__(self):
        """初始化 RAG 引擎组件"""
        self.vector_store = get_vector_store()
        self.llm_client = get_llm_client()
        self.embedding_client = get_embedding_client()

    def _retrieve(self, query: str, source_filter: str = None, top_k: int = None) -> Tuple[List[str], List[Dict]]:
        """
        检索相关文档

        Args:
            query: 用户查询
            source_filter: 可选的过滤条件（如只查特定来源）
            top_k: 返回结果数量（默认使用配置中的 TOP_K）

        Returns:
            (文档内容列表, 元数据列表)
        """
        # 1. 将查询转为向量
        query_embedding = self.embedding_client.get_embeddings([query])[0]

        # 2. 构建过滤条件
        filter_dict = None
        if source_filter:
            filter_dict = {"source_type": source_filter}

        # 3. 执行检索
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=top_k or TOP_K,
            filter_dict=filter_dict
        )

        # 4. 处理结果
        documents = results.get("documents", [[]])[0]  # ChromaDB 返回嵌套列表
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # 5. 根据相似度阈值过滤（ChromaDB 返回的是 L2 距离，越小越相似）
        # 使用指数衰减函数将 L2 距离转换为相似度分数
        import math
        filtered_docs = []
        filtered_metas = []

        for doc, meta, dist in zip(documents, metadatas, distances):
            # 使用指数函数转换距离为相似度：距离越小，相似度越高
            # 当 dist=0 时 similarity=1，当 dist 增大时 similarity 趋近于 0
            similarity = math.exp(-dist / 10.0)
            if similarity >= SIMILARITY_THRESHOLD:
                filtered_docs.append(doc)
                filtered_metas.append(meta)

        return filtered_docs, filtered_metas

    def _build_prompt(self, query: str, context_docs: List[str], context_metas: List[Dict]) -> List[Dict]:
        """
        构建 LLM 的提示词

        Args:
            query: 用户问题
            context_docs: 检索到的文档内容
            context_metas: 检索到的文档元数据

        Returns:
            符合 OpenAI/DeepSeek 格式的消息列表
        """
        context_parts = []
        for i, (doc, meta) in enumerate(zip(context_docs, context_metas), 1):
            source = meta.get("source", "未知来源")
            title = meta.get("title", "")
            truncated_doc = doc[:MAX_CONTEXT_LENGTH] if len(doc) > MAX_CONTEXT_LENGTH else doc
            if len(doc) > MAX_CONTEXT_LENGTH:
                truncated_doc += "..."
            context_parts.append(f"【文档 {i}】\n来源: {source}\n标题: {title}\n内容: {truncated_doc}\n")

        context_str = "\n".join(context_parts)

        user_message = f"""问题：{query}

【参考文档】
{context_str}

请基于以上参考文档回答问题。如果文档中没有相关信息，请明确告知。"""

        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

    def query(self, question: str, source_filter: str = None) -> Dict:
        """
        执行完整的 RAG 查询流程

        Args:
            question: 用户问题
            source_filter: 可选的过滤条件

        Returns:
            包含 answer（回答）、sources（来源）、context（上下文）的字典
        """
        # 1. 检索相关文档
        docs, metas = self._retrieve(question, source_filter)

        # 如果没有找到相关文档
        if not docs:
            return {
                "answer": "根据现有知识库，我暂时没有找到与您问题相关的信息。\n\n可能原因：\n1. 相关文档尚未导入知识库\n2. 问题表述与文档内容差异较大\n\n建议：\n- 尝试用不同的关键词提问\n- 联系管理员添加相关文档",
                "sources": [],
                "context": []
            }

        # 2. 构建提示词
        messages = self._build_prompt(question, docs, metas)

        # 3. 调用 LLM 生成回答
        try:
            answer = self.llm_client.chat(messages)
        except Exception as e:
            return {
                "answer": f"生成回答时出错: {str(e)}",
                "sources": [],
                "context": []
            }

        # 4. 整理来源信息
        sources = []
        seen_sources = set()
        for meta in metas:
            source_key = f"{meta.get('source', '未知')}:{meta.get('title', '')}"
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append({
                    "title": meta.get("title", "未命名文档"),
                    "source": meta.get("source", "未知来源"),
                    "type": meta.get("source_type", "document"),
                    "url": meta.get("url", "")
                })

        return {
            "answer": answer,
            "sources": sources,
            "context": [
                {"content": doc, "metadata": meta}
                for doc, meta in zip(docs, metas)
            ]
        }

    def query_stream(self, question: str, source_filter: str = None):
        """
        流式执行 RAG 查询（实时返回生成内容）
        用于前端展示打字机效果
        """
        # 1. 检索相关文档
        docs, metas = self._retrieve(question, source_filter)

        if not docs:
            yield "根据现有知识库，我暂时没有找到与您问题相关的信息。"
            return

        # 2. 构建提示词
        messages = self._build_prompt(question, docs, metas)

        # 3. 流式生成回答
        for chunk in self.llm_client.chat_stream(messages):
            yield chunk


class ChatSession:
    """
    对话会话管理
    支持多轮对话上下文记忆，自动持久化到数据库
    """

    def __init__(self, session_id: str = None):
        from admin.chat_history import get_history_manager

        self.session_id = session_id or self._generate_session_id()
        self.rag_engine = RAGEngine()
        self.history_manager = get_history_manager()

        # 如果是新会话，创建数据库记录
        if session_id is None:
            self.history_manager.create_session(self.session_id)
            self.history = []
        else:
            # 加载已有会话的历史
            self.history = self.history_manager.get_session_messages(self.session_id)

    def _generate_session_id(self) -> str:
        """生成唯一会话 ID"""
        import uuid
        return str(uuid.uuid4())

    def chat(self, message: str, source_filter: str = None) -> Dict:
        """
        进行一轮对话

        Args:
            message: 用户消息
            source_filter: 可选的过滤条件

        Returns:
            包含回答和来源的字典
        """
        # 保存用户消息到数据库
        self.history_manager.save_message(
            session_id=self.session_id,
            role="user",
            content=message
        )

        # 执行 RAG 查询
        result = self.rag_engine.query(message, source_filter)

        # 保存助手回答到数据库
        self.history_manager.save_message(
            session_id=self.session_id,
            role="assistant",
            content=result["answer"],
            sources=result.get("sources", [])
        )

        # 更新内存中的历史（用于上下文）
        self.history.append({"role": "user", "content": message})
        self.history.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result.get("sources", [])
        })

        # 保留最近 10 轮对话（避免上下文过长）
        if len(self.history) > 20:
            self.history = self.history[-20:]

        return result

    def get_history(self) -> List[Dict]:
        """获取对话历史（从数据库重新加载）"""
        return self.history_manager.get_session_messages(self.session_id)

    def clear_history(self):
        """清空对话历史（删除数据库记录）"""
        self.history_manager.delete_session(self.session_id)
        self.history = []
        # 重新创建空会话
        self.history_manager.create_session(self.session_id)


# 便捷函数
_rag_engine = None

def get_rag_engine() -> RAGEngine:
    """获取 RAG 引擎单例"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
