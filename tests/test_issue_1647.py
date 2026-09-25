# -*- coding: utf-8 -*-
"""Regression test suite for Issue #1647: [Bounty] $1000 DOOLAR BOUNTY IF YOU CAN ADD STATUS METER TO README!!!!1111"""
import os
import sys
try:
    import pytest
except ImportError:
    pytest = None

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_status_meter_import_and_metrics():
    """Verify status meter metrics calculation."""
    from scripts.status_meter import get_bounty_plaza_stats
    stats = get_bounty_plaza_stats()
    assert isinstance(stats, dict)
    assert "total_bounties" in stats
    assert "resolved_bounties" in stats
    assert "success_rate" in stats
    assert stats["total_bounties"] >= stats["resolved_bounties"]
    assert 0 <= stats["success_rate"] <= 100


def test_ascii_meter_rendering_boundaries():
    """Verify ASCII meter rendering at boundary ratios."""
    from scripts.status_meter import render_ascii_meter
    bar_0 = render_ascii_meter(0.0, 10)
    assert "░░░░░░░░░░" in bar_0
    assert "0.0%" in bar_0

    bar_50 = render_ascii_meter(50.0, 10)
    assert "█████░░░░░" in bar_50
    assert "50.0%" in bar_50

    bar_100 = render_ascii_meter(100.0, 10)
    assert "██████████" in bar_100
    assert "100.0%" in bar_100


def test_generate_status_meter_markdown():
    """Verify generated Markdown block adheres to format."""
    from scripts.status_meter import generate_status_meter_block
    block = generate_status_meter_block()
    assert "<!-- START STATUS METER -->" in block
    assert "<!-- END STATUS METER -->" in block
    assert "| 🎯 Total Bounties |" in block
    assert "Status Meter:" in block


def test_readme_injection_and_replacement_safety(tmp_path):
    """Verify safe injection and deduplication in target documents."""
    from scripts.status_meter import update_readme_status_meter
    test_readme = tmp_path / "README.md"
    test_readme.write_text("# Test Project\n\nWelcome to test project.\n", encoding="utf-8")

    ok, _ = update_readme_status_meter(str(test_readme))
    assert ok is True
    content = test_readme.read_text(encoding="utf-8")
    assert "<!-- START STATUS METER -->" in content
    assert "Welcome to test project" in content

    # Second update should cleanly replace rather than duplicate
    ok2, _ = update_readme_status_meter(str(test_readme))
    assert ok2 is True
    content2 = test_readme.read_text(encoding="utf-8")
    assert content2.count("<!-- START STATUS METER -->") == 1


if __name__ == "__main__":
    test_status_meter_import_and_metrics()
    test_ascii_meter_rendering_boundaries()
    test_generate_status_meter_markdown()
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        test_readme_injection_and_replacement_safety(pathlib.Path(td))
    print("All status meter tests passed successfully (4/4 passed)!")
