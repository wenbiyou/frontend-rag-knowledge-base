"""
API 调用工具
提供调用外部 API 的能力
"""

import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

from agent.tools.base import BaseTool, ToolResult


class APICallTool(BaseTool):
    """API 调用工具"""

    name = "api_call"
    description = "调用外部 REST API"
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "API URL"
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "description": "HTTP 方法",
                "default": "GET"
            },
            "headers": {
                "type": "object",
                "description": "请求头"
            },
            "params": {
                "type": "object",
                "description": "查询参数"
            },
            "body": {
                "type": "object",
                "description": "请求体"
            },
            "timeout": {
                "type": "integer",
                "description": "超时时间（秒）",
                "default": 30
            }
        },
        "required": ["url"]
    }

    BLOCKED_DOMAINS = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "internal.",
        "private.",
    ]

    def execute(self, **kwargs) -> ToolResult:
        """执行 API 调用"""
        url = kwargs.get("url", "")
        method = kwargs.get("method", "GET").upper()
        headers = kwargs.get("headers", {})
        params = kwargs.get("params")
        body = kwargs.get("body")
        timeout = kwargs.get("timeout", 30)

        if not url:
            return ToolResult(
                success=False,
                output=None,
                error="URL 不能为空"
            )

        for blocked in self.BLOCKED_DOMAINS:
            if blocked in url:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"禁止访问的域名: {blocked}"
                )

        try:
            import requests

            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=body if body else None,
                timeout=timeout
            )

            try:
                response_data = response.json()
            except:
                response_data = response.text

            return ToolResult(
                success=response.status_code < 400,
                output={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "data": response_data
                },
                metadata={
                    "url": url,
                    "method": method
                }
            )

        except ImportError:
            return ToolResult(
                success=False,
                output=None,
                error="需要安装 requests 库"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"API 调用失败: {str(e)}"
            )


class JSONParserTool(BaseTool):
    """JSON 解析工具"""

    name = "json_parser"
    description = "解析和处理 JSON 数据"
    parameters = {
        "type": "object",
        "properties": {
            "json_string": {
                "type": "string",
                "description": "JSON 字符串"
            },
            "path": {
                "type": "string",
                "description": "JSON 路径，如 'data.items[0].name'"
            }
        },
        "required": ["json_string"]
    }

    def execute(self, **kwargs) -> ToolResult:
        """执行 JSON 解析"""
        json_string = kwargs.get("json_string", "")
        path = kwargs.get("path")

        if not json_string:
            return ToolResult(
                success=False,
                output=None,
                error="JSON 字符串不能为空"
            )

        try:
            data = json.loads(json_string)

            if path:
                result = self._get_by_path(data, path)
            else:
                result = data

            return ToolResult(
                success=True,
                output={
                    "data": result,
                    "path": path
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
                error=f"处理错误: {str(e)}"
            )

    def _get_by_path(self, data: Any, path: str) -> Any:
        """通过路径获取数据"""
        parts = path.replace("]", "").replace("[", ".").split(".")
        result = data

        for part in parts:
            if not part:
                continue
            if part.isdigit():
                result = result[int(part)]
            else:
                result = result[part]

        return result


class URLBuilderTool(BaseTool):
    """URL 构建工具"""

    name = "url_builder"
    description = "构建 URL，支持参数拼接"
    parameters = {
        "type": "object",
        "properties": {
            "base_url": {
                "type": "string",
                "description": "基础 URL"
            },
            "path": {
                "type": "string",
                "description": "路径"
            },
            "params": {
                "type": "object",
                "description": "查询参数"
            }
        },
        "required": ["base_url"]
    }

    def execute(self, **kwargs) -> ToolResult:
        """构建 URL"""
        base_url = kwargs.get("base_url", "")
        path = kwargs.get("path", "")
        params = kwargs.get("params", {})

        if not base_url:
            return ToolResult(
                success=False,
                output=None,
                error="基础 URL 不能为空"
            )

        try:
            from urllib.parse import urljoin, urlencode, urlparse, urlunparse

            url = base_url
            if path:
                url = urljoin(base_url, path)

            if params:
                parsed = urlparse(url)
                query = urlencode(params)
                url = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    query,
                    parsed.fragment
                ))

            return ToolResult(
                success=True,
                output={
                    "url": url,
                    "base_url": base_url,
                    "path": path,
                    "params": params
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"URL 构建错误: {str(e)}"
            )
