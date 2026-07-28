#!/usr/bin/env python3
"""Memanto Migration Showcase: Prove the full freedom loop (in -> owned -> portable)."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

SAMPLE_MEM0_DATA = [
    {
        "id": "mem1",
        "content": "User prefers dark mode and keyboard shortcuts.",
        "score": 0.95,
        "metadata": {"created_at": "2025-01-15T10:00:00Z", "source": "chat"}
    },
    {
        "id": "mem2",
        "content": "Resolved contradiction: user likes Italian cuisine, not spicy food.",
        "score": 0.87,
        "metadata": {"created_at": "2025-01-16T14:30:00Z", "source": "task"}
    }
]

def run_command(cmd, cwd=None):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr

def main():
    parser = argparse.ArgumentParser(
        description="Showcase Memanto memory migration from Mem0 to portable OKF."
    )
    parser.add_argument("--memanto-path", default="memanto",
                        help="Path to the memanto CLI executable (default: memanto)")
    args = parser.parse_args()

    # 1. Check memanto CLI availability
    ret, out, err = run_command([args.memanto_path, "--version"])
    if ret != 0:
        print("❌ memanto CLI not found. Please install it (pip install memanto).")
        sys.exit(1)
    print(f"✅ Using memanto {out.strip()}")

    # 2. Create a temporary workspace
    workdir = tempfile.mkdtemp(prefix="memanto_showcase_")
    print(f"📁 Working directory: {workdir}")

    try:
        # 3. Write sample Mem0 data
        mem0_file = os.path.join(workdir, "dummy_mem0.json")
        with open(mem0_file, "w") as f:
            json.dump(SAMPLE_MEM0_DATA, f, indent=2)
        print(f"📄 Created sample Mem0 memory file: {mem0_file}")

        # 4. Migrate IN from Mem0
        print("\n🔄 Migrating in from Mem0...")
        ret, out, err = run_command(
            [args.memanto_path, "migrate", "mem0", mem0_file],
            cwd=workdir
        )
        if ret != 0:
            print(f"❌ Migration failed:\n{err}")
            sys.exit(1)
        print("✅ Migration successful.")
        print(out)

        # 5. Export to OKF
        print("\n📦 Exporting memory to portable OKF bundle...")
        okf_dir = os.path.join(workdir, "okf_export")
        os.makedirs(okf_dir, exist_ok=True)
        ret, out, err = run_command(
            [args.memanto_path, "memory", "export", "--okf", okf_dir],
            cwd=workdir
        )
        if ret != 0:
            print(f"❌ Export failed:\n{err}")
            sys.exit(1)
        print("✅ OKF export successful.")
        print(out)

        # 6. Show the exported bundle structure
        print("\n📂 Exported OKF bundle contents:")
        for root, dirs, files in os.walk(okf_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                relpath = os.path.relpath(fpath, okf_dir)
                print(f"  📄 {relpath}")
                # Show first few lines for proof
                with open(fpath) as fh:
                    content = fh.read()
                print(f"     {textwrap.shorten(content, width=80)}")

        print("\n🎉 The Great Memory Migration is complete!")
        print("   Memories were moved from Mem0 -> Memanto -> OKF.")
        print(f"   The portable OKF bundle is at: {okf_dir}")

    finally:
        # Cleanup: remove working directory (or keep if --keep used)
        if not os.environ.get("DEBUG"):  # set DEBUG=1 to keep temp dir
            shutil.rmtree(workdir, ignore_errors=True)
            print(f"\n🧹 Cleaned up temporary directory: {workdir}")
        else:
            print(f"\n🔍 DEBUG mode – keeping temporary directory: {workdir}")

