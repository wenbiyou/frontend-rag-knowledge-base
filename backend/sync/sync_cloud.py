"""
云端同步模块
支持数据导出、导入、同步配置管理
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
from config import SYNC_DB_PATH, BASE_DIR

EXPORT_DIR = BASE_DIR / "exports"


class SyncManager:
    """云端同步管理器"""

    def __init__(self):
        self.db_path = SYNC_DB_PATH
        self.export_dir = EXPORT_DIR
        self.export_dir.mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    provider TEXT,
                    endpoint TEXT,
                    credentials TEXT,
                    auto_sync BOOLEAN DEFAULT FALSE,
                    last_sync TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    status TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    def get_config(self, user_id: int) -> Optional[Dict]:
        """获取用户的同步配置"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT provider, endpoint, auto_sync, last_sync
                FROM sync_config
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (user_id,)
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def set_config(
        self,
        user_id: int,
        provider: str = None,
        endpoint: str = None,
        credentials: Dict = None,
        auto_sync: bool = False
    ) -> Dict:
        """设置同步配置"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            credentials_json = json.dumps(credentials, ensure_ascii=False) if credentials else None

            cursor.execute(
                """
                INSERT INTO sync_config (user_id, provider, endpoint, credentials, auto_sync)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    provider = excluded.provider,
                    endpoint = excluded.endpoint,
                    credentials = excluded.credentials,
                    auto_sync = excluded.auto_sync,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, provider, endpoint, credentials_json, auto_sync)
            )

            conn.commit()

            return {
                "success": True,
                "message": "同步配置已保存"
            }

    def export_data(self, user_id: int) -> Dict:
        """导出用户数据"""
        from chat_history import get_history_manager
        from document_manager import get_document_manager

        history_manager = get_history_manager()
        doc_manager = get_document_manager()

        sessions = history_manager.get_all_sessions(limit=1000, user_id=user_id)
        session_messages = {}
        for session in sessions:
            messages = history_manager.get_session_messages(session["session_id"])
            session_messages[session["session_id"]] = messages

        export_data = {
            "version": "2.0.0",
            "exported_at": datetime.now().isoformat(),
            "user_id": user_id,
            "sessions": sessions,
            "messages": session_messages
        }

        filename = f"export_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.export_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        self._log_sync(user_id, "export", "success", {"filename": filename})

        return {
            "success": True,
            "filename": filename,
            "download_url": f"/api/sync/download/{filename}",
            "sessions_count": len(sessions),
            "exported_at": datetime.now().isoformat()
        }

    def import_data(self, user_id: int, data: Dict) -> Dict:
        """导入用户数据"""
        from chat_history import get_history_manager

        history_manager = get_history_manager()

        if data.get("version") != "2.0.0":
            return {"error": "不支持的导出版本"}

        sessions = data.get("sessions", [])
        messages = data.get("messages", {})

        imported_sessions = 0
        imported_messages = 0

        for session in sessions:
            session_id = session["session_id"]
            history_manager.create_session(
                session_id=session_id,
                title=session.get("title"),
                user_id=user_id
            )
            imported_sessions += 1

            session_msgs = messages.get(session_id, [])
            for msg in session_msgs:
                history_manager.save_message(
                    session_id=session_id,
                    role=msg["role"],
                    content=msg["content"],
                    sources=msg.get("sources")
                )
                imported_messages += 1

        self._log_sync(user_id, "import", "success", {
            "sessions": imported_sessions,
            "messages": imported_messages
        })

        return {
            "success": True,
            "message": f"导入完成：{imported_sessions} 个会话，{imported_messages} 条消息",
            "imported_sessions": imported_sessions,
            "imported_messages": imported_messages
        }

    def get_sync_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """获取同步历史"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT action, status, details, created_at
                FROM sync_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            )

            return [dict(row) for row in cursor.fetchall()]

    def _log_sync(self, user_id: int, action: str, status: str, details: Dict = None):
        """记录同步日志"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            details_json = json.dumps(details, ensure_ascii=False) if details else None

            cursor.execute(
                """
                INSERT INTO sync_history (user_id, action, status, details)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, action, status, details_json)
            )

            conn.commit()

    def get_export_file(self, filename: str) -> Optional[Path]:
        """获取导出文件路径"""
        filepath = self.export_dir / filename
        if filepath.exists() and filepath.is_file():
            return filepath
        return None

    def list_exports(self, user_id: int = None) -> List[Dict]:
        """列出导出文件"""
        exports = []
        for file in self.export_dir.glob("export_*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                exports.append({
                    "filename": file.name,
                    "user_id": data.get("user_id"),
                    "exported_at": data.get("exported_at"),
                    "sessions_count": len(data.get("sessions", []))
                })
            except Exception:
                continue

        if user_id:
            exports = [e for e in exports if e["user_id"] == user_id]

        return sorted(exports, key=lambda x: x["exported_at"], reverse=True)


_sync_manager = None


def get_sync_manager() -> SyncManager:
    """获取 SyncManager 单例"""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager()
    return _sync_manager
