"""
用户认证模块
支持用户注册、登录、JWT Token 认证
"""
import sqlite3
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from functools import wraps
from config import BASE_DIR

AUTH_DB_PATH = BASE_DIR / "users.db"
JWT_SECRET = secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7


def hash_password(password: str) -> str:
    """密码加密"""
    return hashlib.sha256(password.encode() + JWT_SECRET.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return hash_password(password) == hashed


def create_token(user_id: int, username: str, role: str) -> str:
    """创建 JWT Token"""
    import base64
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": (datetime.now() + timedelta(hours=JWT_EXPIRE_HOURS)).isoformat()
    }
    payload_str = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_str.encode()).decode()
    signature = hashlib.sha256(f"{payload_b64}.{JWT_SECRET}".encode()).hexdigest()[:32]
    return f"{payload_b64}.{signature}"


def decode_token(token: str) -> Optional[Dict]:
    """解码 JWT Token"""
    try:
        import base64
        parts = token.split('.')
        if len(parts) != 2:
            return None

        payload_b64, signature = parts
        expected_sig = hashlib.sha256(f"{payload_b64}.{JWT_SECRET}".encode()).hexdigest()[:32]
        if signature != expected_sig:
            return None

        payload_str = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_str)

        if datetime.fromisoformat(payload["exp"]) < datetime.now():
            return None

        return payload
    except Exception:
        return None


class UserManager:
    """用户管理器"""

    def __init__(self):
        self.db_path = AUTH_DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    expertise TEXT,
                    bio TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username
                ON users(username)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email
                ON users(email)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_role
                ON users(role)
            """)

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN expertise TEXT")
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN bio TEXT")
            except sqlite3.OperationalError:
                pass

            admin_exists = cursor.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin'"
            ).fetchone()[0]

            if admin_exists == 0:
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("admin", "admin@localhost", hash_password("admin123"), "admin")
                )

            conn.commit()

    def create_user(
        self,
        username: str,
        password: str,
        email: str = None,
        role: str = "user"
    ) -> Dict:
        """创建用户"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, email, hash_password(password), role)
                )
                conn.commit()

                user_id = cursor.lastrowid
                return {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "role": role,
                    "created_at": datetime.now().isoformat()
                }
            except sqlite3.IntegrityError as e:
                if "username" in str(e):
                    return {"error": "用户名已存在"}
                elif "email" in str(e):
                    return {"error": "邮箱已被注册"}
                return {"error": "创建用户失败"}

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """验证用户登录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )

            row = cursor.fetchone()
            if not row:
                return None

            if not verify_password(password, row["password_hash"]):
                return None

            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (row["id"],)
            )
            conn.commit()

            return {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "role": row["role"],
                "created_at": row["created_at"]
            }

    def get_user(self, user_id: int) -> Optional[Dict]:
        """获取用户信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, username, email, role, expertise, bio, created_at, last_login FROM users WHERE id = ?",
                (user_id,)
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """通过用户名获取用户"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, username, email, role, created_at FROM users WHERE username = ?",
                (username,)
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def list_users(self) -> list:
        """获取所有用户列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, username, email, role, expertise, bio, created_at, last_login FROM users ORDER BY created_at DESC"
            )

            return [dict(row) for row in cursor.fetchall()]

    def list_experts(self) -> list:
        """获取所有专家列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, username, email, expertise, bio, created_at FROM users WHERE role = 'expert' ORDER BY created_at DESC"
            )

            return [dict(row) for row in cursor.fetchall()]

    def set_expert(self, user_id: int, expertise: str = None, bio: str = None) -> bool:
        """设置用户为专家"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE users
                SET role = 'expert', expertise = ?, bio = ?
                WHERE id = ?
                """,
                (expertise, bio, user_id)
            )

            conn.commit()
            return cursor.rowcount > 0

    def remove_expert(self, user_id: int) -> bool:
        """移除专家身份"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE users
                SET role = 'user', expertise = NULL, bio = NULL
                WHERE id = ? AND role = 'expert'
                """,
                (user_id,)
            )

            conn.commit()
            return cursor.rowcount > 0

    def update_expert_profile(
        self,
        user_id: int,
        expertise: str = None,
        bio: str = None
    ) -> bool:
        """更新专家资料"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            updates = []
            values = []

            if expertise is not None:
                updates.append("expertise = ?")
                values.append(expertise)
            if bio is not None:
                updates.append("bio = ?")
                values.append(bio)

            if not updates:
                return False

            values.append(user_id)

            cursor.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                values
            )

            conn.commit()
            return cursor.rowcount > 0

    def update_user(self, user_id: int, **kwargs) -> bool:
        """更新用户信息"""
        allowed_fields = {"email", "role", "expertise", "bio"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            set_clause = ", ".join(f"{k} = ?" for k in updates)
            cursor.execute(
                f"UPDATE users SET {set_clause} WHERE id = ?",
                list(updates.values()) + [user_id]
            )

            conn.commit()
            return cursor.rowcount > 0

    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

            return cursor.rowcount > 0

    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict:
        """修改密码"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user_id,)
            )

            row = cursor.fetchone()
            if not row:
                return {"error": "用户不存在"}

            if not verify_password(old_password, row["password_hash"]):
                return {"error": "原密码错误"}

            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), user_id)
            )
            conn.commit()

            return {"success": True, "message": "密码修改成功"}


_user_manager = None


def get_user_manager() -> UserManager:
    """获取 UserManager 单例"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager


def get_current_user(authorization: str = None) -> Optional[Dict]:
    """从 Authorization header 获取当前用户"""
    if not authorization:
        return None

    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization

    payload = decode_token(token)
    if not payload:
        return None

    manager = get_user_manager()
    return manager.get_user(payload["user_id"])
