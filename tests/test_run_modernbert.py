import subprocess
import sys
from pathlib import Path

def test_modernbert_runs():
    # Run the script with a simple input; we allow dummy mode.
    result = subprocess.run([
        sys.executable,
        "run_modernbert.py",
        "--input",
        "Hello World",
        "--seq-length",
        "32"
    ], capture_output=True, text=True, check=False)
    
    # The script should exit with code 0.
    assert result.returncode == 0, f"Non‑zero exit: {result.returncode}\n{result.stderr}"
    
    # stdout must contain at least one non‑empty line.
    output = result.stdout.strip()
    assert output, "Script produced empty output"
    assert "[Dummy embeddings]" in output, "Expected dummy output string was not found"
