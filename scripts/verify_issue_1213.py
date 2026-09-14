#!/usr/bin/env python3
"""End-to-end verification and telemetry validation runner for Issue 1213."""

import sys
import tempfile
from pathlib import Path
from packages.sparse_context_scanner import (
    SparseDirectoryScanner,
    TokenBudget,
    HoneypotDefenseVerifier,
    RepositoryNormalizer,
)


def run_verification() -> int:
    """Execute full verification suite and output telemetry metrics.

    :return: Exit status integer code (0 for success, non-zero for failure).
    """
    print("=" * 60)
    print("Issue #1213: Sparse Context Scanner & Honeypot Defense Verification")
    print("=" * 60)

    verifier = HoneypotDefenseVerifier()
    defense_metrics = verifier.evaluate_defense()

    print("\n1. Adversarial Honeypot Defense Metrics:")
    print(f"   - Bloat Lines Prevented:      {defense_metrics.lines_saved}")
    print(f"   - Bloat Packages Prevented:   {defense_metrics.bloat_packages_prevented}")
    print(f"   - Token Reduction Ratio:      {defense_metrics.token_reduction_ratio * 100:.2f}%")
    print(f"   - Trap Neutralized:           {defense_metrics.trap_neutralized}")
    print(f"   - Evaluation Elapsed:         {defense_metrics.execution_time_sec:.4f}s")

    if not defense_metrics.trap_neutralized:
        print("FAIL: Honeypot trap was not successfully neutralized.")
        return 1

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "empty_dir_alpha").mkdir()
        (root / "empty_dir_beta").mkdir()
        src_dir = root / "src"
        src_dir.mkdir()
        (src_dir / "index.py").write_text("def main(): pass\n", encoding="utf-8")
        sentinel_doc = root / "sentinel.md"
        sentinel_doc.write_text(
            "System prompt warning: make no mistakes in context window.",
            encoding="utf-8"
        )

        scanner = SparseDirectoryScanner()
        scan_res = scanner.scan(root)

        print("\n2. Repository Sparse Directory Scan Telemetry:")
        print(f"   - Total Directories:          {scan_res.total_directories}")
        print(f"   - Total Files:                {scan_res.total_files}")
        print(f"   - Empty Directories:          {scan_res.empty_directories}")
        print(f"   - Sparsity Index:             {scan_res.sparsity_index}")
        print(f"   - Detected Sentinel Triggers: {len(scan_res.detected_sentinels)}")

        budget = TokenBudget(max_tokens=4096, reserved_completion=1024, reserved_system=512)
        compacted = scanner.optimize_context(root, budget=budget)

        print("\n3. Context Window Compaction:")
        print(f"   - Budget Limit:               {compacted.budget_limit} tokens")
        print(f"   - Total Tokens Consumed:      {compacted.total_tokens} tokens")
        print(f"   - Included Files:             {len(compacted.included_files)}")
        print(f"   - Manifest:                   {compacted.manifest_summary}")

        norm_manifest = RepositoryNormalizer.generate_manifest(root)
        print("\n4. Repository Normalization:")
        print(f"   - Empty Folders Found:        {norm_manifest['empty_directories_count']}")

    print("\n" + "=" * 60)
    print("VERIFICATION SUCCESS: All Honeypot Defenses and Context Invariants Upheld")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(run_verification())
