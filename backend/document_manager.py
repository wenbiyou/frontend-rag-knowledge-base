"""
文档管理模块
管理已导入文档的元数据，支持列表查询、删除等功能
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from config import BASE_DIR

DOCUMENT_DB_PATH = BASE_DIR / "documents.db"


class DocumentManager:
    """文档管理器"""

    def __init__(self):
        self.db_path = DOCUMENT_DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT UNIQUE NOT NULL,
                    title TEXT,
                    source_type TEXT DEFAULT 'document',
                    file_type TEXT,
                    chunk_count INTEGER DEFAULT 0,
                    total_chars INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_source
                ON documents(source)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_type
                ON documents(source_type)
            """)

            conn.commit()

    def add_document(
        self,
        source: str,
        title: str = None,
        source_type: str = "document",
        file_type: str = None,
        chunk_count: int = 0,
        total_chars: int = 0,
        metadata: Dict = None
    ) -> Dict:
        """添加或更新文档记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

            cursor.execute(
                """
                INSERT INTO documents (source, title, source_type, file_type, chunk_count, total_chars, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source) DO UPDATE SET
                    title = excluded.title,
                    chunk_count = excluded.chunk_count,
                    total_chars = excluded.total_chars,
                    updated_at = CURRENT_TIMESTAMP,
                    status = 'active'
                """,
                (source, title or source, source_type, file_type, chunk_count, total_chars, metadata_json)
            )

            conn.commit()

            return self.get_document(source)

    def get_document(self, source: str) -> Optional[Dict]:
        """获取单个文档信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM documents WHERE source = ?",
                (source,)
            )

            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    def list_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        source_type: str = None,
        status: str = None,
        search: str = None
    ) -> Dict:
        """获取文档列表（分页）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            where_clauses = []
            params = []

            if source_type:
                where_clauses.append("source_type = ?")
                params.append(source_type)

            if status:
                where_clauses.append("status = ?")
                params.append(status)

            if search:
                where_clauses.append("(title LIKE ? OR source LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            count_cursor = cursor.execute(
                f"SELECT COUNT(*) FROM documents WHERE {where_sql}",
                params
            )
            total = count_cursor.fetchone()[0]

            offset = (page - 1) * page_size
            cursor.execute(
                f"""
                SELECT * FROM documents
                WHERE {where_sql}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset]
            )

            documents = [self._row_to_dict(row) for row in cursor.fetchall()]

            return {
                "documents": documents,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }

    def delete_document(self, source: str) -> bool:
        """软删除文档（标记为已删除）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE documents SET status = 'deleted', updated_at = CURRENT_TIMESTAMP WHERE source = ?",
                (source,)
            )

            conn.commit()
            return cursor.rowcount > 0

    def hard_delete_document(self, source: str) -> bool:
        """永久删除文档记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM documents WHERE source = ?",
                (source,)
            )

            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict:
        """获取文档统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM documents WHERE status = 'active'")
            total_documents = cursor.fetchone()[0]

            cursor.execute(
                "SELECT source_type, COUNT(*) FROM documents WHERE status = 'active' GROUP BY source_type"
            )
            by_type = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT SUM(chunk_count) FROM documents WHERE status = 'active'")
            total_chunks = cursor.fetchone()[0] or 0

            cursor.execute("SELECT SUM(total_chars) FROM documents WHERE status = 'active'")
            total_chars = cursor.fetchone()[0] or 0

            return {
                "total_documents": total_documents,
                "total_chunks": total_chunks,
                "total_chars": total_chars,
                "by_type": by_type
            }

    def sync_from_vector_store(self, vector_store):
        """从向量数据库同步文档信息"""
        all_data = vector_store.collection.get()

        source_info = {}
        for i, meta in enumerate(all_data.get("metadatas", [])):
            if not meta:
                continue

            source = meta.get("source", "unknown")
            if source not in source_info:
                source_info[source] = {
                    "title": meta.get("title", source),
                    "source_type": meta.get("source_type", "document"),
                    "chunk_count": 0,
                    "total_chars": 0
                }

            source_info[source]["chunk_count"] += 1
            doc = all_data.get("documents", [])[i] if i < len(all_data.get("documents", [])) else ""
            source_info[source]["total_chars"] += len(doc)

        for source, info in source_info.items():
            self.add_document(
                source=source,
                title=info["title"],
                source_type=info["source_type"],
                chunk_count=info["chunk_count"],
                total_chars=info["total_chars"]
            )

        return len(source_info)

    def _row_to_dict(self, row) -> Dict:
        """将数据库行转换为字典"""
        result = dict(row)
        if result.get("metadata"):
            result["metadata"] = json.loads(result["metadata"])
        return result


_document_manager = None


def get_document_manager() -> DocumentManager:
    """获取 DocumentManager 单例"""
    global _document_manager
    if _document_manager is None:
        _document_manager = DocumentManager()
    return _document_manager
