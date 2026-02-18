"""
代码执行沙箱
提供安全隔离环境执行代码
"""

import os
import sys
import ast
import tempfile
import subprocess
import threading
import traceback
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from enum import Enum
import json

from agent.sandbox.limits import (
    ResourceLimits,
    LimitEnforcer,
    TimeoutException,
    MemoryLimitException,
    OutputLimitException
)


class Language(Enum):
    """支持的编程语言"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


@dataclass
class SandboxConfig:
    """沙箱配置"""
    language: Language = Language.PYTHON
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    working_dir: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    timeout: float = 10.0
    enable_network: bool = False
    enable_file_write: bool = False
    allowed_modules: List[str] = field(default_factory=list)
    blocked_modules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language.value,
            "limits": self.limits.to_dict(),
            "timeout": self.timeout,
            "enable_network": self.enable_network,
            "enable_file_write": self.enable_file_write,
        }


class CodeValidator:
    """代码安全验证器"""

    DANGEROUS_PATTERNS = [
        "import os",
        "import sys",
        "import subprocess",
        "import socket",
        "import requests",
        "__import__",
        "eval(",
        "exec(",
        "compile(",
        "open(",
        "file(",
        "input(",
        "raw_input(",
    ]

    ALLOWED_BUILTINS = {
        "abs", "all", "any", "bin", "bool", "chr", "complex",
        "dict", "divmod", "enumerate", "filter", "float", "format",
        "frozenset", "hex", "int", "isinstance", "issubclass",
        "iter", "len", "list", "map", "max", "min", "next",
        "oct", "ord", "pow", "print", "range", "repr", "reversed",
        "round", "set", "slice", "sorted", "str", "sum", "tuple",
        "type", "zip", "True", "False", "None",
    }

    def __init__(self, config: SandboxConfig):
        self.config = config

    def validate(self, code: str) -> Tuple[bool, Optional[str]]:
        """验证代码安全性"""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"语法错误: {e}"

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not self._is_module_allowed(alias.name):
                        return False, f"禁止导入模块: {alias.name}"

            elif isinstance(node, ast.ImportFrom):
                if node.module and not self._is_module_allowed(node.module):
                    return False, f"禁止导入模块: {node.module}"

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ("eval", "exec", "compile", "__import__"):
                        return False, f"禁止使用函数: {node.func.id}"

        return True, None

    def _is_module_allowed(self, module_name: str) -> bool:
        """检查模块是否被允许"""
        base_module = module_name.split(".")[0]

        if base_module in self.config.limits.blocked_imports:
            return False

        if self.config.limits.allowed_imports:
            return base_module in self.config.limits.allowed_imports

        return True


class CodeSandbox:
    """代码执行沙箱"""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self.validator = CodeValidator(self.config)
        self._temp_dir: Optional[str] = None

    def create_environment(self) -> str:
        """创建隔离执行环境"""
        self._temp_dir = tempfile.mkdtemp(prefix="sandbox_")

        env_dir = os.path.join(self._temp_dir, "workspace")
        os.makedirs(env_dir, exist_ok=True)

        return env_dir

    def cleanup(self) -> None:
        """清理执行环境"""
        if self._temp_dir and os.path.exists(self._temp_dir):
            import shutil
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None

    def prepare_code(self, code: str) -> str:
        """准备执行代码"""
        if self.config.language == Language.PYTHON:
            return self._prepare_python_code(code)
        elif self.config.language == Language.JAVASCRIPT:
            return self._prepare_javascript_code(code)
        elif self.config.language == Language.TYPESCRIPT:
            return self._prepare_typescript_code(code)
        return code

    def _prepare_python_code(self, code: str) -> str:
        """准备 Python 代码"""
        safe_builtins = {name: __builtins__.get(name) for name in self.validator.ALLOWED_BUILTINS}

        wrapper = f'''
__safe_builtins = {safe_builtins}
__builtins__ = __safe_builtins

{code}
'''
        return wrapper

    def _prepare_javascript_code(self, code: str) -> str:
        """准备 JavaScript 代码"""
        return code

    def _prepare_typescript_code(self, code: str) -> str:
        """准备 TypeScript 代码"""
        return code

    def validate_code(self, code: str) -> Tuple[bool, Optional[str]]:
        """验证代码"""
        return self.validator.validate(code)

    def get_execution_command(self, code_path: str) -> List[str]:
        """获取执行命令"""
        if self.config.language == Language.PYTHON:
            return [sys.executable, code_path]
        elif self.config.language == Language.JAVASCRIPT:
            return ["node", code_path]
        elif self.config.language == Language.TYPESCRIPT:
            return ["npx", "ts-node", code_path]
        return []

    def __enter__(self):
        self.create_environment()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
