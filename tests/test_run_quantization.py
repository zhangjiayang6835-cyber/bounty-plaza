import subprocess
import sys
from pathlib import Path

def test_quantization_runs():
    # Run the script with custom shape and zero-point
    result = subprocess.run([
        sys.executable,
        "run_quantization.py",
        "--zero-point",
        "127.0",
        "--scale",
        "0.5",
        "--shape",
        "1", "16", "64", "64"
    ], capture_output=True, text=True, check=False)
    
    # The script should exit with code 0.
    assert result.returncode == 0, f"Non‑zero exit: {result.returncode}\n{result.stderr}"
    
    # stdout must contain at least one non‑empty line.
    output = result.stdout.strip()
    assert output, "Script produced empty output"
    assert "[Dummy execution]" in output, "Expected dummy output string was not found"
