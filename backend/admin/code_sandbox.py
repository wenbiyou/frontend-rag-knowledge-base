"""
代码沙箱 API 管理
提供代码执行相关的 API 接口
"""

import os
import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
from pathlib import Path

from agent.sandbox import CodeSandbox, SandboxExecutor, SandboxConfig
from agent.sandbox.sandbox import Language
from agent.sandbox.limits import ResourceLimits
from config import DATA_DIR


@dataclass
class ExecutionRecord:
    """执行记录"""
    id: Optional[int] = None
    session_id: str = ""
    user_id: Optional[int] = None
    language: str = "python"
    code: str = ""
    input_data: Optional[str] = None
    output: str = ""
    error: Optional[str] = None
    execution_time: float = 0.0
    memory_used: int = 0
    exit_code: int = 0
    success: bool = False
    created_at: str = ""


class SandboxDB:
    """沙箱执行记录数据库"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DATA_DIR / "sandbox.db")
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER,
                language TEXT NOT NULL,
                code TEXT NOT NULL,
                input_data TEXT,
                output TEXT,
                error TEXT,
                execution_time REAL,
                memory_used INTEGER,
                exit_code INTEGER,
                success INTEGER,
                created_at TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_id ON executions(session_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_id ON executions(user_id)
        ''')

        conn.commit()
        conn.close()

    def save_execution(self, record: ExecutionRecord) -> int:
        """保存执行记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO executions (
                session_id, user_id, language, code, input_data,
                output, error, execution_time, memory_used,
                exit_code, success, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.session_id,
            record.user_id,
            record.language,
            record.code,
            record.input_data,
            record.output,
            record.error,
            record.execution_time,
            record.memory_used,
            record.exit_code,
            1 if record.success else 0,
            record.created_at or datetime.now().isoformat()
        ))

        record.id = cursor.lastrowid
        conn.commit()
        conn.close()

        return record.id

    def get_execution(self, execution_id: int) -> Optional[Dict]:
        """获取执行记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM executions WHERE id = ?
        ''', (execution_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def get_session_executions(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """获取会话的所有执行记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM executions
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (session_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def get_user_executions(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Dict]:
        """获取用户的所有执行记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM executions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def get_stats(self, user_id: Optional[int] = None) -> Dict:
        """获取执行统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if user_id:
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    AVG(execution_time) as avg_time,
                    language
                FROM executions
                WHERE user_id = ?
                GROUP BY language
            ''', (user_id,))
        else:
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    AVG(execution_time) as avg_time,
                    language
                FROM executions
                GROUP BY language
            ''')

        rows = cursor.fetchall()
        conn.close()

        stats = {
            "by_language": {},
            "total": 0,
            "success_rate": 0.0,
            "avg_execution_time": 0.0
        }

        total_count = 0
        total_success = 0
        total_time = 0.0

        for row in rows:
            lang = row[3]
            stats["by_language"][lang] = {
                "total": row[0],
                "success": row[1],
                "avg_time": row[2] or 0.0
            }
            total_count += row[0]
            total_success += row[1] or 0
            total_time += (row[2] or 0.0) * row[0]

        stats["total"] = total_count
        stats["success_rate"] = total_success / total_count if total_count > 0 else 0.0
        stats["avg_execution_time"] = total_time / total_count if total_count > 0 else 0.0

        return stats

    def _row_to_dict(self, row: tuple) -> Dict:
        """将数据库行转为字典"""
        return {
            "id": row[0],
            "session_id": row[1],
            "user_id": row[2],
            "language": row[3],
            "code": row[4],
            "input_data": row[5],
            "output": row[6],
            "error": row[7],
            "execution_time": row[8],
            "memory_used": row[9],
            "exit_code": row[10],
            "success": bool(row[11]),
            "created_at": row[12]
        }


class SandboxManager:
    """沙箱管理器"""

    def __init__(self):
        self.db = SandboxDB()
        self._executors: Dict[str, SandboxExecutor] = {}

    def get_executor(
        self,
        language: Language = Language.PYTHON,
        limits: Optional[ResourceLimits] = None
    ) -> SandboxExecutor:
        """获取执行器"""
        key = f"{language.value}_{id(limits)}"
        if key not in self._executors:
            config = SandboxConfig(language=language)
            if limits:
                config.limits = limits
            self._executors[key] = SandboxExecutor(config)
        return self._executors[key]

    def execute_code(
        self,
        code: str,
        language: str = "python",
        session_id: str = "",
        user_id: Optional[int] = None,
        input_data: Optional[str] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict] = None
    ) -> Dict:
        """
        执行代码并记录

        Args:
            code: 要执行的代码
            language: 编程语言
            session_id: 会话ID
            user_id: 用户ID
            input_data: 输入数据
            timeout: 超时时间
            limits: 资源限制

        Returns:
            执行结果字典
        """
        lang = Language(language.lower())

        resource_limits = None
        if limits:
            resource_limits = ResourceLimits(
                max_cpu_time=limits.get("max_cpu_time", 5.0),
                max_wall_time=limits.get("max_wall_time", 10.0),
                max_memory_mb=limits.get("max_memory_mb", 256),
            )

        executor = self.get_executor(lang, resource_limits)
        result = executor.execute(code, lang, timeout, input_data)

        record = ExecutionRecord(
            session_id=session_id,
            user_id=user_id,
            language=language,
            code=code,
            input_data=input_data,
            output=result.output,
            error=result.error,
            execution_time=result.execution_time,
            memory_used=result.memory_used,
            exit_code=result.exit_code,
            success=result.success,
            created_at=datetime.now().isoformat()
        )

        record.id = self.db.save_execution(record)

        return {
            "id": record.id,
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "execution_time": result.execution_time,
            "exit_code": result.exit_code,
        }

    def get_execution(self, execution_id: int) -> Optional[Dict]:
        """获取执行记录"""
        return self.db.get_execution(execution_id)

    def get_session_executions(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """获取会话执行记录"""
        return self.db.get_session_executions(session_id, limit)

    def get_user_executions(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Dict]:
        """获取用户执行记录"""
        return self.db.get_user_executions(user_id, limit)

    def get_stats(self, user_id: Optional[int] = None) -> Dict:
        """获取执行统计"""
        return self.db.get_stats(user_id)

    def get_supported_languages(self) -> List[Dict]:
        """获取支持的语言列表"""
        return [
            {
                "name": "Python",
                "value": "python",
                "version": "3.x",
                "description": "Python 3.x 解释器"
            },
            {
                "name": "JavaScript",
                "value": "javascript",
                "version": "ES2020+",
                "description": "Node.js 运行时"
            },
            {
                "name": "TypeScript",
                "value": "typescript",
                "version": "4.x",
                "description": "TypeScript 编译执行"
            }
        ]

    def validate_code(self, code: str, language: str = "python") -> Dict:
        """验证代码"""
        lang = Language(language.lower())
        config = SandboxConfig(language=lang)
        sandbox = CodeSandbox(config)

        is_valid, error = sandbox.validate_code(code)

        return {
            "valid": is_valid,
            "error": error
        }


_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager() -> SandboxManager:
    """获取沙箱管理器单例"""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()
    return _sandbox_manager
