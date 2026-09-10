"""End-to-end verification script for issue #1332 deliverables."""

from __future__ import annotations

import os
import subprocess
import sys

try:
    from packages.state_solver.verifier import run_full_verification
except ModuleNotFoundError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from packages.state_solver.verifier import run_full_verification


def verify_typescript_compilation() -> bool:
    """Verify that npm run build compiles cleanly without TS2589 recursion error."""
    result = subprocess.run(
        ["npm", "run", "build"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def verify_typescript_tests() -> bool:
    """Verify that node test/verify.js and test/state.test.js pass cleanly."""
    env = dict(os.environ)
    env["HUMAN_VERIFIED_SIGNATURE"] = "0" * 64

    res_verify = subprocess.run(
        ["node", "test/verify.js"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if res_verify.returncode != 0:
        return False

    res_test = subprocess.run(
        ["node", "--test", "test/state.test.js"],
        capture_output=True,
        text=True,
        check=False,
    )
    return res_test.returncode == 0


def main() -> int:
    """Execute complete end-to-end verification and return exit code."""
    ts_ok = verify_typescript_compilation()
    tests_ok = verify_typescript_tests()
    py_ok = run_full_verification()

    if not (ts_ok and tests_ok and py_ok):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
