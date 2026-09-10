"""Score repository submission on Correctness, Security, Quality, and Performance."""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time

WEIGHTS = {
    "correctness": 40,
    "security": 35,
    "quality": 15,
    "performance": 10,
}

PASSING_SCORE = 90


def check_ast_cheating(code_str: str) -> list[str]:
    """Detect potential cheating or malicious AST patterns.

    Args:
        code_str: Source code string to analyze.

    Returns:
        List of identified violation strings.
    """
    violations = []
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        return ["Syntax error encountered while parsing code"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec", "compile", "__import__"):
                    violations.append(f"Dangerous built-in function called: {node.func.id}")
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ("system", "popen", "spawn"):
                    violations.append(f"Dangerous system execution called: {node.func.attr}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in ("ctypes", "pty"):
                    violations.append(f"Dangerous low-level module imported: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module in ("ctypes", "pty"):
                violations.append(f"Dangerous low-level module imported: {node.module}")
    return violations


def check_bandit(code_file: str) -> list[str]:
    """Run Bandit security analysis on the target file.

    Args:
        code_file: Path to the target Python code file.

    Returns:
        List of identified security issue strings.
    """
    try:
        result = subprocess.run(
            ["bandit", "-f", "json", "-q", code_file],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if not result.stdout.strip():
            return []
        data = json.loads(result.stdout)
        return [
            f"[{issue['test_id']}] {issue['issue_text']} (line {issue['line_number']})"
            for issue in data.get("results", [])
            if issue.get("issue_severity") in ("MEDIUM", "HIGH")
        ]
    except FileNotFoundError:
        return []
    except subprocess.TimeoutExpired:
        return ["Bandit scan timed out (30s)"]
    except Exception as exc:
        return [f"Bandit execution failed: {exc}"]


def check_test_tampering(original_hash: str, test_dir: str) -> list[str]:
    """Verify test files were not modified or tampered with.

    Args:
        original_hash: Expected hash of the test files.
        test_dir: Path to directory containing tests.

    Returns:
        List of tampering violation strings.
    """
    if not original_hash:
        return []
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", test_dir],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.stdout.strip():
            return ["Test directory contains uncommitted modifications"]
    except Exception as exc:
        return [f"Git diff check failed: {exc}"]
    return []


def score_correctness(test_dir: str) -> tuple[int, str]:
    """Run pytest and return score and details.

    Args:
        test_dir: Path to directory or file containing pytest tests.

    Returns:
        Tuple of integer score and detail string.
    """
    if not test_dir or not (os.path.isdir(test_dir) or os.path.isfile(test_dir)):
        return 0, "No test directory or file provided"
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = f"{os.getcwd()}:{env.get('PYTHONPATH', '')}"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_dir, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env=env,
        )
        passed = 0
        total = 0
        for line in result.stdout.split("\n"):
            m_pass = re.search(r"(\d+) passed", line)
            if m_pass:
                passed = int(m_pass.group(1))
            m_failed = re.search(r"(\d+) failed", line)
            if m_failed:
                total += int(m_failed.group(1))
        total += passed

        if total == 0:
            if "no tests ran" in result.stdout or result.returncode == 5:
                return 0, "No tests ran"
            if result.returncode == 0:
                return WEIGHTS["correctness"], "Passed"
            return 0, f"Tests failed with exit code {result.returncode}"

        rate = passed / total
        score = int(rate * WEIGHTS["correctness"])
        return score, f"{passed}/{total} passed"

    except subprocess.TimeoutExpired:
        return 0, "Test execution timed out (120s)"
    except Exception as exc:
        return 0, f"Execution error: {exc}"


def score_security(violations: list[str], code: str) -> tuple[int, str]:
    """Calculate security score based on detected violations.

    Args:
        violations: List of security rule violations.
        code: Source code string under inspection.

    Returns:
        Tuple of integer score and detail string.
    """
    del code
    score = WEIGHTS["security"]
    notes = []

    for v in violations:
        score -= 7
        notes.append(v)

    score = max(0, score)
    detail = "No violations" if not notes else f"Found {len(notes)} issues: " + "; ".join(notes[:3])
    return score, detail


def score_quality(code_file: str) -> tuple[int, str]:
    """Score code quality using pylint.

    Args:
        code_file: File path to evaluate.

    Returns:
        Tuple of integer score and detail string.
    """
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = f"{os.getcwd()}:{env.get('PYTHONPATH', '')}"
        result = subprocess.run(
            [sys.executable, "-m", "pylint", "--score=y", "--output-format=text", code_file],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env,
        )
        for line in result.stdout.split("\n"):
            if "Your code has been rated at" in line:
                m_score = re.search(r"([\d.]+)/10", line)
                if m_score:
                    pylint_score = float(m_score.group(1))
                    score = int(pylint_score / 10 * WEIGHTS["quality"])
                    return score, f"pylint: {pylint_score}/10"
        return 0, "pylint output parse failure"
    except subprocess.TimeoutExpired:
        return 0, "pylint timeout"
    except Exception as exc:
        return 0, f"Quality score error: {exc}"


def score_performance(code_file: str, baseline_sec: float = 1.0) -> tuple[int, str]:
    """Score execution performance.

    Args:
        code_file: File path to execute.
        baseline_sec: Expected runtime baseline in seconds.

    Returns:
        Tuple of integer score and detail string.
    """
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = f"{os.getcwd()}:{env.get('PYTHONPATH', '')}"
        start = time.time()
        subprocess.run(
            [sys.executable, code_file],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env,
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
        return score, f"Elapsed: {elapsed:.2f}s (baseline {baseline_sec}s)"
    except Exception as exc:
        return 0, f"Execution failed: {exc}"


def evaluate(code_file: str, test_dir: str, original_test_hash: str = "") -> dict:
    """Run full evaluation suite across all dimensions.

    Args:
        code_file: Path to candidate solution source file.
        test_dir: Path to test suite directory or file.
        original_test_hash: Git hash of reference test files.

    Returns:
        Dictionary containing scores, details, total score, and pass status.
    """
    with open(code_file, "r", encoding="utf-8") as f:
        code_str = f.read()

    violations = []
    violations.extend(check_ast_cheating(code_str))
    violations.extend(check_bandit(code_file))
    violations.extend(check_test_tampering(original_test_hash, test_dir))

    corr_score, corr_detail = score_correctness(test_dir)
    sec_score, sec_detail = score_security(violations, code_str)
    qual_score, qual_detail = score_quality(code_file)
    perf_score, perf_detail = score_performance(code_file)

    total = corr_score + sec_score + qual_score + perf_score
    passed = total >= PASSING_SCORE and sec_score == WEIGHTS["security"]

    return {
        "total_score": total,
        "passed": passed,
        "passing_threshold": PASSING_SCORE,
        "breakdown": {
            "correctness": {"score": corr_score, "max": WEIGHTS["correctness"], "detail": corr_detail},
            "security": {"score": sec_score, "max": WEIGHTS["security"], "detail": sec_detail},
            "quality": {"score": qual_score, "max": WEIGHTS["quality"], "detail": qual_detail},
            "performance": {"score": perf_score, "max": WEIGHTS["performance"], "detail": perf_detail},
        },
    }


def main() -> None:
    """CLI entrypoint for score evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate code submission quality and security")
    parser.add_argument("--code", required=True, help="Path to code file")
    parser.add_argument("--tests", required=True, help="Path to tests directory or file")
    parser.add_argument("--test-hash", default="", help="Original test hash")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    result = evaluate(args.code, args.tests, args.test_hash)

    if args.json:
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
    else:
        sys.stdout.write("\n" + "=" * 50 + "\n")
        sys.stdout.write("  EVALUATION RESULT\n")
        sys.stdout.write("=" * 50 + "\n")
        sys.stdout.write(f"  Total Score: {result['total_score']} / 100\n")
        sys.stdout.write(f"  Passed:      {'YES' if result['passed'] else 'NO'}\n")
        sys.stdout.write("-" * 50 + "\n")
        for dim, data in result["breakdown"].items():
            sys.stdout.write(f"  {dim:<12}: {data['score']:>2}/{data['max']}  ({data['detail']})\n")
        sys.stdout.write("=" * 50 + "\n\n")

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
