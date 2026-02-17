"""
GitHub 仓库数据库管理
存储仓库配置和同步历史
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from config import SYNC_DB_PATH


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(SYNC_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 仓库配置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name TEXT UNIQUE NOT NULL,
            enabled INTEGER DEFAULT 1,
            auto_sync INTEGER DEFAULT 1,
            webhook_configured INTEGER DEFAULT 0,
            last_sync_at TEXT,
            last_sync_status TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # 同步历史表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name TEXT NOT NULL,
            sync_type TEXT NOT NULL,
            status TEXT NOT NULL,
            files_synced INTEGER DEFAULT 0,
            error_message TEXT,
            triggered_by TEXT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (repo_name) REFERENCES repos(repo_name)
        )
    """)

    # Webhook 事件日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS webhook_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            action TEXT,
            payload TEXT,
            processed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (repo_name) REFERENCES repos(repo_name)
        )
    """)

    conn.commit()
    conn.close()


def add_repo(repo_name: str, enabled: bool = True, auto_sync: bool = True) -> Dict:
    """添加仓库配置"""
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    try:
        cursor.execute("""
            INSERT INTO repos (repo_name, enabled, auto_sync, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (repo_name, int(enabled), int(auto_sync), now, now))

        conn.commit()
        repo_id = cursor.lastrowid

        return {
            "id": repo_id,
            "repo_name": repo_name,
            "enabled": enabled,
            "auto_sync": auto_sync,
            "created_at": now,
            "updated_at": now
        }
    except sqlite3.IntegrityError:
        return {"error": f"仓库 {repo_name} 已存在"}
    finally:
        conn.close()


def get_repo(repo_name: str) -> Optional[Dict]:
    """获取仓库配置"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM repos WHERE repo_name = ?", (repo_name,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_all_repos() -> List[Dict]:
    """获取所有仓库配置"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM repos ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def update_repo(repo_name: str, **kwargs) -> bool:
    """更新仓库配置"""
    if not kwargs:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    kwargs["updated_at"] = datetime.now().isoformat()

    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [repo_name]

    cursor.execute(f"UPDATE repos SET {set_clause} WHERE repo_name = ?", values)
    success = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return success


def delete_repo(repo_name: str) -> bool:
    """删除仓库配置"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM repos WHERE repo_name = ?", (repo_name,))
    success = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return success


def add_sync_history(
    repo_name: str,
    sync_type: str,
    status: str,
    files_synced: int = 0,
    error_message: str = None,
    triggered_by: str = "manual"
) -> Dict:
    """添加同步历史记录"""
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO sync_history 
        (repo_name, sync_type, status, files_synced, error_message, triggered_by, started_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (repo_name, sync_type, status, files_synced, error_message, triggered_by, now))

    history_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": history_id,
        "repo_name": repo_name,
        "sync_type": sync_type,
        "status": status,
        "files_synced": files_synced,
        "error_message": error_message,
        "triggered_by": triggered_by,
        "started_at": now
    }


def complete_sync_history(history_id: int, status: str, files_synced: int = 0, error_message: str = None):
    """完成同步历史记录"""
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute("""
        UPDATE sync_history 
        SET status = ?, files_synced = ?, error_message = ?, completed_at = ?
        WHERE id = ?
    """, (status, files_synced, error_message, now, history_id))

    conn.commit()
    conn.close()


def get_sync_history(repo_name: str = None, limit: int = 50) -> List[Dict]:
    """获取同步历史"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if repo_name:
        cursor.execute("""
            SELECT * FROM sync_history 
            WHERE repo_name = ? 
            ORDER BY started_at DESC 
            LIMIT ?
        """, (repo_name, limit))
    else:
        cursor.execute("""
            SELECT * FROM sync_history 
            ORDER BY started_at DESC 
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def add_webhook_event(
    repo_name: str,
    event_type: str,
    action: str,
    payload: dict,
    processed: bool = False
) -> Dict:
    """添加 Webhook 事件记录"""
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO webhook_events 
        (repo_name, event_type, action, payload, processed, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (repo_name, event_type, action, json.dumps(payload), int(processed), now))

    event_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": event_id,
        "repo_name": repo_name,
        "event_type": event_type,
        "action": action,
        "processed": processed,
        "created_at": now
    }


def mark_webhook_processed(event_id: int):
    """标记 Webhook 事件为已处理"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE webhook_events SET processed = 1 WHERE id = ?", (event_id,))

    conn.commit()
    conn.close()


# 初始化数据库
init_db()
