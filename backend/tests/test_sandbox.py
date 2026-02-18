"""
代码沙箱功能测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.sandbox import CodeSandbox, SandboxExecutor, SandboxConfig
from agent.sandbox.sandbox import Language
from agent.sandbox.limits import ResourceLimits


def test_python_execution():
    """测试 Python 代码执行"""
    print("=" * 50)
    print("测试 Python 代码执行")
    print("=" * 50)

    executor = SandboxExecutor()

    code = '''
print("Hello, World!")

result = sum(range(1, 101))
print(f"1到100的和: {result}")

import math
print(f"圆周率: {math.pi}")
'''

    result = executor.execute_python(code)
    print(f"执行成功: {result.success}")
    print(f"输出: {result.output}")
    print(f"执行时间: {result.execution_time:.3f}s")
    print()

    return result.success


def test_javascript_execution():
    """测试 JavaScript 代码执行"""
    print("=" * 50)
    print("测试 JavaScript 代码执行")
    print("=" * 50)

    executor = SandboxExecutor(SandboxConfig(language=Language.JAVASCRIPT))

    code = '''
console.log("Hello from JavaScript!");

const sum = Array.from({length: 100}, (_, i) => i + 1).reduce((a, b) => a + b, 0);
console.log("1到100的和: " + sum);

console.log("Math.PI: " + Math.PI);
'''

    result = executor.execute(code)
    print(f"执行成功: {result.success}")
    print(f"输出: {result.output}")
    print(f"执行时间: {result.execution_time:.3f}s")
    print()

    return result.success


def test_code_validation():
    """测试代码安全验证"""
    print("=" * 50)
    print("测试代码安全验证")
    print("=" * 50)

    config = SandboxConfig()
    sandbox = CodeSandbox(config)

    safe_code = '''
import math
print(math.sqrt(16))
'''

    is_valid, error = sandbox.validate_code(safe_code)
    print(f"安全代码验证: {'通过' if is_valid else '失败'}")
    if error:
        print(f"错误: {error}")

    dangerous_code = '''
import os
os.system("rm -rf /")
'''

    is_valid, error = sandbox.validate_code(dangerous_code)
    print(f"危险代码验证: {'通过' if is_valid else '拦截'}")
    if error:
        print(f"拦截原因: {error}")
    print()

    return True


def test_timeout():
    """测试超时限制"""
    print("=" * 50)
    print("测试超时限制")
    print("=" * 50)

    limits = ResourceLimits(max_wall_time=2.0)
    config = SandboxConfig(language=Language.PYTHON, limits=limits)
    executor = SandboxExecutor(config)

    code = '''
import time
while True:
    time.sleep(0.1)
    print("running...")
'''

    result = executor.execute(code, timeout=2.0)
    print(f"执行成功: {result.success}")
    print(f"错误信息: {result.error}")
    print()

    return not result.success


def test_resource_limits():
    """测试资源限制"""
    print("=" * 50)
    print("测试资源限制配置")
    print("=" * 50)

    limits = ResourceLimits(
        max_cpu_time=5.0,
        max_wall_time=10.0,
        max_memory_mb=256,
    )

    print(f"CPU 时间限制: {limits.max_cpu_time}s")
    print(f"墙钟时间限制: {limits.max_wall_time}s")
    print(f"内存限制: {limits.max_memory_mb}MB")
    print()

    return True


def test_execution_with_context():
    """测试带上下文执行"""
    print("=" * 50)
    print("测试带上下文执行")
    print("=" * 50)

    executor = SandboxExecutor()

    code = '''
print(f"用户名: {username}")
print(f"年龄: {age}")
print(f"爱好: {hobbies}")
'''

    context = {
        "username": "张三",
        "age": 25,
        "hobbies": ["编程", "阅读", "运动"]
    }

    result = executor.execute_with_context(code, context)
    print(f"执行成功: {result.success}")
    print(f"输出: {result.output}")
    print()

    return result.success


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("       代码沙箱功能测试")
    print("=" * 60 + "\n")

    tests = [
        ("Python 代码执行", test_python_execution),
        ("JavaScript 代码执行", test_javascript_execution),
        ("代码安全验证", test_code_validation),
        ("超时限制", test_timeout),
        ("资源限制配置", test_resource_limits),
        ("带上下文执行", test_execution_with_context),
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
