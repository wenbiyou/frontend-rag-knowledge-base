"""
工具基类定义
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseTool(ABC):
    """工具基类"""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """获取工具 Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
