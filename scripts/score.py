#!/usr/bin/env python3
"""Automated code quality scoring engine for bounty-plaza submissions."""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

PASS_THRESHOLD = 90
WEIGHTS = {
    "correctness": 40,
    "security": 35,
    "quality": 15,
    "performance": 10,
}


def _check_return_cheating(node: ast.FunctionDef, violations: list[str]) -> None:
    """Detect functions returning hardcoded strings or lists.

    Args:
        node: AST function definition node.
        violations: Mutable list of detected violations.
    """
    for inner in ast.walk(node):
        if not isinstance(inner, ast.Return):
            continue
        if isinstance(inner.value, ast.Constant) and isinstance(inner.value.value, str):
            if len(inner.value.value) > 20:
                violations.append(f"函数 {node.name} 直接返回硬编码字符串（疑似预期输出伪造）")
                break
        if isinstance(inner.value, ast.List) and len(inner.value.elts) > 2:
            violations.append(f"函数 {node.name} 直接返回硬编码列表（疑似预期输出伪造）")
            break


def check_ast_cheating(code: str) -> list[str]:
    """Inspect abstract syntax tree for cheating and banned operations.

    Args:
        code: Source code string to inspect.

    Returns:
        List of detected violation messages.
    """
    violations = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        violations.append(f"代码语法错误: {exc}")
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            _check_return_cheating(node, violations)

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "compile"):
                violations.append(f"禁止使用 {node.func.id}()")
            if isinstance(node.func, ast.Attribute):
                caller = node.func.value
                if isinstance(caller, ast.Name) and caller.id in ("os", "subprocess"):
                    if node.func.attr in ("system", "popen", "call", "run"):
                        violations.append(f"危险系统调用: {caller.id}.{node.func.attr}()")

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module in ("pickle", "marshal", "shelve", "ctypes", "imp", "importlib"):
                    violations.append(f"禁止使用模块: {module}")

    return violations


def check_bandit(code_file: str) -> list[str]:
    """Execute bandit static analyzer to detect security vulnerabilities.

    Args:
        code_file: Path to source code file.

    Returns:
        List of bandit issue descriptions.
    """
    violations = []
    try:
        result = subprocess.run(
            ["bandit", "-q", "-f", "json", code_file],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.stdout:
            data = json.loads(result.stdout)
            for issue in data.get("results", []):
                if issue.get("issue_severity") in ("HIGH", "MEDIUM"):
                    test_name = issue.get("test_name")
                    issue_text = issue.get("issue_text")
                    violations.append(f"[bandit] {test_name}: {issue_text}")
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        violations.append("[安全扫描] bandit 未安装或执行失败，无法评分")
    return violations


def check_test_tampering(original_hash: str, test_dir: str) -> list[str]:
    """Verify test files maintain structural integrity.

    Args:
        original_hash: Baseline verification hash.
        test_dir: Directory containing tests.

    Returns:
        List of tampering alerts.
    """
    violations = []
    if not original_hash:
        return violations
    for file_path in Path(test_dir).glob("test_*.py"):
        with open(file_path, encoding="utf-8") as handle:
            lines = len(handle.readlines())
        if lines < 3:
            violations.append(f"测试文件 {file_path.name} 被清空或篡改")
    return violations


def score_correctness(test_dir: str) -> tuple:
    """Run pytest suite and calculate correctness score.

    Args:
        test_dir: Directory containing test suites.

    Returns:
        Tuple containing integer score and status note.
    """
    if not test_dir or not os.path.isdir(test_dir):
        return 0, "无测试目录"
    try:
        python_bin = sys.executable or "python3"
        result = subprocess.run(
            [python_bin, "-m", "pytest", test_dir, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        passed = result.stdout.count("PASSED")
        failed = (
            result.stdout.count("FAILED")
            + result.stdout.count("ERROR")
            + result.stdout.count("ERRORS")
        )
        total = passed + failed
        if total == 0:
            return 0, "无测试用例"
        rate = passed / total if total > 0 else 0
        score = round(40 * rate)
        return score, f"{passed}/{total} 通过"
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 0, f"测试执行失败: {exc}"


def score_security(violations: list[str]) -> tuple:
    """Calculate security score with deductions for detected violations.

    Args:
        violations: List of security violation messages.

    Returns:
        Tuple containing integer score and status detail.
    """
    deductions = len(violations) * 7
    score = max(0, 35 - deductions)
    details = "; ".join(violations) if violations else "无违规"
    return score, details


def score_quality(code_file: str) -> tuple:
    """Calculate code quality score using pylint.

    Args:
        code_file: Path to source code file.

    Returns:
        Tuple containing integer score and pylint output detail.
    """
    try:
        result = subprocess.run(
            ["pylint", "--score=y", "--output-format=text", code_file],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        for line in result.stdout.split("\n"):
            if "Your code has been rated at" in line:
                match = re.search(r"([\d.]+)/10", line)
                if match:
                    rating = float(match.group(1))
                    return round(rating / 10 * 15), f"pylint: {rating}/10"
        return 0, "pylint 未输出评分（无法评分）"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 0, "pylint 未安装或执行失败"


def score_performance(code_file: str, baseline_sec: float = 1.0) -> tuple:
    """Evaluate execution performance relative to baseline.

    Args:
        code_file: Path to source code file.
        baseline_sec: Reference maximum execution threshold.

    Returns:
        Tuple containing integer score and execution time note.
    """
    try:
        python_bin = sys.executable or "python3"
        with open(code_file, encoding="utf-8") as file_handle:
            code_content = file_handle.read()
        start = time.time()
        subprocess.run(
            [python_bin, "-c", code_content],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        elapsed = time.time() - start
        ratio = elapsed / max(baseline_sec, 0.1)
        if ratio <= 1:
            score = 10
        elif ratio <= 2:
            score = 8
        elif ratio <= 5:
            score = 5
        else:
            score = 2
        return score, f"执行时间 {elapsed:.2f}s (基线 {baseline_sec}s)"
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        return 0, f"执行失败: {exc}"


def _aggregate_dimension_scores(code_file: str, test_dir: str = None) -> tuple:
    """Collect dimension-specific scoring tuples.

    Args:
        code_file: Path to code file under evaluation.
        test_dir: Path to directory containing tests.

    Returns:
        Tuple containing correctness, security, quality, and performance tuples.
    """
    c_res = score_correctness(test_dir)
    s_res = score_security([])
    q_res = score_quality(code_file)
    p_res = score_performance(code_file)
    return c_res, s_res, q_res, p_res


def evaluate(code_file: str, test_dir: str = None) -> dict:
    """Perform full automated scoring pipeline across all quality dimensions.

    Args:
        code_file: Path to candidate source code.
        test_dir: Optional path to test suite directory.

    Returns:
        Structured evaluation dictionary containing overall score and breakdown.
    """
    real_path = os.path.realpath(code_file)
    allowed_dir = os.path.realpath(os.getenv("SUBMISSION_DIR", os.path.dirname(code_file)))
    if not real_path.startswith(allowed_dir):
        raise ValueError(f"代码文件不在允许的目录中: {code_file}")

    with open(real_path, encoding="utf-8") as handle:
        code = handle.read(10_000_000)

    all_violations = check_ast_cheating(code) + check_bandit(code_file)
    if all_violations:
        return {
            "score": 0,
            "passed": False,
            "details": {
                "security": {"score": 0, "note": "一票否决: 检测到作弊行为", "weight": 35}
            },
            "violations": all_violations,
            "cheating_detected": True,
        }

    c_res, s_res, q_res, p_res = _aggregate_dimension_scores(code_file, test_dir)
    total = c_res[0] + s_res[0] + q_res[0] + p_res[0]

    return {
        "score": total,
        "passed": total >= PASS_THRESHOLD,
        "details": {
            "correctness": {"score": c_res[0], "note": c_res[1], "weight": 40},
            "security": {"score": s_res[0], "note": s_res[1], "weight": 35},
            "quality": {"score": q_res[0], "note": q_res[1], "weight": 15},
            "performance": {"score": p_res[0], "note": p_res[1], "weight": 10},
        },
        "violations": [],
        "cheating_detected": False,
    }


def main() -> int:
    """Command line entrypoint for scoring submissions.

    Returns:
        0 if submission passes threshold, 1 otherwise.
    """
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
        print("评分结果")
        print("=" * 50)
        for dim, data in result["details"].items():
            progress_bar = (
                "█" * (data["score"] // 2) + "░" * (10 - data["score"] // 2)
            )
            score_str = f"{data['score']:>3}/{data['weight']:<2}"
            print(f"  {dim:<15} {score_str} {progress_bar} {data['note']}")
        print("-" * 50)
        verdict = "达标" if result["passed"] else "未达标"
        print(f"  总分: {result['score']}/100  {verdict}")

        if result["violations"]:
            print("\n  违规项:")
            for item in result["violations"]:
                print(f"    - {item}")

        if result["cheating_detected"]:
            print("\n  检测到作弊行为，总分: 0")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
