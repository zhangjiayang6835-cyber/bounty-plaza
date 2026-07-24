#!/usr/bin/env python3
"""
End-to-end test for copperhead create pipeline.

This test runs the full pipeline from brief to final stage,
verifying that each stage completes cleanly without errors.

It requires the copperhead CLI and environment to be set up.

Usage:
    python scripts/test_copperhead_create.py
"""

import subprocess
import tempfile
import os
import sys
import shutil

def run_cmd(cmd, cwd=None):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
        sys.exit(result.returncode)
    return result.stdout

def main():
    # Create a temporary directory for the test run
    with tempfile.TemporaryDirectory(prefix="copperhead_test_") as tmpdir:
        print(f"Using temporary directory: {tmpdir}")

        # Define the brief text for the test
        brief = "Test board with a microcontroller and LED"

        # Run copperhead create with the brief
        # This should run all 8 stages and commit each stage independently
        cmd = ["copperhead", "create", "--brief", brief]
        run_cmd(cmd, cwd=tmpdir)

        # Verify that the final stage directory exists and contains expected files
        final_stage_dir = os.path.join(tmpdir, "outputs")
        if not os.path.isdir(final_stage_dir):
            print(f"Error: final stage directory {final_stage_dir} does not exist")
            sys.exit(1)

        # Check for presence of key output files (e.g. KiCad files)
        expected_files = ["board.kicad_pcb", "board.sch"]
        missing_files = []
        for f in expected_files:
            path = os.path.join(final_stage_dir, f)
            if not os.path.isfile(path):
                missing_files.append(f)
        if missing_files:
            print(f"Error: missing expected output files: {missing_files}")
            sys.exit(1)

        print("End-to-end copperhead create test passed cleanly.")

if __name__ == "__main__":
    main()
