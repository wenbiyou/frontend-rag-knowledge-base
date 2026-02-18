"""
结果聚合器
负责聚合多个子任务的结果
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from agent.orchestrator.planner import SubTask, TaskType
from agent.orchestrator.executor import ExecutionResult


@dataclass
class AggregatedResult:
    """聚合结果"""
    query: str
    success: bool
    answer: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    subtask_results: List[Dict[str, Any]] = field(default_factory=list)
    total_execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "success": self.success,
            "answer": self.answer,
            "sources": self.sources,
            "subtask_results": self.subtask_results,
            "total_execution_time": self.total_execution_time,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ResultAggregator:
    """结果聚合器"""

    def __init__(self):
        pass

    def aggregate(
        self,
        query: str,
        subtasks: List[SubTask],
        results: Dict[str, ExecutionResult]
    ) -> AggregatedResult:
        """
        聚合多个子任务的结果

        Args:
            query: 原始查询
            subtasks: 子任务列表
            results: 执行结果映射

        Returns:
            聚合结果
        """
        total_time = sum(r.execution_time for r in results.values())

        successful_results = [
            (task, results[task.id])
            for task in subtasks
            if task.id in results and results[task.id].success
        ]

        failed_results = [
            (task, results[task.id])
            for task in subtasks
            if task.id in results and not results[task.id].success
        ]

        sources = self._extract_sources(successful_results)

        answer = self._generate_answer(query, successful_results, failed_results)

        subtask_results = [
            {
                "task_id": task.id,
                "task_name": task.name,
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "execution_time": result.execution_time,
            }
            for task, result in [(t, results.get(t.id)) for t in subtasks]
            if result is not None
        ]

        return AggregatedResult(
            query=query,
            success=len(failed_results) == 0,
            answer=answer,
            sources=sources,
            subtask_results=subtask_results,
            total_execution_time=total_time,
            metadata={
                "total_subtasks": len(subtasks),
                "successful_subtasks": len(successful_results),
                "failed_subtasks": len(failed_results),
            }
        )

    def _extract_sources(
        self,
        results: List[tuple]
    ) -> List[Dict[str, Any]]:
        """提取来源信息"""
        sources = []

        for task, result in results:
            if not result.output:
                continue

            if isinstance(result.output, dict):
                if "results" in result.output:
                    for item in result.output.get("results", []):
                        if isinstance(item, dict):
                            sources.append({
                                "title": item.get("title", ""),
                                "source": item.get("source", ""),
                                "content": item.get("content", item.get("snippet", ""))[:200],
                                "task_id": task.id,
                            })

        return sources[:10]

    def _generate_answer(
        self,
        query: str,
        successful_results: List[tuple],
        failed_results: List[tuple]
    ) -> str:
        """生成最终答案"""
        if not successful_results and not failed_results:
            return "抱歉，无法处理您的请求。"

        parts = []

        for task, result in successful_results:
            if result.output:
                if isinstance(result.output, dict):
                    if "result" in result.output:
                        parts.append(f"**{task.name}**: {result.output['result']}")
                    elif "statistics" in result.output:
                        stats = result.output["statistics"]
                        parts.append(f"**{task.name}**: {json.dumps(stats, ensure_ascii=False)}")
                    elif "results" in result.output:
                        items = result.output["results"]
                        if items:
                            parts.append(f"**{task.name}**: 找到 {len(items)} 条相关结果")
                    else:
                        parts.append(f"**{task.name}**: 已完成")
                elif isinstance(result.output, str):
                    parts.append(f"**{task.name}**: {result.output[:500]}")

        if failed_results:
            failed_names = [task.name for task, _ in failed_results]
            parts.append(f"\n以下任务执行失败: {', '.join(failed_names)}")

        if parts:
            return "\n\n".join(parts)
        else:
            return "任务已完成，但没有生成有效结果。"

    def aggregate_simple(
        self,
        query: str,
        results: List[ExecutionResult]
    ) -> AggregatedResult:
        """
        简单聚合（无子任务信息）

        Args:
            query: 查询
            results: 执行结果列表

        Returns:
            聚合结果
        """
        total_time = sum(r.execution_time for r in results)

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        answer_parts = []
        for result in successful:
            if result.output:
                if isinstance(result.output, dict):
                    if "result" in result.output:
                        answer_parts.append(str(result.output["result"]))
                    elif "output" in result.output:
                        answer_parts.append(str(result.output["output"]))
                else:
                    answer_parts.append(str(result.output))

        answer = "\n".join(answer_parts) if answer_parts else "执行完成"

        return AggregatedResult(
            query=query,
            success=len(failed) == 0,
            answer=answer,
            subtask_results=[r.to_dict() for r in results],
            total_execution_time=total_time,
        )


def get_result_aggregator() -> ResultAggregator:
    """获取结果聚合器实例"""
    return ResultAggregator()
