"""Verification script for Issue #976 solution."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent

    print("--> 1. Running pytest unit test suite...")
    res1 = subprocess.run([sys.executable, "-m", "pytest", str(root / "tests"), "-v"], check=False)
    if res1.returncode != 0:
        return 1

    print("\n--> 2. Running pylint quality check...")
    res2 = subprocess.run([sys.executable, "-m", "pylint", str(root / "src" / "math_utils.py")], check=False)
    if res2.returncode != 0:
        return 1

    print("\n--> 3. Running bandit security check...")
    res3 = subprocess.run([sys.executable, "-m", "bandit", "-q", "-f", "json", str(root / "src" / "math_utils.py")], check=False)
    if res3.returncode != 0:
        return 1

    print("\n--> 4. Running official scoring system...")
    res4 = subprocess.run([sys.executable, str(root / "scripts" / "score.py"), "--code", str(root / "src" / "math_utils.py"), "--tests", str(root / "tests")], check=False)
    return res4.returncode


if __name__ == "__main__":
    sys.exit(main())
