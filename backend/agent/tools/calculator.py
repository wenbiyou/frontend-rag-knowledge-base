"""
计算工具
提供数学计算和数据分析能力
"""

import json
import math
import statistics
from typing import Dict, Any, List, Optional
from decimal import Decimal, getcontext

from agent.tools.base import BaseTool, ToolResult


class CalculatorTool(BaseTool):
    """数学计算工具"""

    name = "calculator"
    description = "执行数学计算，支持基本运算、三角函数、对数等"
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，如 '2 + 3 * 4' 或 'sin(pi/2)'"
            },
            "precision": {
                "type": "integer",
                "description": "结果精度（小数位数）",
                "default": 10
            }
        },
        "required": ["expression"]
    }

    SAFE_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        "floor": math.floor,
        "ceil": math.ceil,
        "pi": math.pi,
        "e": math.e,
    }

    def execute(self, **kwargs) -> ToolResult:
        """执行数学计算"""
        expression = kwargs.get("expression", "")
        precision = kwargs.get("precision", 10)

        if not expression:
            return ToolResult(
                success=False,
                output=None,
                error="表达式不能为空"
            )

        try:
            safe_dict = {"__builtins__": {}}
            safe_dict.update(self.SAFE_FUNCTIONS)

            result = eval(expression, safe_dict, {})

            if isinstance(result, float):
                result = round(result, precision)

            return ToolResult(
                success=True,
                output={
                    "expression": expression,
                    "result": result,
                    "type": type(result).__name__
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"计算错误: {str(e)}"
            )


class StatisticsTool(BaseTool):
    """统计分析工具"""

    name = "statistics"
    description = "对数据集进行统计分析"
    parameters = {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "items": {"type": "number"},
                "description": "数据数组"
            },
            "operations": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["mean", "median", "mode", "std", "var", "min", "max", "sum", "count"]
                },
                "description": "要执行的操作列表"
            }
        },
        "required": ["data"]
    }

    def execute(self, **kwargs) -> ToolResult:
        """执行统计分析"""
        data = kwargs.get("data", [])
        operations = kwargs.get("operations", ["mean", "median", "std", "min", "max", "sum", "count"])

        if not data:
            return ToolResult(
                success=False,
                output=None,
                error="数据不能为空"
            )

        try:
            results = {}

            for op in operations:
                if op == "mean":
                    results["mean"] = statistics.mean(data)
                elif op == "median":
                    results["median"] = statistics.median(data)
                elif op == "mode":
                    try:
                        results["mode"] = statistics.mode(data)
                    except statistics.StatisticsError:
                        results["mode"] = None
                elif op == "std":
                    if len(data) > 1:
                        results["std"] = statistics.stdev(data)
                    else:
                        results["std"] = 0
                elif op == "var":
                    if len(data) > 1:
                        results["var"] = statistics.variance(data)
                    else:
                        results["var"] = 0
                elif op == "min":
                    results["min"] = min(data)
                elif op == "max":
                    results["max"] = max(data)
                elif op == "sum":
                    results["sum"] = sum(data)
                elif op == "count":
                    results["count"] = len(data)

            for key in results:
                if isinstance(results[key], float):
                    results[key] = round(results[key], 6)

            return ToolResult(
                success=True,
                output={
                    "data_size": len(data),
                    "statistics": results
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"统计分析错误: {str(e)}"
            )


class DataAnalysisTool(BaseTool):
    """数据分析工具"""

    name = "data_analysis"
    description = "分析数据特征，包括分布、异常值检测等"
    parameters = {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "items": {"type": "number"},
                "description": "数据数组"
            },
            "analysis_type": {
                "type": "string",
                "enum": ["distribution", "outliers", "correlation", "all"],
                "description": "分析类型",
                "default": "all"
            }
        },
        "required": ["data"]
    }

    def execute(self, **kwargs) -> ToolResult:
        """执行数据分析"""
        data = kwargs.get("data", [])
        analysis_type = kwargs.get("analysis_type", "all")

        if not data:
            return ToolResult(
                success=False,
                output=None,
                error="数据不能为空"
            )

        try:
            results = {}

            if analysis_type in ["distribution", "all"]:
                sorted_data = sorted(data)
                n = len(sorted_data)
                results["distribution"] = {
                    "q1": sorted_data[n // 4] if n >= 4 else sorted_data[0],
                    "q2": sorted_data[n // 2],
                    "q3": sorted_data[3 * n // 4] if n >= 4 else sorted_data[-1],
                    "iqr": sorted_data[3 * n // 4] - sorted_data[n // 4] if n >= 4 else 0,
                }

            if analysis_type in ["outliers", "all"]:
                sorted_data = sorted(data)
                n = len(sorted_data)
                q1 = sorted_data[n // 4] if n >= 4 else sorted_data[0]
                q3 = sorted_data[3 * n // 4] if n >= 4 else sorted_data[-1]
                iqr = q3 - q1

                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr

                outliers = [x for x in data if x < lower_bound or x > upper_bound]
                results["outliers"] = {
                    "count": len(outliers),
                    "values": outliers[:10],
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                }

            return ToolResult(
                success=True,
                output={
                    "data_size": len(data),
                    "analysis": results
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"数据分析错误: {str(e)}"
            )
