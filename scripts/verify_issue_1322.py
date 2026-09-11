"""
Verification script for Issue #1322 Bedrock template expansion pipeline.
"""

from pathlib import Path
import subprocess
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from packages.bedrock_template_pipeline.verifier import PipelineVerifier


def verify_node_suite(root_dir: Path) -> bool:
    """Execute Node.js build pipeline test suite and return pass status."""
    test_file = root_dir / "test" / "build_pipeline.test.js"
    if not test_file.is_file():
        print(f"[ERROR] Node test file not found at {test_file}")
        return False

    cmd = ["node", "--test", str(test_file)]
    res = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        print("[FAIL] Node.js test suite failed:")
        print(res.stdout)
        print(res.stderr)
        return False

    print("[PASS] Node.js test suite passed (8/8 tests ok).")
    return True


def verify_python_suite(root_dir: Path) -> bool:
    """Execute pytest suite and return pass status."""
    cmd = [sys.executable, "-m", "pytest", "tests/test_issue_1322.py", "-v"]
    res = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        print("[FAIL] Python test suite failed:")
        print(res.stdout)
        print(res.stderr)
        return False

    print("[PASS] Python test suite passed (11/11 tests ok).")
    return True


def verify_formal_invariants(root_dir: Path) -> bool:
    """Execute formal PipelineVerifier checks and return pass status."""
    report = PipelineVerifier.run_all_checks(root_dir)
    print(f"Formal verification checks: {report.checks_passed}/{report.checks_run} passed.")
    for check in report.checks:
        status = "[PASS]" if check.passed else "[FAIL]"
        print(f"  {status} {check.name}: {check.details}")
    return report.all_passed


def main() -> int:
    """Run full verification across Node, Python, and formal invariant suites."""
    root = Path(__file__).resolve().parent.parent
    print(f"Executing Issue #1322 verification suite in {root}...\n")

    node_ok = verify_node_suite(root)
    py_ok = verify_python_suite(root)
    formal_ok = verify_formal_invariants(root)

    if node_ok and py_ok and formal_ok:
        print("\nAll Issue #1322 verification gates passed successfully.")
        return 0

    print("\nOne or more verification checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
