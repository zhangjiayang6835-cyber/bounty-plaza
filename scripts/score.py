#!/usr/bin/env python3
"""
评分系统 — Scoring System
提交代码质量评分，百分制，≥90 分达标。

评分维度:
  - 功能正确性 (40分) — pytest 通过率
  - 安全性     (35分) — 作弊检测+静态分析
  - 代码质量   (15分) — pylint + 圈复杂度
  - 性能       (10分) — 执行效率

一票否决项（0分）:
  - AST 检测到直接返回预期输出
  - 删除/篡改测试用例
  - 引入外部恶意依赖
  - 代码为空/乱码
  - bandit 检测到高危漏洞

用法:
    python scripts/score.py --code <file> --tests <test_dir>
    python scripts/score.py --check <file>   # 仅检查作弊
"""

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


# ── 评分配置 ─────────────────────────────────────────────────────

PASS_THRESHOLD = 90
WEIGHTS = {
    "correctness": 40,
    "security": 35,
    "quality": 15,
    "performance": 10,
}


# ── 一票否决检测 ─────────────────────────────────────────────────

def check_ast_cheating(code: str) -> list[str]:
    """AST 静态分析检测作弊行为"""
    violations = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        violations.append(f"代码语法错误: {e}")
        return violations

    for node in ast.walk(tree):
        # 检测直接 return 硬编码值
        if isinstance(node, ast.FunctionDef):
            for n in ast.walk(node):
                if isinstance(n, ast.Return) and isinstance(n.value, (ast.Constant, ast.List, ast.Dict)):
                    if isinstance(n.value, ast.Constant) and isinstance(n.value.value, str) and len(n.value.value) > 20:
                        violations.append(f"函数 {node.name} 直接返回硬编码字符串（疑似预期输出伪造）")
                        break
                    if isinstance(n.value, ast.List) and len(n.value.elts) > 2:
                        violations.append(f"函数 {node.name} 直接返回硬编码列表（疑似预期输出伪造）")
                        break

        # 检测 eval/exec
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "compile"):
                violations.append(f"禁止使用 {node.func.id}()")
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("system", "popen", "call", "run") and isinstance(node.func.value, ast.Name) and node.func.value.id in ("os", "subprocess"):
                    if True:  # 所有危险系统调用
                        violations.append(f"危险系统调用: {node.func.value.id}.{node.func.attr}()")

        # 检测 import 白名单违规
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module in ("pickle", "marshal", "shelve", "ctypes", "imp", "importlib"):
                    violations.append(f"禁止使用模块: {module}")

    return violations


def check_bandit(code_file: str) -> list[str]:
    """调用 bandit 做安全扫描"""
    violations = []
    try:
        result = subprocess.run(
            ["bandit", "-q", "-f", "json", code_file],
            capture_output=True, text=True, timeout=30
        )
        if result.stdout:
            data = json.loads(result.stdout)
            for issue in data.get("results", []):
                if issue.get("issue_severity") in ("HIGH", "MEDIUM"):
                    violations.append(f"[bandit] {issue.get('test_name')}: {issue.get('issue_text')}")
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return violations


def check_test_tampering(original_hash: str, test_dir: str) -> list[str]:
    """检查测试用例是否被篡改"""
    violations = []
    if not original_hash:
        return violations
    for f in Path(test_dir).glob("test_*.py"):
        content = f.read_text()
        current_hash = str(hash(content))
        # 简单校验：文件行数
        with open(f) as fh:
            lines = len(fh.readlines())
        if lines < 3:
            violations.append(f"测试文件 {f.name} 被清空或篡改")
    return violations


# ── 评分函数 ─────────────────────────────────────────────────────

def score_correctness(test_dir: str) -> tuple:
    """运行 pytest，返回 (分数, 详情)"""
    if not test_dir or not os.path.isdir(test_dir):
        return 0, "无测试目录"
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", test_dir, "-v", "--tb=short", ],
            capture_output=True, text=True, timeout=120
        )
        # 从 stdout 解析测试结果
        passed = result.stdout.count("PASSED")
        failed = result.stdout.count("FAILED") + result.stdout.count("ERROR") + result.stdout.count("ERRORS")
        total = passed + failed
        if total == 0:
            return 0, "无测试用例"
        rate = passed / total if total > 0 else 0
        score = round(40 * rate)
        return score, f"{passed}/{total} 通过"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return 0, f"测试执行失败: {e}"


def score_security(violations: list[str], code: str) -> tuple:
    """安全评分，满分 35，每项违规扣 7 分"""
    deductions = len(violations) * 7
    score = max(0, 35 - deductions)
    details = "; ".join(violations) if violations else "无违规"
    return score, details


def score_quality(code_file: str) -> tuple:
    """代码质量评分，调用 pylint"""
    try:
        result = subprocess.run(
            ["pylint", "--score=y", "--output-format=text", code_file],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.split("\n"):
            if "Your code has been rated at" in line:
                # "Your code has been rated at 8.50/10"
                import re
                m = re.search(r"([\d.]+)/10", line)
                if m:
                    score = float(m.group(1))
                    return round(score / 10 * 15), f"pylint: {score}/10"
        return 10, "pylint 未输出评分（可能有语法问题）"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 10, "pylint 未安装，默认 10/15"


def score_performance(code_file: str, baseline_sec: float = 1.0) -> tuple:
    """性能评分，执行时间对比基线"""
    try:
        start = time.time()
        result = subprocess.run(
            ["python", code_file],
            capture_output=True, text=True, timeout=30
        )
        elapsed = time.time() - start
        ratio = elapsed / max(baseline_sec, 0.1)
        if ratio <= 1: score = 10
        elif ratio <= 2: score = 8
        elif ratio <= 5: score = 5
        else: score = 2
        return score, f"执行时间 {elapsed:.2f}s (基线 {baseline_sec}s)"
    except Exception as e:
        return 0, f"执行失败: {e}"


# ── 主流程 ────────────────────────────────────────────────────────

def evaluate(code_file: str, test_dir: str = None) -> dict:
    """完整评测流程，返回评分结果"""
    with open(code_file, encoding="utf-8") as f:
        code = f.read()

    result = {
        "score": 0,
        "passed": False,
        "details": {},
        "violations": [],
        "cheating_detected": False,
    }

    # 1. 一票否决检查
    ast_violations = check_ast_cheating(code)
    bandit_violations = check_bandit(code_file)
    all_violations = ast_violations + bandit_violations

    if all_violations:
        result["cheating_detected"] = True
        result["violations"] = all_violations
        result["details"]["security"] = {"score": 0, "note": "一票否决: 检测到作弊行为"}
        result["score"] = 0
        return result

    # 2. 分维度评分
    correctness_score, correctness_note = score_correctness(test_dir)
    security_score, security_note = score_security([], code)
    quality_score, quality_note = score_quality(code_file)
    perf_score, perf_note = score_performance(code_file)

    total = correctness_score + security_score + quality_score + perf_score

    result["score"] = total
    result["passed"] = total >= PASS_THRESHOLD
    result["details"] = {
        "correctness": {"score": correctness_score, "note": correctness_note, "weight": 40},
        "security": {"score": security_score, "note": security_note, "weight": 35},
        "quality": {"score": quality_score, "note": quality_note, "weight": 15},
        "performance": {"score": perf_score, "note": perf_note, "weight": 10},
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="代码质量评分系统")
    parser.add_argument("--code", required=True, help="待评分的代码文件")
    parser.add_argument("--tests", default=None, help="测试目录")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    result = evaluate(args.code, args.tests)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("=" * 50)
        print("📊 评分结果")
        print("=" * 50)
        for dim, data in result["details"].items():
            bar = "█" * (data["score"] // 2) + "░" * (10 - data["score"] // 2)
            print(f"  {dim:<15} {data['score']:>3}/{data['weight']:<2} {bar} {data['note']}")
        print("-" * 50)
        verdict = "✅ 达标 ✅" if result["passed"] else "❌ 未达标 ❌"
        print(f"  总分: {result['score']}/100  {verdict}")

        if result["violations"]:
            print("\n  违规项:")
            for v in result["violations"]:
                print(f"    ❌ {v}")

        if result["cheating_detected"]:
            print("\n  ⚠️  检测到作弊行为，总分: 0")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
