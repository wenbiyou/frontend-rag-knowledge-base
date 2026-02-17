"""
数据库管理模块
统一管理所有 SQLite 数据库连接，提供连接池和统一接口
"""
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
from threading import Lock
from config import DB_PATHS, DATA_DIR


class DatabaseManager:
    """
    数据库管理器
    提供统一的数据库连接管理和查询接口
    
    数据库分布：
    - core.db: 用户、API Key、聊天记录、分析数据
    - knowledge.db: 文档、代码分析、反馈
    - ai.db: 知识图谱、AI导师、推荐
    - community.db: 社区贡献、提示词分享
    - sync.db: 同步配置、GitHub 仓库
    """
    
    _instance: Optional['DatabaseManager'] = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._connections: Dict[str, sqlite3.Connection] = {}
    
    def get_connection(self, db_name: str) -> sqlite3.Connection:
        """获取数据库连接"""
        if db_name not in DB_PATHS:
            raise ValueError(f"Unknown database: {db_name}")
        
        if db_name not in self._connections:
            db_path = DB_PATHS[db_name]
            conn = sqlite3.connect(str(db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._connections[db_name] = conn
        
        return self._connections[db_name]
    
    @contextmanager
    def transaction(self, db_name: str):
        """事务上下文管理器"""
        conn = self.get_connection(db_name)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def execute(self, db_name: str, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行单条 SQL"""
        conn = self.get_connection(db_name)
        return conn.execute(query, params)
    
    def executemany(self, db_name: str, query: str, params_list: list) -> sqlite3.Cursor:
        """批量执行 SQL"""
        conn = self.get_connection(db_name)
        return conn.executemany(query, params_list)
    
    def fetchone(self, db_name: str, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """查询单条记录"""
        cursor = self.execute(db_name, query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetchall(self, db_name: str, query: str, params: tuple = ()) -> list:
        """查询多条记录"""
        cursor = self.execute(db_name, query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def close_all(self):
        """关闭所有连接"""
        for conn in self._connections.values():
            conn.close()
        self._connections.clear()


_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器单例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_core_db() -> sqlite3.Connection:
    """获取核心数据库连接"""
    return get_db_manager().get_connection("core")


def get_knowledge_db() -> sqlite3.Connection:
    """获取知识库数据库连接"""
    return get_db_manager().get_connection("knowledge")


def get_ai_db() -> sqlite3.Connection:
    """获取 AI 数据库连接"""
    return get_db_manager().get_connection("ai")


def get_community_db() -> sqlite3.Connection:
    """获取社区数据库连接"""
    return get_db_manager().get_connection("community")


def get_sync_db() -> sqlite3.Connection:
    """获取同步数据库连接"""
    return get_db_manager().get_connection("sync")
