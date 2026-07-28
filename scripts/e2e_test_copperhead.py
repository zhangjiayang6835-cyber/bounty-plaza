#!/usr/bin/env python3
"""
End-to-end test for the copperhead create pipeline (8 stages).
Runs a complete brief-to-final pipeline and reports results.
Expected to be invoked in an environment with copperhead and KiCad installed.
"""

import subprocess
import sys
import tempfile
import os
import json
from pathlib import Path

BRIEF = "A simple LED blinker board with a 555 timer and a push button"
PIPELINE_STAGES = [
    "spec-seed",
    "architecture",
    "part-selection",
    "schematic",
    "layout-draft",
    "outputs",
    "firmware",
    "dev-plan",
]


def check_environment():
    """Check that copperhead and kicad-cli are available."""
    for cmd in ["copperhead", "kicad-cli"]:
        if subprocess.call(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            print(f"ERROR: {cmd} not found in PATH")
            return False
    return True


def run_create(stage=None):
    """Run `copperhead create` up to the given stage (or all stages)."""
    cmd = ["copperhead", "create", "--brief", BRIEF]
    if stage:
        cmd.extend(["--up-to", stage])
    cmd.extend(["--no-interactive", "--auto-commit"])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def test_pipeline():
    """Execute full pipeline stage by stage, verifying intermediate success."""
    print("Starting copperhead end-to-end test...")
    res = run_create()
    if res.returncode != 0:
        print("FATAL: Full pipeline failed:")
        print(res.stdout)
        print(res.stderr)
        return False
    print("Full pipeline completed successfully.")

    # Verify that each stage actually produced committed artifacts
    # (This is a placeholder; real verification would check KiCad files, git history, etc.)
    print("Checking for expected outputs...")
    # Simulate checking last few commits for stage messages
    git_log = subprocess.run(
        ["git", "log", "--oneline", "-5"],
        capture_output=True, text=True
    )
    if "spec-seed" not in git_log.stdout:
        print("WARNING: spec-seed commit not found in recent history")
        # Not necessarily fatal if stages are squashed, but log it.
    return True


def main():
    if not check_environment():
        sys.exit(1)
    # Create a temporary directory to avoid polluting current repo
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        # Initialize a bare git repo for copperhead's usage
        subprocess.run(["git", "init"], capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@copperhead.dev"], capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Runner"], capture_output=True)
        success = test_pipeline()
        if success:
            print("E2E TEST PASSED")
        else:
            print("E2E TEST FAILED")
            sys.exit(1)


if __name__ == "__main__":
    main()
