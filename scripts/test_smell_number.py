#!/usr/bin/env python3
import json
import subprocess
import sys

def test_smell_number_output():
    result = subprocess.run([sys.executable, "scripts/smell_number.py"], capture_output=True, text=True)
    assert result.returncode == 0, "Script should exit with code 0"
    output = result.stdout.strip()
    data = json.loads(output)
    assert "number" in data, "Output JSON must contain 'number'"
    assert 1 <= data["number"] <= 1_000_000, "Number must be between 1 and 1,000,000"
    assert "smell_description" in data, "Output JSON must contain 'smell_description'"
    assert isinstance(data["smell_description"], str) and len(data["smell_description"]) > 0, "Smell description must be a non-empty string"

if __name__ == "__main__":
    test_smell_number_output()
    print("All tests passed.")
