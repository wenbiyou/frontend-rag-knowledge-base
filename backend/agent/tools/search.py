"""
搜索工具
提供知识库检索和网络搜索能力
"""

import json
from typing import Dict, Any, List, Optional

from agent.tools.base import BaseTool, ToolResult


class KnowledgeSearchTool(BaseTool):
    """知识库搜索工具"""

    name = "knowledge_search"
    description = "在知识库中搜索相关信息"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询"
            },
            "top_k": {
                "type": "integer",
                "description": "返回结果数量",
                "default": 5
            },
            "source_filter": {
                "type": "string",
                "description": "来源过滤"
            }
        },
        "required": ["query"]
    }

    def execute(self, **kwargs) -> ToolResult:
        """执行知识库搜索"""
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 5)
        source_filter = kwargs.get("source_filter")

        if not query:
            return ToolResult(
                success=False,
                output=None,
                error="查询不能为空"
            )

        try:
            from core.rag_engine import get_rag_engine

            rag_engine = get_rag_engine()
            docs, metas = rag_engine._retrieve(query, source_filter, top_k)

            results = []
            for doc, meta in zip(docs, metas):
                results.append({
                    "content": doc[:500] + "..." if len(doc) > 500 else doc,
                    "title": meta.get("title", ""),
                    "source": meta.get("source", ""),
                    "source_type": meta.get("source_type", ""),
                })

            return ToolResult(
                success=True,
                output={
                    "query": query,
                    "results": results,
                    "total": len(results)
                },
                metadata={"source_filter": source_filter}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"搜索失败: {str(e)}"
            )


class WebSearchTool(BaseTool):
    """网络搜索工具"""

    name = "web_search"
    description = "在网络上搜索信息（需要配置搜索API）"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询"
            },
            "num_results": {
                "type": "integer",
                "description": "返回结果数量",
                "default": 5
            }
        },
        "required": ["query"]
    }

    def execute(self, **kwargs) -> ToolResult:
        """执行网络搜索"""
        query = kwargs.get("query", "")
        num_results = kwargs.get("num_results", 5)

        if not query:
            return ToolResult(
                success=False,
                output=None,
                error="查询不能为空"
            )

        try:
            import requests

            search_url = f"https://api.duckduckgo.com/?q={query}&format=json&limit={num_results}"
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()

            data = response.json()

            results = []
            if "RelatedTopics" in data:
                for topic in data["RelatedTopics"][:num_results]:
                    if "Text" in topic and "FirstURL" in topic:
                        results.append({
                            "title": topic.get("Text", "")[:100],
                            "url": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", "")
                        })

            return ToolResult(
                success=True,
                output={
                    "query": query,
                    "results": results,
                    "total": len(results)
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
                error=f"网络搜索失败: {str(e)}"
            )


class CodeSearchTool(BaseTool):
    """代码搜索工具"""

    name = "code_search"
    description = "在代码库中搜索代码片段"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询"
            },
            "language": {
                "type": "string",
                "description": "编程语言过滤"
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量",
                "default": 10
            }
        },
        "required": ["query"]
    }

    def execute(self, **kwargs) -> ToolResult:
        """执行代码搜索"""
        query = kwargs.get("query", "")
        language = kwargs.get("language")
        limit = kwargs.get("limit", 10)

        if not query:
            return ToolResult(
                success=False,
                output=None,
                error="查询不能为空"
            )

        try:
            from admin.code_analyzer import get_code_analyzer

            analyzer = get_code_analyzer()
            results = analyzer.search_snippets(query, limit)

            if language:
                results = [r for r in results if r.get("language") == language]

            return ToolResult(
                success=True,
                output={
                    "query": query,
                    "results": results,
                    "total": len(results)
                },
                metadata={"language": language}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"代码搜索失败: {str(e)}"
            )
