"""
任务规划器
负责分解复杂任务为子任务
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from datetime import datetime


class TaskType(Enum):
    """任务类型"""
    SEARCH = "search"
    CALCULATION = "calculation"
    CODE = "code"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    UNKNOWN = "unknown"


class TaskPriority(Enum):
    """任务优先级"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class SubTask:
    """子任务"""
    id: str
    name: str
    description: str
    task_type: TaskType
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "parameters": self.parameters,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


class TaskPlanner:
    """任务规划器"""

    KEYWORDS = {
        TaskType.SEARCH: ["搜索", "查找", "找", "查询", "search", "find", "query", "检索"],
        TaskType.CALCULATION: ["计算", "求", "算", "统计", "calculate", "compute", "count", "sum"],
        TaskType.CODE: ["代码", "编写", "实现", "编程", "code", "write", "implement", "program"],
        TaskType.ANALYSIS: ["分析", "评估", "比较", "analyze", "evaluate", "compare"],
        TaskType.SYNTHESIS: ["总结", "综合", "概述", "summarize", "synthesize", "overview"],
    }

    def __init__(self):
        self._task_counter = 0

    def plan(self, query: str) -> List[SubTask]:
        """
        规划任务

        Args:
            query: 用户查询

        Returns:
            子任务列表
        """
        task_type = self._classify_task(query)

        if task_type == TaskType.SEARCH:
            return self._plan_search_task(query)
        elif task_type == TaskType.CALCULATION:
            return self._plan_calculation_task(query)
        elif task_type == TaskType.CODE:
            return self._plan_code_task(query)
        elif task_type == TaskType.ANALYSIS:
            return self._plan_analysis_task(query)
        elif task_type == TaskType.SYNTHESIS:
            return self._plan_synthesis_task(query)
        else:
            return self._plan_general_task(query)

    def _classify_task(self, query: str) -> TaskType:
        """分类任务类型"""
        query_lower = query.lower()

        scores = {}
        for task_type, keywords in self.KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            scores[task_type] = score

        max_score = max(scores.values())
        if max_score == 0:
            return TaskType.UNKNOWN

        for task_type, score in scores.items():
            if score == max_score:
                return task_type

        return TaskType.UNKNOWN

    def _generate_task_id(self) -> str:
        """生成任务 ID"""
        self._task_counter += 1
        return f"task_{self._task_counter}_{datetime.now().strftime('%H%M%S')}"

    def _plan_search_task(self, query: str) -> List[SubTask]:
        """规划搜索任务"""
        return [
            SubTask(
                id=self._generate_task_id(),
                name="知识库搜索",
                description=f"在知识库中搜索: {query}",
                task_type=TaskType.SEARCH,
                priority=TaskPriority.HIGH,
                parameters={"query": query, "tool": "knowledge_search"}
            )
        ]

    def _plan_calculation_task(self, query: str) -> List[SubTask]:
        """规划计算任务"""
        expression = self._extract_expression(query)

        return [
            SubTask(
                id=self._generate_task_id(),
                name="数学计算",
                description=f"执行计算: {expression or query}",
                task_type=TaskType.CALCULATION,
                priority=TaskPriority.HIGH,
                parameters={"expression": expression, "tool": "calculator"}
            )
        ]

    def _plan_code_task(self, query: str) -> List[SubTask]:
        """规划代码任务"""
        return [
            SubTask(
                id=self._generate_task_id(),
                name="代码搜索",
                description=f"搜索相关代码: {query}",
                task_type=TaskType.SEARCH,
                priority=TaskPriority.HIGH,
                parameters={"query": query, "tool": "code_search"}
            ),
            SubTask(
                id=self._generate_task_id(),
                name="代码执行",
                description="在沙箱中执行代码",
                task_type=TaskType.CODE,
                priority=TaskPriority.MEDIUM,
                dependencies=[],
                parameters={"tool": "sandbox"}
            )
        ]

    def _plan_analysis_task(self, query: str) -> List[SubTask]:
        """规划分析任务"""
        return [
            SubTask(
                id=self._generate_task_id(),
                name="数据收集",
                description=f"收集分析所需数据: {query}",
                task_type=TaskType.SEARCH,
                priority=TaskPriority.HIGH,
                parameters={"query": query, "tool": "knowledge_search"}
            ),
            SubTask(
                id=self._generate_task_id(),
                name="数据分析",
                description="分析收集的数据",
                task_type=TaskType.ANALYSIS,
                priority=TaskPriority.MEDIUM,
                parameters={"tool": "data_analysis"}
            )
        ]

    def _plan_synthesis_task(self, query: str) -> List[SubTask]:
        """规划综合任务"""
        return [
            SubTask(
                id=self._generate_task_id(),
                name="信息收集",
                description=f"收集相关信息: {query}",
                task_type=TaskType.SEARCH,
                priority=TaskPriority.HIGH,
                parameters={"query": query, "tool": "knowledge_search"}
            ),
            SubTask(
                id=self._generate_task_id(),
                name="信息综合",
                description="综合分析并生成总结",
                task_type=TaskType.SYNTHESIS,
                priority=TaskPriority.MEDIUM,
                parameters={"tool": "llm"}
            )
        ]

    def _plan_general_task(self, query: str) -> List[SubTask]:
        """规划通用任务"""
        return [
            SubTask(
                id=self._generate_task_id(),
                name="知识检索",
                description=f"检索相关知识: {query}",
                task_type=TaskType.SEARCH,
                priority=TaskPriority.HIGH,
                parameters={"query": query, "tool": "knowledge_search"}
            )
        ]

    def _extract_expression(self, query: str) -> str:
        """从查询中提取数学表达式"""
        math_funcs = ['sqrt', 'sin', 'cos', 'tan', 'log', 'log10', 'log2', 'exp', 'abs', 'floor', 'ceil', 'pow']
        
        for func in math_funcs:
            if func in query.lower():
                pattern = rf'{func}\([^)]+\)'
                matches = re.findall(pattern, query, re.IGNORECASE)
                if matches:
                    rest = re.sub(pattern, '', query)
                    numbers = re.findall(r'[\+\-\*\/\d\.\s\(\)]+', rest)
                    if numbers:
                        return matches[0] + ''.join(numbers).strip()
                    return matches[0]
        
        pattern = r'[\d\+\-\*\/\(\)\.\s\^]+'
        match = re.search(pattern, query)
        if match:
            return match.group().strip()

        return query

    def decompose_complex_task(
        self,
        query: str,
        max_subtasks: int = 5
    ) -> List[SubTask]:
        """
        分解复杂任务

        Args:
            query: 复杂查询
            max_subtasks: 最大子任务数

        Returns:
            子任务列表
        """
        subtasks = []

        sentences = re.split(r'[，。；,;]', query)
        sentences = [s.strip() for s in sentences if s.strip()]

        for i, sentence in enumerate(sentences[:max_subtasks]):
            task_type = self._classify_task(sentence)
            subtasks.append(SubTask(
                id=self._generate_task_id(),
                name=f"子任务 {i + 1}",
                description=sentence,
                task_type=task_type,
                priority=TaskPriority.HIGH if i == 0 else TaskPriority.MEDIUM,
                parameters={"query": sentence}
            ))

        if not subtasks:
            subtasks = self.plan(query)

        return subtasks

    def get_execution_order(self, subtasks: List[SubTask]) -> List[List[SubTask]]:
        """
        获取任务执行顺序（拓扑排序）

        Args:
            subtasks: 子任务列表

        Returns:
            分层执行顺序
        """
        if not subtasks:
            return []

        dependency_map = {t.id: set(t.dependencies) for t in subtasks}
        task_map = {t.id: t for t in subtasks}

        result = []
        remaining = set(t.id for t in subtasks)

        while remaining:
            ready = []
            for task_id in list(remaining):
                deps = dependency_map.get(task_id, set())
                if not deps or not deps.intersection(remaining):
                    ready.append(task_map[task_id])

            if not ready:
                for task_id in remaining:
                    ready.append(task_map[task_id])
                remaining.clear()
            else:
                for task in ready:
                    remaining.discard(task.id)

            result.append(ready)

        return result


def get_task_planner() -> TaskPlanner:
    """获取任务规划器实例"""
    return TaskPlanner()
