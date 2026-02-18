"""
Agent 编排器
协调多个 Agent 完成复杂任务
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import uuid
from datetime import datetime


@dataclass
class Task:
    """任务定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    subtasks: List["Task"] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class AgentContext:
    """Agent 上下文"""
    session_id: str = ""
    user_id: Optional[int] = None
    conversation_history: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentOrchestrator:
    """Agent 编排器"""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._context: Optional[AgentContext] = None

    def create_task(
        self,
        name: str,
        description: str = ""
    ) -> Task:
        """创建任务"""
        task = Task(name=name, description=description)
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: str = None,
        result: Any = None,
        error: str = None
    ) -> Optional[Task]:
        """更新任务"""
        task = self.get_task(task_id)
        if not task:
            return None

        if status:
            task.status = status
        if result is not None:
            task.result = result
        if error:
            task.error = error

        if status in ("completed", "failed"):
            task.completed_at = datetime.now().isoformat()

        return task

    def decompose_task(self, task: Task) -> List[Task]:
        """分解任务（占位实现）"""
        return []

    def aggregate_results(self, tasks: List[Task]) -> Any:
        """聚合结果"""
        results = []
        for task in tasks:
            if task.status == "completed" and task.result is not None:
                results.append(task.result)
        return results

    def set_context(self, context: AgentContext) -> None:
        """设置上下文"""
        self._context = context

    def get_context(self) -> Optional[AgentContext]:
        """获取上下文"""
        return self._context


_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """获取编排器单例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
