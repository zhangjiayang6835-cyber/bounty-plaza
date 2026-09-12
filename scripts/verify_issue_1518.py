"""Verification script for Issue #1518: slugify repeated and trailing hyphens."""

from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# pylint: disable=wrong-import-position
from packages.slugify_toolkit.verifier import SlugVerifier


def run_node_tests() -> bool:
    """Executes the Node.js test suite."""
    res = subprocess.run(
        ["node", "--test", "test/slugify.test.js"],
        capture_output=True,
        text=True,
        check=False,
    )
    return res.returncode == 0 and "pass 5" in res.stdout


def main() -> int:
    """Runs all checks and outputs status."""
    print("=== Slugify Verification Report (#1518) ===")
    node_ok = run_node_tests()
    print(f"[{'PASS' if node_ok else 'FAIL'}] Node.js test suite (test/slugify.test.js: 5/5 tests)")

    verifier = SlugVerifier()
    test_cases = [
        ("Hello,   World!!", "hello-world"),
        ("  --Hello World--  ", "hello-world"),
        ("Hello World", "hello-world"),
        ("Café Déjà Vu", "cafe-deja-vu"),
        ("Special @#$% Characters! Here", "special-characters-here"),
    ]
    failures = verifier.verify_matrix(test_cases)
    matrix_ok = len(failures) == 0
    print(f"[{'PASS' if matrix_ok else 'FAIL'}] Slug matrix verification")

    parity_ok = verifier.verify_cross_runtime_parity([tc[0] for tc in test_cases])
    print(f"[{'PASS' if parity_ok else 'FAIL'}] Cross-runtime Node vs Python parity")

    all_passed = node_ok and matrix_ok and parity_ok
    if all_passed:
        print("All verification checks passed successfully.")
        return 0
    print("One or more verification checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
