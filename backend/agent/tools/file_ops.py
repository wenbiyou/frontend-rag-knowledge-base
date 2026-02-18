"""
文件操作工具
提供安全的文件读写能力
"""

import os
import json
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path

from agent.tools.base import BaseTool, ToolResult


class FileReadTool(BaseTool):
    """文件读取工具"""

    name = "file_read"
    description = "读取文件内容"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径"
            },
            "encoding": {
                "type": "string",
                "description": "文件编码",
                "default": "utf-8"
            },
            "start_line": {
                "type": "integer",
                "description": "起始行号"
            },
            "end_line": {
                "type": "integer",
                "description": "结束行号"
            }
        },
        "required": ["file_path"]
    }

    MAX_FILE_SIZE = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = [".txt", ".md", ".json", ".csv", ".xml", ".yaml", ".yml", ".log", ".py", ".js", ".ts", ".html", ".css"]

    def execute(self, **kwargs) -> ToolResult:
        """读取文件"""
        file_path = kwargs.get("file_path", "")
        encoding = kwargs.get("encoding", "utf-8")
        start_line = kwargs.get("start_line")
        end_line = kwargs.get("end_line")

        if not file_path:
            return ToolResult(
                success=False,
                output=None,
                error="文件路径不能为空"
            )

        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"文件不存在: {file_path}"
                )

            if path.stat().st_size > self.MAX_FILE_SIZE:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"文件过大（超过 {self.MAX_FILE_SIZE // (1024*1024)} MB）"
                )

            with open(path, "r", encoding=encoding) as f:
                lines = f.readlines()

            if start_line is not None or end_line is not None:
                start = (start_line or 1) - 1
                end = end_line or len(lines)
                lines = lines[start:end]

            content = "".join(lines)

            return ToolResult(
                success=True,
                output={
                    "content": content,
                    "line_count": len(lines),
                    "file_size": path.stat().st_size,
                    "file_path": str(path.absolute())
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"读取文件失败: {str(e)}"
            )


class FileWriteTool(BaseTool):
    """文件写入工具"""

    name = "file_write"
    description = "写入文件内容"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径"
            },
            "content": {
                "type": "string",
                "description": "文件内容"
            },
            "mode": {
                "type": "string",
                "enum": ["write", "append"],
                "description": "写入模式",
                "default": "write"
            },
            "encoding": {
                "type": "string",
                "description": "文件编码",
                "default": "utf-8"
            }
        },
        "required": ["file_path", "content"]
    }

    def __init__(self, sandbox_dir: str = None):
        self.sandbox_dir = sandbox_dir or tempfile.gettempdir()

    def execute(self, **kwargs) -> ToolResult:
        """写入文件"""
        file_path = kwargs.get("file_path", "")
        content = kwargs.get("content", "")
        mode = kwargs.get("mode", "write")
        encoding = kwargs.get("encoding", "utf-8")

        if not file_path:
            return ToolResult(
                success=False,
                output=None,
                error="文件路径不能为空"
            )

        try:
            path = Path(self.sandbox_dir) / file_path.lstrip("/")

            path.parent.mkdir(parents=True, exist_ok=True)

            write_mode = "w" if mode == "write" else "a"

            with open(path, write_mode, encoding=encoding) as f:
                f.write(content)

            return ToolResult(
                success=True,
                output={
                    "file_path": str(path.absolute()),
                    "bytes_written": len(content.encode(encoding)),
                    "mode": mode
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"写入文件失败: {str(e)}"
            )


class DirectoryListTool(BaseTool):
    """目录列表工具"""

    name = "directory_list"
    description = "列出目录内容"
    parameters = {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "目录路径"
            },
            "pattern": {
                "type": "string",
                "description": "文件匹配模式（glob）"
            },
            "recursive": {
                "type": "boolean",
                "description": "是否递归",
                "default": False
            }
        },
        "required": ["directory"]
    }

    def execute(self, **kwargs) -> ToolResult:
        """列出目录"""
        directory = kwargs.get("directory", "")
        pattern = kwargs.get("pattern", "*")
        recursive = kwargs.get("recursive", False)

        if not directory:
            return ToolResult(
                success=False,
                output=None,
                error="目录路径不能为空"
            )

        try:
            path = Path(directory)

            if not path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"目录不存在: {directory}"
                )

            if not path.is_dir():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"不是目录: {directory}"
                )

            if recursive:
                items = list(path.rglob(pattern))
            else:
                items = list(path.glob(pattern))

            files = []
            dirs = []

            for item in items:
                item_info = {
                    "name": item.name,
                    "path": str(item),
                    "size": item.stat().st_size if item.is_file() else None,
                }
                if item.is_file():
                    files.append(item_info)
                elif item.is_dir():
                    dirs.append(item_info)

            return ToolResult(
                success=True,
                output={
                    "directory": str(path.absolute()),
                    "files": files,
                    "directories": dirs,
                    "total_files": len(files),
                    "total_dirs": len(dirs)
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"列出目录失败: {str(e)}"
            )


class JSONFileTool(BaseTool):
    """JSON 文件操作工具"""

    name = "json_file"
    description = "读取或写入 JSON 文件"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径"
            },
            "operation": {
                "type": "string",
                "enum": ["read", "write"],
                "description": "操作类型"
            },
            "data": {
                "type": "object",
                "description": "要写入的数据（仅 write 操作需要）"
            }
        },
        "required": ["file_path", "operation"]
    }

    def __init__(self, sandbox_dir: str = None):
        self.sandbox_dir = sandbox_dir or tempfile.gettempdir()

    def execute(self, **kwargs) -> ToolResult:
        """执行 JSON 文件操作"""
        file_path = kwargs.get("file_path", "")
        operation = kwargs.get("operation", "read")
        data = kwargs.get("data")

        if not file_path:
            return ToolResult(
                success=False,
                output=None,
                error="文件路径不能为空"
            )

        try:
            if operation == "read":
                path = Path(file_path)
                if not path.exists():
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"文件不存在: {file_path}"
                    )

                with open(path, "r", encoding="utf-8") as f:
                    result = json.load(f)

                return ToolResult(
                    success=True,
                    output={
                        "data": result,
                        "file_path": str(path.absolute())
                    }
                )

            elif operation == "write":
                if data is None:
                    return ToolResult(
                        success=False,
                        output=None,
                        error="写入操作需要提供数据"
                    )

                path = Path(self.sandbox_dir) / file_path.lstrip("/")
                path.parent.mkdir(parents=True, exist_ok=True)

                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                return ToolResult(
                    success=True,
                    output={
                        "file_path": str(path.absolute()),
                        "bytes_written": path.stat().st_size
                    }
                )

        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"JSON 解析错误: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"操作失败: {str(e)}"
            )
