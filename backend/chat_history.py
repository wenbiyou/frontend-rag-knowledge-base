"""
对话历史管理模块
使用 SQLite 持久化存储对话记录，支持多用户隔离
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from config import BASE_DIR

CHAT_DB_PATH = BASE_DIR / "chat_history.db"


class ChatHistoryManager:
    """对话历史管理器"""

    def __init__(self):
        self.db_path = CHAT_DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    title TEXT DEFAULT '新对话',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON chat_messages(session_id, created_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user
                ON chat_sessions(user_id, updated_at)
            """)

            conn.commit()

    def create_session(self, session_id: str, title: str = None, user_id: int = None) -> None:
        """创建新会话"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO chat_sessions (session_id, title, user_id) VALUES (?, ?, ?)",
                (session_id, title or '新对话', user_id)
            )
            conn.commit()

    def save_message(self, session_id: str, role: str, content: str,
                     sources: List[Dict] = None) -> None:
        """保存单条消息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
            cursor.execute(
                """
                INSERT INTO chat_messages (session_id, role, content, sources)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, sources_json)
            )

            cursor.execute(
                """
                UPDATE chat_sessions
                SET updated_at = CURRENT_TIMESTAMP,
                    message_count = message_count + 1
                WHERE session_id = ?
                """,
                (session_id,)
            )

            if role == 'user':
                cursor.execute(
                    "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
                    (session_id,)
                )
                count = cursor.fetchone()[0]
                if count <= 2:
                    title = content[:30] + '...' if len(content) > 30 else content
                    cursor.execute(
                        "UPDATE chat_sessions SET title = ? WHERE session_id = ?",
                        (title, session_id)
                    )

            conn.commit()

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """获取指定会话的所有消息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT role, content, sources, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,)
            )

            messages = []
            for row in cursor.fetchall():
                msg = {
                    'role': row['role'],
                    'content': row['content'],
                    'created_at': row['created_at']
                }
                if row['sources']:
                    msg['sources'] = json.loads(row['sources'])
                messages.append(msg)

            return messages

    def get_all_sessions(self, limit: int = 50, user_id: int = None) -> List[Dict]:
        """获取会话列表（支持用户隔离）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if user_id is not None:
                cursor.execute(
                    """
                    SELECT session_id, title, created_at, updated_at, message_count
                    FROM chat_sessions
                    WHERE user_id = ? OR user_id IS NULL
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (user_id, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT session_id, title, created_at, updated_at, message_count
                    FROM chat_sessions
                    WHERE user_id IS NULL
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (limit,)
                )

            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'session_id': row['session_id'],
                    'title': row['title'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'message_count': row['message_count']
                })

            return sessions

    def delete_session(self, session_id: str, user_id: int = None) -> bool:
        """删除会话及其所有消息（支持用户验证）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if user_id is not None:
                cursor.execute(
                    "SELECT user_id FROM chat_sessions WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                if row and row[0] is not None and row[0] != user_id:
                    return False

            cursor.execute(
                "DELETE FROM chat_messages WHERE session_id = ?",
                (session_id,)
            )

            cursor.execute(
                "DELETE FROM chat_sessions WHERE session_id = ?",
                (session_id,)
            )

            conn.commit()
            return cursor.rowcount > 0

    def rename_session(self, session_id: str, new_title: str, user_id: int = None) -> bool:
        """重命名会话（支持用户验证）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if user_id is not None:
                cursor.execute(
                    "SELECT user_id FROM chat_sessions WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                if row and row[0] is not None and row[0] != user_id:
                    return False

            cursor.execute(
                "UPDATE chat_sessions SET title = ? WHERE session_id = ?",
                (new_title, session_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self, user_id: int = None) -> Dict:
        """获取对话统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if user_id is not None:
                cursor.execute(
                    "SELECT COUNT(*) FROM chat_sessions WHERE user_id = ?",
                    (user_id,)
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM chat_sessions WHERE user_id IS NULL")
            session_count = cursor.fetchone()[0]

            if user_id is not None:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM chat_messages m
                    JOIN chat_sessions s ON m.session_id = s.session_id
                    WHERE s.user_id = ?
                    """,
                    (user_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM chat_messages m
                    JOIN chat_sessions s ON m.session_id = s.session_id
                    WHERE s.user_id IS NULL
                    """
                )
            message_count = cursor.fetchone()[0]

            if user_id is not None:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM chat_messages m
                    JOIN chat_sessions s ON m.session_id = s.session_id
                    WHERE s.user_id = ? AND m.role = 'user'
                    """,
                    (user_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM chat_messages m
                    JOIN chat_sessions s ON m.session_id = s.session_id
                    WHERE s.user_id IS NULL AND m.role = 'user'
                    """
                )
            user_message_count = cursor.fetchone()[0]

            return {
                'total_sessions': session_count,
                'total_messages': message_count,
                'user_messages': user_message_count,
                'assistant_messages': message_count - user_message_count
            }


_history_manager = None


def get_history_manager() -> ChatHistoryManager:
    """获取 ChatHistoryManager 单例"""
    global _history_manager
    if _history_manager is None:
        _history_manager = ChatHistoryManager()
    return _history_manager
