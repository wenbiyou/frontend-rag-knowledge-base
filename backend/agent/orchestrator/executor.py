"""
任务执行器
负责执行子任务
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import traceback
from datetime import datetime

from agent.orchestrator.planner import SubTask, TaskType
from agent.tools import get_tool_registry
from agent.sandbox import SandboxExecutor, SandboxConfig
from agent.sandbox.sandbox import Language


@dataclass
class ExecutionResult:
    """执行结果"""
    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    tool_used: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "tool_used": self.tool_used,
        }


class TaskExecutor:
    """任务执行器"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.tool_registry = get_tool_registry()
        self.sandbox_executor = SandboxExecutor()

    def execute(self, subtask: SubTask) -> ExecutionResult:
        """
        执行单个子任务

        Args:
            subtask: 子任务

        Returns:
            执行结果
        """
        start_time = time.time()

        try:
            tool_name = subtask.parameters.get("tool", "")

            if tool_name == "sandbox":
                result = self._execute_sandbox(subtask)
            elif tool_name == "llm":
                result = self._execute_llm(subtask)
            elif tool_name and self.tool_registry.has_tool(tool_name):
                result = self._execute_tool(subtask, tool_name)
            else:
                result = self._execute_default(subtask)

            result.execution_time = time.time() - start_time
            return result

        except Exception as e:
            return ExecutionResult(
                task_id=subtask.id,
                success=False,
                error=f"{str(e)}\n{traceback.format_exc()}",
                execution_time=time.time() - start_time
            )

    def _execute_tool(self, subtask: SubTask, tool_name: str) -> ExecutionResult:
        """执行工具调用"""
        params = {k: v for k, v in subtask.parameters.items() if k != "tool"}

        result = self.tool_registry.execute(tool_name, **params)

        return ExecutionResult(
            task_id=subtask.id,
            success=result.success,
            output=result.output,
            error=result.error,
            tool_used=tool_name
        )

    def _execute_sandbox(self, subtask: SubTask) -> ExecutionResult:
        """执行沙箱代码"""
        code = subtask.parameters.get("code", "")
        language = subtask.parameters.get("language", "python")

        if not code:
            return ExecutionResult(
                task_id=subtask.id,
                success=False,
                error="没有提供要执行的代码"
            )

        lang = Language.PYTHON
        if language.lower() == "javascript":
            lang = Language.JAVASCRIPT
        elif language.lower() == "typescript":
            lang = Language.TYPESCRIPT

        result = self.sandbox_executor.execute(code, lang)

        return ExecutionResult(
            task_id=subtask.id,
            success=result.success,
            output=result.output,
            error=result.error,
            tool_used="sandbox"
        )

    def _execute_llm(self, subtask: SubTask) -> ExecutionResult:
        """执行 LLM 调用（占位实现）"""
        return ExecutionResult(
            task_id=subtask.id,
            success=True,
            output={"message": "LLM 调用需要配置 AI 客户端"},
            tool_used="llm"
        )

    def _execute_default(self, subtask: SubTask) -> ExecutionResult:
        """默认执行方式"""
        query = subtask.parameters.get("query", subtask.description)

        if self.tool_registry.has_tool("knowledge_search"):
            result = self.tool_registry.execute("knowledge_search", query=query)
            return ExecutionResult(
                task_id=subtask.id,
                success=result.success,
                output=result.output,
                error=result.error,
                tool_used="knowledge_search"
            )

        return ExecutionResult(
            task_id=subtask.id,
            success=False,
            error="没有可用的执行工具"
        )

    def execute_parallel(
        self,
        subtasks: List[SubTask],
        max_concurrent: int = 4
    ) -> List[ExecutionResult]:
        """
        并行执行多个子任务

        Args:
            subtasks: 子任务列表
            max_concurrent: 最大并发数

        Returns:
            执行结果列表
        """
        results = []

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            future_to_task = {
                executor.submit(self.execute, task): task
                for task in subtasks
            }

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(ExecutionResult(
                        task_id=task.id,
                        success=False,
                        error=str(e)
                    ))

        return results

    def execute_sequential(
        self,
        subtasks: List[SubTask]
    ) -> List[ExecutionResult]:
        """
        顺序执行多个子任务

        Args:
            subtasks: 子任务列表

        Returns:
            执行结果列表
        """
        results = []
        for task in subtasks:
            result = self.execute(task)
            results.append(result)
        return results

    def execute_with_dependencies(
        self,
        subtasks: List[SubTask],
        execution_order: List[List[SubTask]]
    ) -> Dict[str, ExecutionResult]:
        """
        按依赖关系执行任务

        Args:
            subtasks: 子任务列表
            execution_order: 执行顺序

        Returns:
            任务 ID 到结果的映射
        """
        results = {}

        for batch in execution_order:
            batch_results = self.execute_parallel(batch)
            for result in batch_results:
                results[result.task_id] = result

        return results


def get_task_executor() -> TaskExecutor:
    """获取任务执行器实例"""
    return TaskExecutor()
