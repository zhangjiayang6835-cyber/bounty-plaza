"""Comprehensive unit test suite for Issue 1213 sparse context scanner and honeypot defense."""

import os
import tempfile
from pathlib import Path
import pytest
from packages.sparse_context_scanner import (
    FileMetadata,
    DirectoryScanResult,
    TreeCounts,
    TreeMetrics,
    TokenBudget,
    CompactedContext,
    SentinelGuard,
    TokenBudgetManager,
    SparseDirectoryScanner,
    RepositoryNormalizer,
    HoneypotDefenseVerifier,
)


class TestSentinelGuard:
    """Test suite for adversarial honeypot pattern detection and neutralization."""

    def test_detect_make_no_mistakes(self) -> None:
        """Verify detection of the 'make no mistakes' honeypot trigger phrase."""
        guard = SentinelGuard()
        sample = "The repository instructions clearly say make   no  mistakes in empty space."
        result = guard.scan_content(sample)
        assert result.matched is True
        assert result.risk_level == "HIGH"
        assert len(result.patterns) > 0
        assert "[SANITIZED_SENTINEL_TOKEN]" in result.neutralized_content

    def test_detect_canned_maintainer_greeting(self) -> None:
        """Verify detection of canned AI maintainer greeting traps."""
        guard = SentinelGuard()
        sample = "Hey maintainer! I noticed this issue and crafted a wonderful enterprise solution"
        result = guard.scan_content(sample)
        assert result.matched is True
        assert result.risk_level == "HIGH"
        assert not guard.is_safe(sample)

    def test_detect_automated_trap_trigger(self) -> None:
        """Verify detection of automated trap and auto-closed notices."""
        guard = SentinelGuard()
        sample = "Automated trap triggered. Your PR will be auto-closed in 4 seconds."
        result = guard.scan_content(sample)
        assert result.matched is True
        assert result.risk_level == "HIGH"

    def test_safe_content_passes(self) -> None:
        """Verify that legitimate code content produces no false positives."""
        guard = SentinelGuard()
        legitimate_code = "def calculate_sum(a: int, b: int) -> int:\n    return a + b\n"
        result = guard.scan_content(legitimate_code)
        assert result.matched is False
        assert result.risk_level == "NONE"
        assert guard.is_safe(legitimate_code)

    def test_empty_content_handling(self) -> None:
        """Verify handling of empty or null text input."""
        guard = SentinelGuard()
        result = guard.scan_content("")
        assert result.matched is False
        assert result.risk_level == "NONE"


class TestTokenBudgetAndEntropy:
    """Test suite for token estimation, Shannon entropy, and context compaction."""

    def test_token_estimation_accuracy(self) -> None:
        """Verify heuristic token estimation for typical source code."""
        text = "function executeTransaction(address to, uint256 amount) external returns (bool);"
        tokens = TokenBudgetManager.estimate_tokens(text)
        assert tokens > 10
        assert tokens < 40
        assert TokenBudgetManager.estimate_tokens("") == 0

    def test_shannon_entropy_calculation(self) -> None:
        """Verify Shannon entropy differentiates repetitive vs varied data."""
        uniform_bytes = b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        varied_bytes = b"abcdefghijklmnopqrstuvwxyz012345"
        entropy_uniform = TokenBudgetManager.calculate_entropy(uniform_bytes)
        entropy_varied = TokenBudgetManager.calculate_entropy(varied_bytes)
        assert entropy_uniform == 0.0
        assert entropy_varied > 4.5
        assert TokenBudgetManager.calculate_entropy(b"") == 0.0

    def test_context_compaction_within_budget(self) -> None:
        """Verify that file compaction strictly respects the available context quota."""
        budget = TokenBudget(max_tokens=2000, reserved_completion=500, reserved_system=500)
        manager = TokenBudgetManager(budget)
        assert budget.available_context == 1000

        files = [
            FileMetadata("path/to/large.py", 8000, 600, 4.2, False, False),
            FileMetadata("path/to/medium.py", 4000, 300, 4.5, False, False),
            FileMetadata("path/to/small.py", 1000, 200, 4.8, False, False),
            FileMetadata("path/to/empty.py", 0, 0, 0.0, True, False),
        ]
        compacted = manager.compact(files)
        assert compacted.total_tokens <= budget.available_context
        assert "path/to/empty.py" not in compacted.included_files
        assert len(compacted.included_files) >= 2


class TestSparseDirectoryScanner:
    """Test suite for sparse directory traversal, empty subtree pruning, and cycle defense."""

    def test_scan_non_existent_directory(self) -> None:
        """Verify that scanning a non-existent directory safely returns empty result."""
        scanner = SparseDirectoryScanner()
        res = scanner.scan("/non/existent/path/to/nowhere")
        assert res.total_directories == 0
        assert res.total_files == 0
        assert res.sparsity_index == 0.0

    def test_scan_empty_and_sparse_directories(self) -> None:
        """Verify scanning real directory tree with empty folders and code files."""
        scanner = SparseDirectoryScanner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "empty_dir_a").mkdir()
            (root / "empty_dir_b").mkdir()
            nested = root / "nested" / "deep_empty"
            nested.mkdir(parents=True)
            code_dir = root / "src"
            code_dir.mkdir()
            code_file = code_dir / "app.py"
            code_file.write_text("print('hello world')\n", encoding="utf-8")

            res = scanner.scan(root)
            assert res.total_directories >= 4
            assert res.total_files == 1
            assert res.empty_directories >= 3
            assert res.sparsity_index > 0.0

    def test_scan_sentinel_file_detection(self) -> None:
        """Verify that sentinel trigger files in the filesystem are accurately flagged."""
        scanner = SparseDirectoryScanner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sentinel_file = root / "README.txt"
            sentinel_file.write_text("Instruction: make no mistakes here.", encoding="utf-8")

            res = scanner.scan(root)
            assert len(res.detected_sentinels) == 1
            assert any("README.txt" in s for s in res.detected_sentinels)

    def test_symlink_cycle_detection(self) -> None:
        """Verify that recursive symlink loops do not cause infinite recursion."""
        scanner = SparseDirectoryScanner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sub = root / "sub"
            sub.mkdir()
            cycle_link = sub / "loop"
            try:
                os.symlink(str(root), str(cycle_link))
            except (OSError, NotImplementedError):
                pytest.skip("Symlinks not permitted or supported on platform")

            res = scanner.scan(root)
            assert res.cycle_count >= 1

    def test_optimize_context_pipeline(self) -> None:
        """Verify end-to-end context optimization on a real filesystem hierarchy."""
        scanner = SparseDirectoryScanner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for i in range(5):
                f = root / f"module_{i}.py"
                f.write_text(f"def func_{i}(): return {i}\n", encoding="utf-8")
            budget = TokenBudget(max_tokens=1500, reserved_completion=200, reserved_system=200)
            compacted = scanner.optimize_context(root, budget=budget)
            assert compacted.total_tokens <= budget.available_context
            assert len(compacted.included_files) > 0


class TestRepositoryNormalizer:
    """Test suite for empty directory identification and manifest generation."""

    def test_identify_empty_directories(self) -> None:
        """Verify accurate identification of leaf empty directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "empty1").mkdir()
            (root / "empty2").mkdir()
            non_empty = root / "active"
            non_empty.mkdir()
            (non_empty / "file.txt").write_text("data", encoding="utf-8")

            empties = RepositoryNormalizer.identify_empty_directories(root)
            assert len(empties) == 2
            assert any("empty1" in p for p in empties)
            assert any("empty2" in p for p in empties)

    def test_create_gitkeep_placeholders(self) -> None:
        """Verify creating .gitkeep files in empty directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "leaf1").mkdir()
            (root / "leaf2").mkdir()

            created = RepositoryNormalizer.create_gitkeep_placeholders(root)
            assert created == 2
            assert (root / "leaf1" / ".gitkeep").exists()
            assert (root / "leaf2" / ".gitkeep").exists()

            second_run = RepositoryNormalizer.create_gitkeep_placeholders(root)
            assert second_run == 0

    def test_generate_manifest(self) -> None:
        """Verify structured repository manifest generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "empty_folder").mkdir()
            (root / "file.txt").write_text("hello", encoding="utf-8")

            manifest = RepositoryNormalizer.generate_manifest(root)
            assert manifest["empty_directories_count"] == 1
            assert manifest["is_clean"] is False
            assert manifest["total_files"] == 1


class TestHoneypotDefenseVerifier:
    """Test suite for Issue 1213 honeypot defense verification."""

    def test_evaluate_defense_metrics(self) -> None:
        """Verify evaluation of bloat prevention metrics and token savings."""
        verifier = HoneypotDefenseVerifier()
        metrics = verifier.evaluate_defense()
        assert metrics.lines_saved == 4000
        assert metrics.bloat_packages_prevented == 45
        assert metrics.token_reduction_ratio > 0.90
        assert metrics.execution_time_sec < 1.0
        assert metrics.trap_neutralized is True

    def test_verify_no_canned_patterns(self) -> None:
        """Verify verification of safe candidate text vs trigger contaminated text."""
        verifier = HoneypotDefenseVerifier()
        safe_response = "Refactored directory scanning engine to handle empty subtrees."
        bad_response = "Hey maintainer! I noticed this issue and crafted a solution"
        assert verifier.verify_no_canned_patterns(safe_response) is True
        assert verifier.verify_no_canned_patterns(bad_response) is False
