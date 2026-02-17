"""
问答质量反馈模块
支持点赞/踩、错误标记、反馈统计
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from config import BASE_DIR

FEEDBACK_DB_PATH = BASE_DIR / "feedback.db"


@dataclass
class Feedback:
    """反馈数据"""
    id: int
    message_id: str
    session_id: str
    user_id: Optional[int]
    feedback_type: str  # like, dislike, error, helpful
    comment: Optional[str]
    created_at: str


class FeedbackManager:
    """反馈管理器"""

    def __init__(self):
        self.db_path = FEEDBACK_DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    user_id INTEGER,
                    feedback_type TEXT NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedbacks_message
                ON feedbacks(message_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedbacks_session
                ON feedbacks(session_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedbacks_type
                ON feedbacks(feedback_type)
            """)

            conn.commit()

    def submit_feedback(
        self,
        message_id: str,
        session_id: str,
        feedback_type: str,
        user_id: int = None,
        comment: str = None
    ) -> Dict:
        """提交反馈"""
        valid_types = ['like', 'dislike', 'error', 'helpful']
        if feedback_type not in valid_types:
            raise ValueError(f"无效的反馈类型: {feedback_type}")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id FROM feedbacks
                WHERE message_id = ? AND user_id = ? AND feedback_type = ?
                """,
                (message_id, user_id, feedback_type)
            )

            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "DELETE FROM feedbacks WHERE id = ?",
                    (existing[0],)
                )
                conn.commit()
                return {"action": "removed", "feedback_id": existing[0]}

            cursor.execute(
                """
                INSERT INTO feedbacks (message_id, session_id, user_id, feedback_type, comment)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, session_id, user_id, feedback_type, comment)
            )

            conn.commit()

            return {
                "action": "added",
                "feedback_id": cursor.lastrowid,
                "message_id": message_id,
                "feedback_type": feedback_type
            }

    def get_message_feedback(self, message_id: str) -> Dict:
        """获取消息的反馈统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT feedback_type, COUNT(*) as count
                FROM feedbacks
                WHERE message_id = ?
                GROUP BY feedback_type
                """,
                (message_id,)
            )

            stats = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                "message_id": message_id,
                "likes": stats.get('like', 0),
                "dislikes": stats.get('dislike', 0),
                "errors": stats.get('error', 0),
                "helpful": stats.get('helpful', 0)
            }

    def get_user_feedback(
        self,
        message_id: str,
        user_id: int
    ) -> Optional[str]:
        """获取用户对消息的反馈"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT feedback_type FROM feedbacks
                WHERE message_id = ? AND user_id = ?
                """,
                (message_id, user_id)
            )

            row = cursor.fetchone()
            return row[0] if row else None

    def get_session_feedback(self, session_id: str) -> List[Dict]:
        """获取会话的所有反馈"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, message_id, feedback_type, comment, created_at
                FROM feedbacks
                WHERE session_id = ?
                ORDER BY created_at DESC
                """,
                (session_id,)
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_recent_feedback(self, limit: int = 50) -> List[Dict]:
        """获取最近的反馈"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT f.*, c.content as message_preview
                FROM feedbacks f
                LEFT JOIN chat_messages c ON f.message_id = CAST(c.id AS TEXT)
                ORDER BY f.created_at DESC
                LIMIT ?
                """,
                (limit,)
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_feedback_stats(self, days: int = 7) -> Dict:
        """获取反馈统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT feedback_type, COUNT(*) as count
                FROM feedbacks
                WHERE created_at >= datetime('now', ?)
                GROUP BY feedback_type
                """,
                (f'-{days} days',)
            )

            by_type = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT COUNT(DISTINCT session_id)
                FROM feedbacks
                WHERE created_at >= datetime('now', ?)
                """,
                (f'-{days} days',)
            )

            sessions_with_feedback = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*) FROM feedbacks
                WHERE feedback_type = 'error'
                AND created_at >= datetime('now', ?)
                """,
                (f'-{days} days',)
            )

            error_reports = cursor.fetchone()[0]

            total_feedback = sum(by_type.values())

            satisfaction_rate = 0
            if total_feedback > 0:
                positive = by_type.get('like', 0) + by_type.get('helpful', 0)
                negative = by_type.get('dislike', 0) + by_type.get('error', 0)
                satisfaction_rate = round(positive / (positive + negative) * 100, 1) if (positive + negative) > 0 else 0

            return {
                "period_days": days,
                "total_feedback": total_feedback,
                "by_type": by_type,
                "sessions_with_feedback": sessions_with_feedback,
                "error_reports": error_reports,
                "satisfaction_rate": satisfaction_rate
            }

    def get_problematic_messages(self, limit: int = 20) -> List[Dict]:
        """获取问题消息（被标记为错误或踩的）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT message_id,
                       SUM(CASE WHEN feedback_type = 'error' THEN 1 ELSE 0 END) as error_count,
                       SUM(CASE WHEN feedback_type = 'dislike' THEN 1 ELSE 0 END) as dislike_count
                FROM feedbacks
                WHERE feedback_type IN ('error', 'dislike')
                GROUP BY message_id
                HAVING error_count > 0 OR dislike_count > 0
                ORDER BY error_count DESC, dislike_count DESC
                LIMIT ?
                """,
                (limit,)
            )

            return [dict(row) for row in cursor.fetchall()]

    def delete_feedback(self, feedback_id: int) -> bool:
        """删除反馈"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM feedbacks WHERE id = ?", (feedback_id,))
            conn.commit()

            return cursor.rowcount > 0


_feedback_manager = None


def get_feedback_manager() -> FeedbackManager:
    """获取反馈管理器单例"""
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = FeedbackManager()
    return _feedback_manager
