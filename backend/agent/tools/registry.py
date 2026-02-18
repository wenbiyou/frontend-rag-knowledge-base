"""
工具注册中心
管理和调度各种工具
"""

from typing import Dict, List, Any, Optional
import json

from agent.tools.base import BaseTool, ToolResult
from agent.tools.search import KnowledgeSearchTool, WebSearchTool, CodeSearchTool
from agent.tools.calculator import CalculatorTool, StatisticsTool, DataAnalysisTool
from agent.tools.api_caller import APICallTool, JSONParserTool, URLBuilderTool
from agent.tools.file_ops import FileReadTool, FileWriteTool, DirectoryListTool, JSONFileTool


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """注册默认工具"""
        self.register(KnowledgeSearchTool())
        self.register(WebSearchTool())
        self.register(CodeSearchTool())
        self.register(CalculatorTool())
        self.register(StatisticsTool())
        self.register(DataAnalysisTool())
        self.register(APICallTool())
        self.register(JSONParserTool())
        self.register(URLBuilderTool())
        self.register(FileReadTool())
        self.register(FileWriteTool())
        self.register(DirectoryListTool())
        self.register(JSONFileTool())

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具"""
        return [tool.get_schema() for tool in self._tools.values()]

    def list_tools_by_category(self) -> Dict[str, List[Dict]]:
        """按类别列出工具"""
        categories = {
            "search": [],
            "calculation": [],
            "api": [],
            "file": [],
        }

        search_tools = {"knowledge_search", "web_search", "code_search"}
        calc_tools = {"calculator", "statistics", "data_analysis"}
        api_tools = {"api_call", "json_parser", "url_builder"}
        file_tools = {"file_read", "file_write", "directory_list", "json_file"}

        for name, tool in self._tools.items():
            schema = tool.get_schema()
            if name in search_tools:
                categories["search"].append(schema)
            elif name in calc_tools:
                categories["calculation"].append(schema)
            elif name in api_tools:
                categories["api"].append(schema)
            elif name in file_tools:
                categories["file"].append(schema)

        return categories

    def execute(self, name: str, **kwargs) -> ToolResult:
        """执行工具"""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"工具 '{name}' 不存在"
            )
        return tool.execute(**kwargs)

    def has_tool(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools

    def get_tool_schemas_for_llm(self) -> List[Dict]:
        """获取用于 LLM 的工具 Schema（OpenAI Function Calling 格式）"""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        return schemas


_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取工具注册中心单例"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
