import subprocess
import sys
from pathlib import Path

def test_gemma2_runs():
    # Run the script with a simple prompt; we allow dummy mode.
    result = subprocess.run([
        sys.executable,
        "run_gemma2.py",
        "--prompt",
        "Hello",
    ], capture_output=True, text=True, check=False)
    # The script should exit with code 0.
    assert result.returncode == 0, f"Non‑zero exit: {result.returncode}\n{result.stderr}"
    # stdout must contain at least one non‑empty line.
    output = result.stdout.strip()
    assert output, "Script produced empty output"
