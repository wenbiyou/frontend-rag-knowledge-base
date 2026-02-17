"""
统计分析模块
记录和分析用户使用情况，包括每日统计、热门问题等
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import Counter
from config import BASE_DIR

ANALYTICS_DB_PATH = BASE_DIR / "analytics.db"


class AnalyticsManager:
    """统计分析管理器"""

    def __init__(self):
        self.db_path = ANALYTICS_DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS question_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    question TEXT NOT NULL,
                    source_filter TEXT,
                    has_answer BOOLEAN DEFAULT TRUE,
                    response_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_questions INTEGER DEFAULT 0,
                    unique_sessions INTEGER DEFAULT 0,
                    avg_response_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_question_logs_date
                ON question_logs(date)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_question_logs_session
                ON question_logs(session_id)
            """)

            conn.commit()

    def log_question(
        self,
        question: str,
        session_id: str = None,
        source_filter: str = None,
        has_answer: bool = True,
        response_time_ms: int = None
    ) -> None:
        """记录用户提问"""
        today = datetime.now().strftime("%Y-%m-%d")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO question_logs
                (session_id, question, source_filter, has_answer, response_time_ms, date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, question, source_filter, has_answer, response_time_ms, today)
            )

            cursor.execute(
                """
                INSERT INTO daily_stats (date, total_questions)
                VALUES (?, 1)
                ON CONFLICT(date) DO UPDATE SET
                    total_questions = total_questions + 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (today,)
            )

            conn.commit()

    def get_overview(self) -> Dict:
        """获取总览统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM question_logs")
            total_questions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT session_id) FROM question_logs")
            unique_sessions = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(DISTINCT date) FROM question_logs"
            )
            active_days = cursor.fetchone()[0]

            cursor.execute(
                "SELECT AVG(response_time_ms) FROM question_logs WHERE response_time_ms IS NOT NULL"
            )
            avg_response_time = cursor.fetchone()[0] or 0

            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT COUNT(*) FROM question_logs WHERE date = ?",
                (today,)
            )
            today_questions = cursor.fetchone()[0]

            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT COUNT(*) FROM question_logs WHERE date >= ?",
                (week_ago,)
            )
            week_questions = cursor.fetchone()[0]

            return {
                "total_questions": total_questions,
                "unique_sessions": unique_sessions,
                "active_days": active_days,
                "avg_response_time_ms": int(avg_response_time),
                "today_questions": today_questions,
                "week_questions": week_questions,
            }

    def get_daily_stats(self, days: int = 30) -> List[Dict]:
        """获取每日统计"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            cursor.execute(
                """
                SELECT 
                    date,
                    COUNT(*) as total_questions,
                    COUNT(DISTINCT session_id) as unique_sessions,
                    AVG(response_time_ms) as avg_response_time_ms
                FROM question_logs
                WHERE date >= ?
                GROUP BY date
                ORDER BY date ASC
                """,
                (start_date,)
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_popular_questions(self, limit: int = 20) -> List[Dict]:
        """获取热门问题"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    question,
                    COUNT(*) as count,
                    COUNT(DISTINCT session_id) as unique_askers
                FROM question_logs
                GROUP BY question
                ORDER BY count DESC
                LIMIT ?
                """,
                (limit,)
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_source_usage(self) -> List[Dict]:
        """获取来源使用统计"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    COALESCE(source_filter, 'all') as source,
                    COUNT(*) as count
                FROM question_logs
                GROUP BY source_filter
                ORDER BY count DESC
                """
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_hourly_distribution(self) -> List[Dict]:
        """获取小时分布统计"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    CAST(strftime('%H', created_at) AS INTEGER) as hour,
                    COUNT(*) as count
                FROM question_logs
                GROUP BY hour
                ORDER BY hour ASC
                """
            )

            result = {row["hour"]: row["count"] for row in cursor.fetchall()}

            distribution = []
            for hour in range(24):
                distribution.append({
                    "hour": hour,
                    "count": result.get(hour, 0)
                })

            return distribution


_analytics_manager = None


def get_analytics_manager() -> AnalyticsManager:
    """获取 AnalyticsManager 单例"""
    global _analytics_manager
    if _analytics_manager is None:
        _analytics_manager = AnalyticsManager()
    return _analytics_manager
