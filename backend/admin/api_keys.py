"""
API Key 管理模块
支持 API Key 生成、验证、权限控制
"""
import sqlite3
import secrets
import hashlib
from datetime import datetime
from typing import Optional, Dict, List
from config import CORE_DB_PATH


def generate_api_key() -> str:
    """生成 API Key"""
    return f"sk-{secrets.token_hex(24)}"


def hash_api_key(key: str) -> str:
    """API Key 哈希"""
    return hashlib.sha256(key.encode()).hexdigest()


class APIKeyManager:
    """API Key 管理器"""

    def __init__(self):
        self.db_path = CORE_DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    key_hash TEXT UNIQUE NOT NULL,
                    key_prefix TEXT NOT NULL,
                    name TEXT NOT NULL,
                    permissions TEXT DEFAULT 'read',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    usage_count INTEGER DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_keys_user
                ON api_keys(user_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_keys_prefix
                ON api_keys(key_prefix)
            """)

            conn.commit()

    def create_key(
        self,
        user_id: int,
        name: str,
        permissions: str = "read"
    ) -> Dict:
        """创建 API Key"""
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        key_prefix = api_key[:10]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO api_keys (user_id, key_hash, key_prefix, name, permissions)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, key_hash, key_prefix, name, permissions)
            )

            conn.commit()

            return {
                "id": cursor.lastrowid,
                "name": name,
                "key": api_key,
                "key_prefix": key_prefix,
                "permissions": permissions,
                "created_at": datetime.now().isoformat(),
                "warning": "请妥善保存 API Key，系统不会再次显示完整 Key"
            }

    def validate_key(self, api_key: str) -> Optional[Dict]:
        """验证 API Key"""
        key_hash = hash_api_key(api_key)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, user_id, name, permissions, is_active
                FROM api_keys
                WHERE key_hash = ?
                """,
                (key_hash,)
            )

            row = cursor.fetchone()
            if not row or not row["is_active"]:
                return None

            cursor.execute(
                """
                UPDATE api_keys
                SET last_used = CURRENT_TIMESTAMP, usage_count = usage_count + 1
                WHERE id = ?
                """,
                (row["id"],)
            )
            conn.commit()

            return {
                "id": row["id"],
                "user_id": row["user_id"],
                "name": row["name"],
                "permissions": row["permissions"]
            }

    def list_keys(self, user_id: int) -> List[Dict]:
        """获取用户的 API Key 列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, key_prefix, name, permissions, is_active,
                       created_at, last_used, usage_count
                FROM api_keys
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )

            return [dict(row) for row in cursor.fetchall()]

    def revoke_key(self, key_id: int, user_id: int) -> bool:
        """撤销 API Key"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE api_keys
                SET is_active = FALSE
                WHERE id = ? AND user_id = ?
                """,
                (key_id, user_id)
            )

            conn.commit()
            return cursor.rowcount > 0

    def delete_key(self, key_id: int, user_id: int) -> bool:
        """删除 API Key"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM api_keys WHERE id = ? AND user_id = ?",
                (key_id, user_id)
            )

            conn.commit()
            return cursor.rowcount > 0

    def get_key_stats(self, user_id: int) -> Dict:
        """获取 API Key 统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM api_keys WHERE user_id = ?",
                (user_id,)
            )
            total_keys = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM api_keys WHERE user_id = ? AND is_active = TRUE",
                (user_id,)
            )
            active_keys = cursor.fetchone()[0]

            cursor.execute(
                "SELECT SUM(usage_count) FROM api_keys WHERE user_id = ?",
                (user_id,)
            )
            total_usage = cursor.fetchone()[0] or 0

            return {
                "total_keys": total_keys,
                "active_keys": active_keys,
                "total_usage": total_usage
            }


_api_key_manager = None


def get_api_key_manager() -> APIKeyManager:
    """获取 APIKeyManager 单例"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


def authenticate_with_api_key(api_key: str) -> Optional[Dict]:
    """使用 API Key 认证"""
    manager = get_api_key_manager()
    return manager.validate_key(api_key)
