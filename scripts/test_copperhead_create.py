#!/usr/bin/env python3
"""
End-to-end test for copperhead create pipeline.

This test runs the full pipeline from brief to final stage,
verifying that each stage completes cleanly without errors.

Usage:
    python scripts/test_copperhead_create.py

Requirements:
- copperhead CLI installed and in PATH
- A test brief file named test_brief.txt in the same directory
"""

import subprocess
import sys
import os

def run_stage(stage_name, args):
    print(f"Running stage: {stage_name} with args: {args}")
    result = subprocess.run(["copperhead", "create"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Stage {stage_name} failed with exit code {result.returncode}")
        print("STDOUT:")
        print(result.stdout)
        print("STDERR:")
        print(result.stderr)
        sys.exit(1)
    else:
        print(f"Stage {stage_name} completed successfully.")

def main():
    # Path to the brief file
    brief_file = os.path.join(os.path.dirname(__file__), "test_brief.txt")
    if not os.path.isfile(brief_file):
        print(f"Test brief file not found: {brief_file}")
        sys.exit(1)

    # Define the stages in order with their arguments
    stages = [
        ("spec-seed", ["spec-seed", "--brief", brief_file]),
        ("architecture", ["architecture"]),
        ("part-selection", ["part-selection"]),
        ("schematic", ["schematic"]),
        ("layout-draft", ["layout-draft"]),
        ("outputs", ["outputs"]),
        ("firmware", ["firmware"]),
        ("dev-plan", ["dev-plan"]),
    ]

    # Run each stage sequentially
    for stage_name, args in stages:
        run_stage(stage_name, args)

    print("All stages completed successfully.")

if __name__ == "__main__":
    main()
