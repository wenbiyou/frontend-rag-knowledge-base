"""
多Agent协作框架测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.orchestrator import (
    get_orchestrator,
    get_task_planner,
    get_task_executor,
    get_result_aggregator,
    TaskType,
    TaskPriority,
)


def test_task_planner():
    """测试任务规划器"""
    print("=" * 50)
    print("测试任务规划器")
    print("=" * 50)

    planner = get_task_planner()

    test_queries = [
        "搜索 React Hooks 的用法",
        "计算 2 + 3 * 4",
        "分析这段代码的性能问题",
        "总结前端开发的最佳实践",
    ]

    for query in test_queries:
        subtasks = planner.plan(query)
        print(f"\n查询: {query}")
        print(f"子任务数: {len(subtasks)}")
        for task in subtasks:
            print(f"  - {task.name}: {task.task_type.value}")

    print()
    return True


def test_task_classification():
    """测试任务分类"""
    print("=" * 50)
    print("测试任务分类")
    print("=" * 50)

    planner = get_task_planner()

    test_cases = [
        ("搜索 React Hooks", TaskType.SEARCH),
        ("计算 1+1", TaskType.CALCULATION),
        ("编写代码实现", TaskType.CODE),
        ("分析数据", TaskType.ANALYSIS),
        ("总结要点", TaskType.SYNTHESIS),
    ]

    all_correct = True
    for query, expected_type in test_cases:
        actual_type = planner._classify_task(query)
        status = "✅" if actual_type == expected_type else "❌"
        print(f"{status} '{query}' -> {actual_type.value} (期望: {expected_type.value})")
        if actual_type != expected_type:
            all_correct = False

    print()
    return all_correct


def test_execution_order():
    """测试执行顺序"""
    print("=" * 50)
    print("测试执行顺序")
    print("=" * 50)

    planner = get_task_planner()

    query = "搜索 React Hooks，然后分析其性能特点"
    subtasks = planner.decompose_complex_task(query)

    print(f"查询: {query}")
    print(f"子任务数: {len(subtasks)}")

    execution_order = planner.get_execution_order(subtasks)
    print(f"执行批次: {len(execution_order)}")

    for i, batch in enumerate(execution_order):
        print(f"  批次 {i + 1}: {[t.name for t in batch]}")

    print()
    return True


def test_task_executor():
    """测试任务执行器"""
    print("=" * 50)
    print("测试任务执行器")
    print("=" * 50)

    from agent.orchestrator.planner import SubTask

    executor = get_task_executor()

    subtask = SubTask(
        id="test_001",
        name="计算测试",
        description="执行数学计算",
        task_type=TaskType.CALCULATION,
        parameters={"expression": "2 + 3 * 4", "tool": "calculator"}
    )

    result = executor.execute(subtask)

    print(f"任务: {subtask.name}")
    print(f"成功: {result.success}")
    print(f"输出: {result.output}")
    print(f"执行时间: {result.execution_time:.3f}s")

    print()
    return result.success


def test_result_aggregator():
    """测试结果聚合器"""
    print("=" * 50)
    print("测试结果聚合器")
    print("=" * 50)

    from agent.orchestrator.planner import SubTask
    from agent.orchestrator.executor import ExecutionResult

    aggregator = get_result_aggregator()

    subtasks = [
        SubTask(
            id="task_1",
            name="搜索",
            description="搜索测试",
            task_type=TaskType.SEARCH,
        ),
        SubTask(
            id="task_2",
            name="计算",
            description="计算测试",
            task_type=TaskType.CALCULATION,
        ),
    ]

    results = {
        "task_1": ExecutionResult(
            task_id="task_1",
            success=True,
            output={"results": [{"title": "测试结果", "content": "这是测试内容"}]},
            tool_used="knowledge_search"
        ),
        "task_2": ExecutionResult(
            task_id="task_2",
            success=True,
            output={"result": 14},
            tool_used="calculator"
        ),
    }

    aggregated = aggregator.aggregate("测试查询", subtasks, results)

    print(f"查询: {aggregated.query}")
    print(f"成功: {aggregated.success}")
    print(f"答案: {aggregated.answer[:200]}...")
    print(f"来源数: {len(aggregated.sources)}")
    print(f"总执行时间: {aggregated.total_execution_time:.3f}s")

    print()
    return aggregated.success


def test_orchestrator():
    """测试编排器"""
    print("=" * 50)
    print("测试编排器")
    print("=" * 50)

    orchestrator = get_orchestrator()

    result = orchestrator.execute_task("计算 sqrt(16) + 2")

    print(f"查询: {result.query}")
    print(f"成功: {result.success}")
    print(f"答案: {result.answer}")
    print(f"子任务数: {len(result.subtask_results)}")
    print(f"总执行时间: {result.total_execution_time:.3f}s")

    print()
    return result.success


def test_parallel_execution():
    """测试并行执行"""
    print("=" * 50)
    print("测试并行执行")
    print("=" * 50)

    from agent.orchestrator.planner import SubTask
    from agent.orchestrator.executor import get_task_executor

    executor = get_task_executor()

    subtasks = [
        SubTask(
            id="p1",
            name="计算1",
            description="计算 1+1",
            task_type=TaskType.CALCULATION,
            parameters={"expression": "1+1", "tool": "calculator"}
        ),
        SubTask(
            id="p2",
            name="计算2",
            description="计算 2+2",
            task_type=TaskType.CALCULATION,
            parameters={"expression": "2+2", "tool": "calculator"}
        ),
        SubTask(
            id="p3",
            name="计算3",
            description="计算 3+3",
            task_type=TaskType.CALCULATION,
            parameters={"expression": "3+3", "tool": "calculator"}
        ),
    ]

    import time
    start = time.time()
    results = executor.execute_parallel(subtasks)
    elapsed = time.time() - start

    print(f"并行执行 {len(subtasks)} 个任务")
    print(f"总耗时: {elapsed:.3f}s")
    print(f"成功数: {sum(1 for r in results if r.success)}")

    for r in results:
        print(f"  - {r.task_id}: {r.output}")

    print()
    return all(r.success for r in results)


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("       多Agent协作框架测试")
    print("=" * 60 + "\n")

    tests = [
        ("任务规划器", test_task_planner),
        ("任务分类", test_task_classification),
        ("执行顺序", test_execution_order),
        ("任务执行器", test_task_executor),
        ("结果聚合器", test_result_aggregator),
        ("编排器", test_orchestrator),
        ("并行执行", test_parallel_execution),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            results.append((name, False, str(e)))

    print("\n" + "=" * 60)
    print("       测试结果汇总")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, success, error in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status}")
        if error:
            print(f"  错误: {error}")
        if success:
            passed += 1
        else:
            failed += 1

    print()
    print(f"总计: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
