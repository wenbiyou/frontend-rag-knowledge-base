"""
向量数据库模块
使用 ChromaDB 存储文档的向量表示，支持语义检索
类比：这是一个智能索引系统，不是存储原文，而是存储"意思"方便快速查找
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import hashlib
import time
from config import CHROMA_DB_PATH

class VectorStore:
    """向量数据库封装类"""

    def __init__(self):
        """初始化 ChromaDB 客户端"""
        # 创建持久化客户端（数据会保存到磁盘）
        self.client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(
                anonymized_telemetry=False  # 关闭匿名数据收集
            )
        )

        # 获取或创建集合
        # collection 类似数据库中的表
        self.collection = self.client.get_or_create_collection(
            name="frontend_knowledge",
            metadata={"description": "前端知识库文档向量"}
        )

    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
        source_type: str = "document"
    ) -> None:
        """
        添加文档到向量数据库

        Args:
            documents: 原始文本内容列表
            embeddings: 对应的向量表示列表
            metadatas: 元数据列表（如来源、标题、URL 等）
            source_type: 文档来源类型（document/github/official）
        """
        # 生成唯一 ID（基于内容和当前时间）
        ids = []
        for i, doc in enumerate(documents):
            # 使用文档内容哈希 + 时间戳 + 索引生成唯一 ID
            content_hash = hashlib.md5(doc.encode()).hexdigest()[:12]
            timestamp = int(time.time())
            doc_id = f"{source_type}_{timestamp}_{i}_{content_hash}"
            ids.append(doc_id)

            # 添加来源类型到元数据
            metadatas[i]["source_type"] = source_type
            metadatas[i]["added_at"] = timestamp

        # 批量添加到数据库
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> Dict:
        """
        基于向量相似度检索相关文档

        Args:
            query_embedding: 查询问题的向量表示
            n_results: 返回结果数量
            filter_dict: 过滤条件（如只查某个来源的文档）

        Returns:
            包含 documents, metadatas, distances 的字典
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_dict  # 可选过滤
        )
        return results

    def delete_by_source(self, source: str) -> None:
        """删除特定来源的所有文档（用于更新时清理旧数据）"""
        self.collection.delete(
            where={"source": source}
        )

    def get_stats(self) -> Dict:
        """获取数据库统计信息"""
        count = self.collection.count()
        return {
            "total_documents": count,
            "db_path": CHROMA_DB_PATH
        }

    def list_sources(self) -> List[str]:
        """列出所有文档来源"""
        # 获取所有元数据
        all_data = self.collection.get()
        sources = set()
        for metadata in all_data.get("metadatas", []):
            if metadata and "source" in metadata:
                sources.add(metadata["source"])
        return sorted(list(sources))


# 单例模式，全局复用
_vector_store = None

def get_vector_store() -> VectorStore:
    """获取 VectorStore 单例实例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
