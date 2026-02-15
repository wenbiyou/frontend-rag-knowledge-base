"""
对话历史管理模块
使用 SQLite 持久化存储对话记录
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from config import BASE_DIR

# 数据库文件路径
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

            # 创建会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT DEFAULT '新对话',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0
                )
            """)

            # 创建消息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT NOT NULL,  -- 'user' 或 'assistant'
                    content TEXT NOT NULL,
                    sources TEXT,  -- JSON 格式的来源信息
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON chat_messages(session_id, created_at)
            """)

            conn.commit()

    def create_session(self, session_id: str, title: str = None) -> None:
        """创建新会话"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO chat_sessions (session_id, title) VALUES (?, ?)",
                (session_id, title or '新对话')
            )
            conn.commit()

    def save_message(self, session_id: str, role: str, content: str,
                     sources: List[Dict] = None) -> None:
        """保存单条消息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 保存消息
            sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
            cursor.execute(
                """
                INSERT INTO chat_messages (session_id, role, content, sources)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, sources_json)
            )

            # 更新会话的 updated_at 和 message_count
            cursor.execute(
                """
                UPDATE chat_sessions
                SET updated_at = CURRENT_TIMESTAMP,
                    message_count = message_count + 1
                WHERE session_id = ?
                """,
                (session_id,)
            )

            # 如果是第一条用户消息，自动设置会话标题
            if role == 'user':
                cursor.execute(
                    "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
                    (session_id,)
                )
                count = cursor.fetchone()[0]
                if count <= 2:  # 第一条或第二条消息
                    # 使用用户消息的前 20 字作为标题
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

    def get_all_sessions(self, limit: int = 50) -> List[Dict]:
        """获取所有会话列表（最近更新的在前）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT session_id, title, created_at, updated_at, message_count
                FROM chat_sessions
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

    def delete_session(self, session_id: str) -> bool:
        """删除会话及其所有消息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 先删除消息
            cursor.execute(
                "DELETE FROM chat_messages WHERE session_id = ?",
                (session_id,)
            )

            # 再删除会话
            cursor.execute(
                "DELETE FROM chat_sessions WHERE session_id = ?",
                (session_id,)
            )

            conn.commit()
            return cursor.rowcount > 0

    def rename_session(self, session_id: str, new_title: str) -> bool:
        """重命名会话"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chat_sessions SET title = ? WHERE session_id = ?",
                (new_title, session_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict:
        """获取对话统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM chat_sessions")
            session_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM chat_messages")
            message_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM chat_messages WHERE role = 'user'"
            )
            user_message_count = cursor.fetchone()[0]

            return {
                'total_sessions': session_count,
                'total_messages': message_count,
                'user_messages': user_message_count,
                'assistant_messages': message_count - user_message_count
            }


# 单例模式
_history_manager = None


def get_history_manager() -> ChatHistoryManager:
    """获取 ChatHistoryManager 单例"""
    global _history_manager
    if _history_manager is None:
        _history_manager = ChatHistoryManager()
    return _history_manager
