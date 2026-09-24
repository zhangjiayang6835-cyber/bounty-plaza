#!/usr/bin/env python3
"""Code quality scoring system.

Evaluates submission quality on a 100-point scale:
  - Correctness (40 points): pytest pass rate
  - Security (35 points): AST analysis and bandit scanning
  - Quality (15 points): pylint score
  - Performance (10 points): execution efficiency relative to baseline
"""

import argparse
import ast
import json
import os
import re
import shutil
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


def _check_ast_functions(node: ast.AST, violations: list[str]) -> None:
    """Detect hardcoded return outputs in functions.

    Args:
        node: AST node to evaluate.
        violations: Accumulator list of detected violations.
    """
    if not isinstance(node, ast.FunctionDef):
        return
    for child in ast.walk(node):
        if not isinstance(child, ast.Return):
            continue
        if (
            isinstance(child.value, ast.Constant)
            and isinstance(child.value.value, str)
            and len(child.value.value) > 20
        ):
            violations.append(
                f"Function {node.name} returns hardcoded string output"
            )
            break
        if (
            isinstance(child.value, ast.List)
            and len(child.value.elts) > 2
        ):
            violations.append(
                f"Function {node.name} returns hardcoded list output"
            )
            break


def _check_ast_calls(node: ast.AST, violations: list[str]) -> None:
    """Detect forbidden runtime evaluation calls.

    Args:
        node: AST node to evaluate.
        violations: Accumulator list of detected violations.
    """
    if not isinstance(node, ast.Call):
        return
    if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "compile"):
        violations.append(f"Forbidden call to {node.func.id}()")
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr in ("system", "popen")
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in ("os", "subprocess")
    ):
        violations.append(
            f"Dangerous system call: {node.func.value.id}.{node.func.attr}()"
        )


def _check_ast_imports(node: ast.AST, violations: list[str]) -> None:
    """Detect unapproved imported modules.

    Args:
        node: AST node to evaluate.
        violations: Accumulator list of detected violations.
    """
    if not isinstance(node, (ast.Import, ast.ImportFrom)):
        return
    for alias in node.names:
        module = alias.name.split(".")[0]
        if module in ("pickle", "marshal", "shelve", "ctypes", "imp", "importlib"):
            violations.append(f"Forbidden import of module: {module}")


def check_ast_cheating(code: str) -> list[str]:
    """Inspect syntax tree for cheating patterns and unauthorized calls.

    Args:
        code: Source code content string.

    Returns:
        List of identified violation messages.
    """
    violations: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        violations.append(f"Syntax error during parsing: {exc}")
        return violations

    for node in ast.walk(tree):
        _check_ast_functions(node, violations)
        _check_ast_calls(node, violations)
        _check_ast_imports(node, violations)

    return violations


def check_bandit(code_file: str) -> list[str]:
    """Execute Bandit security scanner against the specified source file.

    Args:
        code_file: Path to candidate source code.

    Returns:
        List of detected security vulnerability descriptions.
    """
    violations: list[str] = []
    bandit_bin = shutil.which("bandit")
    if not bandit_bin:
        violations.append("Bandit scanner not found in environment")
        return violations

    try:
        result = subprocess.run(
            [bandit_bin, "-q", "-f", "json", code_file],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.stdout:
            data = json.loads(result.stdout)
            for issue in data.get("results", []):
                if issue.get("issue_severity") in ("HIGH", "MEDIUM"):
                    violations.append(
                        f"[bandit] {issue.get('test_name')}: {issue.get('issue_text')}"
                    )
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        violations.append("Bandit security scanner failed during execution")
    return violations


def check_test_tampering(original_hash: str, test_dir: str) -> list[str]:
    """Ensure test suites remain intact and non-empty.

    Args:
        original_hash: Expected test suite hash identifier.
        test_dir: Directory containing test suites.

    Returns:
        List of detected test suite integrity errors.
    """
    violations: list[str] = []
    if not original_hash:
        return violations
    for file_path in Path(test_dir).glob("test_*.py"):
        with open(file_path, "r", encoding="utf-8") as handle:
            lines = len(handle.readlines())
        if lines < 3:
            violations.append(f"Test file {file_path.name} is truncated or empty")
    return violations


def score_correctness(test_dir: str) -> tuple[int, str]:
    """Run pytest suite and determine correctness score.

    Args:
        test_dir: Directory containing pytest test suites.

    Returns:
        Tuple containing integer score and summary status string.
    """
    if not test_dir or not os.path.isdir(test_dir):
        return 0, "No test directory provided"
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
            return 0, "No tests discovered"
        rate = passed / total if total > 0 else 0
        score = round(40 * rate)
        return score, f"{passed}/{total} passed"
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 0, f"Test execution failed: {exc}"


def score_security(violations: list[str]) -> tuple[int, str]:
    """Calculate security score with deductions for detected violations.

    Args:
        violations: List of detected security violation messages.

    Returns:
        Tuple containing integer score and status details.
    """
    deductions = len(violations) * 7
    score = max(0, 35 - deductions)
    details = "; ".join(violations) if violations else "No violations detected"
    return score, details


def score_quality(code_file: str) -> tuple[int, str]:
    """Calculate code quality score using pylint.

    Args:
        code_file: Path to source code file.

    Returns:
        Tuple containing integer score and pylint output details.
    """
    pylint_bin = shutil.which("pylint")
    if not pylint_bin:
        return 0, "Pylint not installed"
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}".rstrip(":")
        result = subprocess.run(
            [pylint_bin, "--score=y", "--output-format=text", code_file],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env,
        )
        for line in result.stdout.split("\n"):
            if "Your code has been rated at" in line:
                match = re.search(r"([\d.]+)/10", line)
                if match:
                    score = float(match.group(1))
                    return round(score / 10 * 15), f"pylint: {score}/10"
        return 0, "Pylint produced no score output"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 0, "Pylint execution error"


def score_performance(code_file: str, baseline_sec: float = 1.0) -> tuple[int, str]:
    """Evaluate execution performance relative to baseline.

    Args:
        code_file: Path to source code file.
        baseline_sec: Target execution threshold in seconds.

    Returns:
        Tuple containing integer score and execution time note.
    """
    try:
        python_bin = sys.executable or "python3"
        with open(code_file, "r", encoding="utf-8") as handle:
            code_content = handle.read()
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
        return score, f"Execution time {elapsed:.2f}s (baseline {baseline_sec}s)"
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        return 0, f"Execution failed: {exc}"


def _aggregate_dimension_scores(
    code_file: str, test_dir: str | None
) -> tuple[tuple[int, str], tuple[int, str], tuple[int, str], tuple[int, str]]:
    """Gather scores across correctness, security, quality, and performance.

    Args:
        code_file: Path to source code file.
        test_dir: Directory containing test suites.

    Returns:
        Tuple containing results for each evaluation dimension.
    """
    c_res = score_correctness(test_dir or "")
    s_res = score_security([])
    q_res = score_quality(code_file)
    p_res = score_performance(code_file)
    return c_res, s_res, q_res, p_res


def evaluate(code_file: str, test_dir: str | None = None) -> dict:
    """Run full automated evaluation pipeline across all dimensions.

    Args:
        code_file: Path to candidate source code.
        test_dir: Optional path to test directory.

    Returns:
        Structured evaluation dictionary containing overall score and breakdown.
    """
    real_path = os.path.realpath(code_file)
    allowed_dir = os.path.realpath(os.getenv("SUBMISSION_DIR", os.path.dirname(code_file)))
    if not real_path.startswith(allowed_dir):
        raise ValueError(f"Code file not within permitted directory: {code_file}")

    with open(real_path, "r", encoding="utf-8") as handle:
        code = handle.read(10_000_000)

    ast_violations = check_ast_cheating(code)
    bandit_violations = check_bandit(code_file)
    all_violations = ast_violations + bandit_violations

    if all_violations:
        return {
            "score": 0,
            "passed": False,
            "details": {
                "security": {
                    "score": 0,
                    "note": "Immediate failure: cheating detected",
                    "weight": 35,
                }
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
    parser = argparse.ArgumentParser(description="Code Quality Scoring System")
    parser.add_argument("--code", required=True, help="Target code file to score")
    parser.add_argument("--tests", default=None, help="Directory containing test suites")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    result = evaluate(args.code, args.tests)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("=" * 50)
        print("Evaluation Results")
        print("=" * 50)
        for dim, data in result["details"].items():
            progress_bar = (
                "#" * (data["score"] // 2) + "." * (10 - data["score"] // 2)
            )
            score_str = f"{data['score']:>3}/{data['weight']:<2}"
            print(f"  {dim:<15} {score_str} {progress_bar} {data['note']}")
        print("-" * 50)
        verdict = "PASSED" if result["passed"] else "FAILED"
        print(f"  Total Score: {result['score']}/100  {verdict}")

        if result["violations"]:
            print("\n  Violations:")
            for item in result["violations"]:
                print(f"    - {item}")

        if result["cheating_detected"]:
            print("\n  Cheating detected; score zeroed.")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
