"""
资源限制模块
控制代码执行的 CPU、内存、时间限制
"""

import os
import time
import signal
import threading
import resource
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class LimitType(Enum):
    """限制类型"""
    CPU_TIME = "cpu_time"
    MEMORY = "memory"
    WALL_TIME = "wall_time"
    OUTPUT_SIZE = "output_size"


@dataclass
class ResourceLimits:
    """资源限制配置"""
    max_cpu_time: float = 5.0
    max_wall_time: float = 10.0
    max_memory_mb: int = 256
    max_output_size: int = 1024 * 1024
    max_file_size: int = 10 * 1024 * 1024
    max_processes: int = 1
    max_threads: int = 1
    allowed_imports: list = field(default_factory=lambda: [
        "math", "json", "re", "datetime", "collections", "itertools",
        "functools", "typing", "random", "string", "copy", "os.path",
        "hashlib", "base64", "urllib.parse", "decimal", "fractions"
    ])
    blocked_imports: list = field(default_factory=lambda: [
        "os.system", "subprocess", "socket", "requests",
        "http.client", "ftplib", "telnetlib", "smtplib",
        "poplib", "imaplib", "nntplib", "popen2",
        "commands", "pty", "fcntl", "pipes", "posixfile"
    ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_cpu_time": self.max_cpu_time,
            "max_wall_time": self.max_wall_time,
            "max_memory_mb": self.max_memory_mb,
            "max_output_size": self.max_output_size,
            "max_file_size": self.max_file_size,
            "max_processes": self.max_processes,
            "max_threads": self.max_threads,
        }

    @classmethod
    def default(cls) -> "ResourceLimits":
        return cls()

    @classmethod
    def strict(cls) -> "ResourceLimits":
        return cls(
            max_cpu_time=2.0,
            max_wall_time=5.0,
            max_memory_mb=128,
            max_output_size=256 * 1024,
            max_processes=1,
            max_threads=1,
        )

    @classmethod
    def relaxed(cls) -> "ResourceLimits":
        return cls(
            max_cpu_time=30.0,
            max_wall_time=60.0,
            max_memory_mb=512,
            max_output_size=10 * 1024 * 1024,
            max_processes=4,
            max_threads=4,
        )


class LimitEnforcer:
    """资源限制执行器"""

    def __init__(self, limits: ResourceLimits):
        self.limits = limits
        self._start_time: Optional[float] = None
        self._timer: Optional[threading.Timer] = None
        self._violated: bool = False
        self._violation_type: Optional[str] = None

    def set_limits(self) -> None:
        """设置资源限制（仅 Unix 系统）"""
        try:
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (int(self.limits.max_cpu_time), int(self.limits.max_cpu_time) + 1)
            )
        except (ValueError, resource.error):
            pass

        try:
            memory_bytes = self.limits.max_memory_mb * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_AS,
                (memory_bytes, memory_bytes)
            )
        except (ValueError, resource.error):
            pass

        try:
            resource.setrlimit(
                resource.RLIMIT_NPROC,
                (self.limits.max_processes, self.limits.max_processes)
            )
        except (ValueError, resource.error):
            pass

    def start_timer(self, callback: callable) -> None:
        """启动超时计时器"""
        self._start_time = time.time()
        self._violated = False
        self._violation_type = None

        def timeout_handler():
            self._violated = True
            self._violation_type = "wall_time"
            callback()

        self._timer = threading.Timer(self.limits.max_wall_time, timeout_handler)
        self._timer.daemon = True
        self._timer.start()

    def stop_timer(self) -> None:
        """停止计时器"""
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def check_memory(self) -> bool:
        """检查内存使用"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / (1024 * 1024)
            if memory_mb > self.limits.max_memory_mb:
                self._violated = True
                self._violation_type = "memory"
                return False
        except ImportError:
            pass
        return True

    def get_elapsed_time(self) -> float:
        """获取已执行时间"""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def is_violated(self) -> bool:
        """是否违反限制"""
        return self._violated

    def get_violation_type(self) -> Optional[str]:
        """获取违反类型"""
        return self._violation_type

    def cleanup(self) -> None:
        """清理资源"""
        self.stop_timer()


class TimeoutException(Exception):
    """超时异常"""
    pass


class MemoryLimitException(Exception):
    """内存限制异常"""
    pass


class OutputLimitException(Exception):
    """输出限制异常"""
    pass
