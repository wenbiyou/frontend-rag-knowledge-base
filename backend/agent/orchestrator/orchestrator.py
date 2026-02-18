"""
Agent 编排器
协调多个 Agent 完成复杂任务
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import uuid
from datetime import datetime

from agent.orchestrator.planner import TaskPlanner, SubTask, get_task_planner
from agent.orchestrator.executor import TaskExecutor, ExecutionResult, get_task_executor
from agent.orchestrator.aggregator import ResultAggregator, AggregatedResult, get_result_aggregator


@dataclass
class Task:
    """任务定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    subtasks: List[SubTask] = field(default_factory=list)
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
        self.planner = get_task_planner()
        self.executor = get_task_executor()
        self.aggregator = get_result_aggregator()

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

    def decompose_task(self, task: Task, query: str) -> List[SubTask]:
        """分解任务"""
        subtasks = self.planner.decompose_complex_task(query)
        task.subtasks = subtasks
        return subtasks

    def execute_task(
        self,
        query: str,
        auto_decompose: bool = True
    ) -> AggregatedResult:
        """
        执行任务

        Args:
            query: 用户查询
            auto_decompose: 是否自动分解

        Returns:
            聚合结果
        """
        task = self.create_task(
            name="User Query",
            description=query
        )
        task.status = "running"

        if auto_decompose:
            subtasks = self.planner.plan(query)
        else:
            subtasks = [SubTask(
                id=f"single_{task.id}",
                name="直接执行",
                description=query,
                task_type=self.planner._classify_task(query),
                parameters={"query": query}
            )]

        task.subtasks = subtasks

        execution_order = self.planner.get_execution_order(subtasks)

        results = self.executor.execute_with_dependencies(subtasks, execution_order)

        aggregated = self.aggregator.aggregate(query, subtasks, results)

        task.result = aggregated.to_dict()
        task.status = "completed" if aggregated.success else "partial"
        task.completed_at = datetime.now().isoformat()

        return aggregated

    def execute_parallel_tasks(
        self,
        queries: List[str]
    ) -> List[AggregatedResult]:
        """
        并行执行多个任务

        Args:
            queries: 查询列表

        Returns:
            结果列表
        """
        results = []

        for query in queries:
            result = self.execute_task(query)
            results.append(result)

        return results

    def set_context(self, context: AgentContext) -> None:
        """设置上下文"""
        self._context = context

    def get_context(self) -> Optional[AgentContext]:
        """获取上下文"""
        return self._context

    def get_task_history(self, limit: int = 10) -> List[Dict]:
        """获取任务历史"""
        tasks = sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )[:limit]
        return [t.to_dict() for t in tasks]

    def clear_history(self) -> None:
        """清空历史"""
        self._tasks.clear()


_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """获取编排器单例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
