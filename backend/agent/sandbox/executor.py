"""
沙箱代码执行器
执行代码并返回结果
"""

import os
import sys
import json
import time
import signal
import threading
import subprocess
import traceback
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import tempfile

from agent.sandbox.sandbox import CodeSandbox, SandboxConfig, Language
from agent.sandbox.limits import (
    ResourceLimits,
    LimitEnforcer,
    TimeoutException,
    MemoryLimitException,
    OutputLimitException
)


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: str
    error: Optional[str] = None
    return_value: Any = None
    execution_time: float = 0.0
    memory_used: int = 0
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "return_value": self.return_value,
            "execution_time": self.execution_time,
            "memory_used": self.memory_used,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class OutputCapture:
    """输出捕获器"""

    def __init__(self, max_size: int = 1024 * 1024):
        self.max_size = max_size
        self._output = []
        self._size = 0
        self._truncated = False

    def write(self, text: str) -> None:
        if self._truncated:
            return

        if self._size + len(text) > self.max_size:
            remaining = self.max_size - self._size
            if remaining > 0:
                self._output.append(text[:remaining])
            self._truncated = True
            return

        self._output.append(text)
        self._size += len(text)

    def get_output(self) -> str:
        result = "".join(self._output)
        if self._truncated:
            result += "\n... [输出被截断]"
        return result

    def clear(self) -> None:
        self._output = []
        self._size = 0
        self._truncated = False


class SandboxExecutor:
    """沙箱执行器"""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self.sandbox = CodeSandbox(self.config)

    def execute(
        self,
        code: str,
        language: Optional[Language] = None,
        timeout: Optional[float] = None,
        input_data: Optional[str] = None
    ) -> ExecutionResult:
        """
        执行代码

        Args:
            code: 要执行的代码
            language: 编程语言
            timeout: 超时时间
            input_data: 输入数据

        Returns:
            ExecutionResult: 执行结果
        """
        if language:
            self.config.language = language

        effective_timeout = timeout or self.config.timeout

        is_valid, error_msg = self.sandbox.validate_code(code)
        if not is_valid:
            return ExecutionResult(
                success=False,
                output="",
                error=f"代码验证失败: {error_msg}",
                exit_code=-1
            )

        start_time = time.time()

        try:
            result = self._execute_in_subprocess(code, effective_timeout, input_data)
            result.execution_time = time.time() - start_time
            return result

        except TimeoutException:
            return ExecutionResult(
                success=False,
                output="",
                error=f"执行超时（超过 {effective_timeout} 秒）",
                execution_time=time.time() - start_time,
                exit_code=-1
            )
        except MemoryLimitException:
            return ExecutionResult(
                success=False,
                output="",
                error=f"内存超限（超过 {self.config.limits.max_memory_mb} MB）",
                execution_time=time.time() - start_time,
                exit_code=-1
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"执行错误: {str(e)}\n{traceback.format_exc()}",
                execution_time=time.time() - start_time,
                exit_code=-1
            )

    def _execute_in_subprocess(
        self,
        code: str,
        timeout: float,
        input_data: Optional[str]
    ) -> ExecutionResult:
        """在子进程中执行代码"""

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=self._get_file_suffix(),
            delete=False
        ) as f:
            f.write(code)
            code_path = f.name

        try:
            env = os.environ.copy()
            env.update(self.config.env_vars)
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            cmd = self._get_execution_command(code_path)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if input_data else subprocess.DEVNULL,
                env=env,
                cwd=self.sandbox._temp_dir if self.sandbox._temp_dir else None,
                preexec_fn=self._set_process_limits if os.name != 'nt' else None
            )

            try:
                stdout, stderr = process.communicate(
                    input=input_data.encode() if input_data else None,
                    timeout=timeout
                )
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise TimeoutException(f"执行超时（超过 {timeout} 秒）")

            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            success = process.returncode == 0 and not stderr_str

            return ExecutionResult(
                success=success,
                output=stdout_str,
                error=stderr_str if stderr_str else None,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=process.returncode
            )

        finally:
            try:
                os.unlink(code_path)
            except OSError:
                pass

    def _get_file_suffix(self) -> str:
        """获取代码文件后缀"""
        suffixes = {
            Language.PYTHON: ".py",
            Language.JAVASCRIPT: ".js",
            Language.TYPESCRIPT: ".ts",
        }
        return suffixes.get(self.config.language, ".txt")

    def _get_execution_command(self, code_path: str) -> List[str]:
        """获取执行命令"""
        if self.config.language == Language.PYTHON:
            return [sys.executable, "-u", code_path]
        elif self.config.language == Language.JAVASCRIPT:
            return ["node", code_path]
        elif self.config.language == Language.TYPESCRIPT:
            return ["npx", "ts-node", code_path]
        return []

    def _set_process_limits(self) -> None:
        """设置进程资源限制（仅 Unix）"""
        import resource

        try:
            resource.setrlimit(
                resource.RLIMIT_AS,
                (self.config.limits.max_memory_mb * 1024 * 1024, 
                 self.config.limits.max_memory_mb * 1024 * 1024)
            )
        except (ValueError, resource.error):
            pass

        try:
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (int(self.config.limits.max_cpu_time), 
                 int(self.config.limits.max_cpu_time) + 1)
            )
        except (ValueError, resource.error):
            pass

        try:
            resource.setrlimit(
                resource.RLIMIT_NPROC,
                (self.config.limits.max_processes, 
                 self.config.limits.max_processes)
            )
        except (ValueError, resource.error):
            pass

    def execute_python(
        self,
        code: str,
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """执行 Python 代码"""
        return self.execute(code, Language.PYTHON, timeout)

    def execute_javascript(
        self,
        code: str,
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """执行 JavaScript 代码"""
        return self.execute(code, Language.JAVASCRIPT, timeout)

    def execute_typescript(
        self,
        code: str,
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """执行 TypeScript 代码"""
        return self.execute(code, Language.TYPESCRIPT, timeout)

    def execute_with_context(
        self,
        code: str,
        context: Dict[str, Any],
        language: Language = Language.PYTHON
    ) -> ExecutionResult:
        """带上下文执行代码"""
        if language == Language.PYTHON:
            context_code = self._build_python_context(context)
            full_code = context_code + "\n" + code
        else:
            full_code = code

        return self.execute(full_code, language)

    def _build_python_context(self, context: Dict[str, Any]) -> str:
        """构建 Python 上下文代码"""
        lines = []
        for key, value in context.items():
            if isinstance(value, str):
                lines.append(f'{key} = """{value}"""')
            elif isinstance(value, (dict, list)):
                lines.append(f'{key} = {json.dumps(value)}')
            else:
                lines.append(f'{key} = {value}')
        return "\n".join(lines)


def get_executor(
    language: Language = Language.PYTHON,
    limits: Optional[ResourceLimits] = None
) -> SandboxExecutor:
    """获取执行器实例"""
    config = SandboxConfig(language=language)
    if limits:
        config.limits = limits
    return SandboxExecutor(config)
