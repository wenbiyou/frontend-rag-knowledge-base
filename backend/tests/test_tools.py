"""
工具调用系统测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools import get_tool_registry, ToolResult


def test_list_tools():
    """测试列出工具"""
    print("=" * 50)
    print("测试列出所有工具")
    print("=" * 50)

    registry = get_tool_registry()
    tools = registry.list_tools()

    print(f"已注册工具数量: {len(tools)}")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description'][:50]}...")
    print()

    return len(tools) > 0


def test_calculator():
    """测试计算器工具"""
    print("=" * 50)
    print("测试计算器工具")
    print("=" * 50)

    registry = get_tool_registry()

    test_cases = [
        ("2 + 3 * 4", 14),
        ("sqrt(16)", 4),
        ("sin(pi/2)", 1),
        ("log(e)", 1),
    ]

    all_passed = True
    for expr, expected in test_cases:
        result = registry.execute("calculator", expression=expr)
        status = "✅" if result.success else "❌"
        print(f"{status} {expr} = {result.output.get('result') if result.success else result.error}")
        if result.success:
            actual = result.output.get('result')
            if abs(actual - expected) > 0.0001:
                all_passed = False
        else:
            all_passed = False

    print()
    return all_passed


def test_statistics():
    """测试统计工具"""
    print("=" * 50)
    print("测试统计工具")
    print("=" * 50)

    registry = get_tool_registry()

    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    result = registry.execute("statistics", data=data)

    if result.success:
        stats = result.output.get("statistics", {})
        print(f"数据: {data}")
        print(f"均值: {stats.get('mean')}")
        print(f"中位数: {stats.get('median')}")
        print(f"标准差: {stats.get('std')}")
        print(f"最小值: {stats.get('min')}")
        print(f"最大值: {stats.get('max')}")
        print(f"总和: {stats.get('sum')}")
        print()
        return True
    else:
        print(f"执行失败: {result.error}")
        print()
        return False


def test_json_parser():
    """测试 JSON 解析工具"""
    print("=" * 50)
    print("测试 JSON 解析工具")
    print("=" * 50)

    registry = get_tool_registry()

    json_string = '{"name": "张三", "age": 25, "skills": ["Python", "JavaScript"]}'

    result = registry.execute("json_parser", json_string=json_string)
    if result.success:
        print(f"解析结果: {result.output.get('data')}")
    else:
        print(f"解析失败: {result.error}")

    result2 = registry.execute("json_parser", json_string=json_string, path="skills")
    if result2.success:
        print(f"路径 'skills' 结果: {result2.output.get('data')}")
    else:
        print(f"路径解析失败: {result2.error}")

    print()
    return result.success and result2.success


def test_url_builder():
    """测试 URL 构建工具"""
    print("=" * 50)
    print("测试 URL 构建工具")
    print("=" * 50)

    registry = get_tool_registry()

    result = registry.execute(
        "url_builder",
        base_url="https://api.example.com",
        path="/users",
        params={"page": 1, "limit": 10}
    )

    if result.success:
        print(f"构建的 URL: {result.output.get('url')}")
        print()
        return True
    else:
        print(f"构建失败: {result.error}")
        print()
        return False


def test_tool_schemas_for_llm():
    """测试 LLM 工具 Schema"""
    print("=" * 50)
    print("测试 LLM 工具 Schema")
    print("=" * 50)

    registry = get_tool_registry()
    schemas = registry.get_tool_schemas_for_llm()

    print(f"Schema 数量: {len(schemas)}")
    print(f"第一个工具 Schema:")
    import json
    print(json.dumps(schemas[0], indent=2, ensure_ascii=False))
    print()

    return len(schemas) > 0


def test_tools_by_category():
    """测试按类别列出工具"""
    print("=" * 50)
    print("测试按类别列出工具")
    print("=" * 50)

    registry = get_tool_registry()
    categories = registry.list_tools_by_category()

    for category, tools in categories.items():
        print(f"{category}: {len(tools)} 个工具")
        for tool in tools:
            print(f"  - {tool['name']}")

    print()
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("       工具调用系统测试")
    print("=" * 60 + "\n")

    tests = [
        ("列出工具", test_list_tools),
        ("计算器工具", test_calculator),
        ("统计工具", test_statistics),
        ("JSON 解析工具", test_json_parser),
        ("URL 构建工具", test_url_builder),
        ("LLM Schema", test_tool_schemas_for_llm),
        ("按类别列出", test_tools_by_category),
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
