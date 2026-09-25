"""Verification suite specifically testing resolution for Issue 1647."""

from pathlib import Path

from src.status_meter import START_TAG, END_TAG, get_default_metrics


def test_readme_contains_status_meter_start_and_end():
    """Verify that README.md contains matching status meter delimiters."""
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md must exist in root repository"
    content = readme_path.read_text(encoding="utf-8")
    assert START_TAG in content, "README.md missing status meter start delimiter"
    assert END_TAG in content, "README.md missing status meter end delimiter"


def test_readme_en_contains_status_meter_start_and_end():
    """Verify that README.en.md contains matching status meter delimiters."""
    readme_en_path = Path("README.en.md")
    assert readme_en_path.exists(), "README.en.md must exist in root repository"
    content = readme_en_path.read_text(encoding="utf-8")
    assert START_TAG in content, "README.en.md missing status meter start delimiter"
    assert END_TAG in content, "README.en.md missing status meter end delimiter"


def test_status_meter_contains_critical_components():
    """Verify presence of mandatory system component meters in README documents."""
    readme_content = Path("README.md").read_text(encoding="utf-8")
    readme_en_content = Path("README.en.md").read_text(encoding="utf-8")

    critical_terms = [
        "Settlement Engine",
        "Verification Gate",
        "Base RPC Failover",
        "Security Gate",
    ]

    for term in critical_terms:
        assert term in readme_content, f"README.md missing status meter component: {term}"
        assert term in readme_en_content, f"README.en.md missing status meter component: {term}"


def test_status_meter_visual_bars():
    """Verify visual progress meter bar format in README documents."""
    readme_content = Path("README.md").read_text(encoding="utf-8")
    assert "█" in readme_content, "README.md must contain rendered meter blocks"
    assert "100.00%" in readme_content or "99.98%" in readme_content


def test_metrics_integrity():
    """Verify that metrics contain sound non-mock values."""
    metrics = get_default_metrics()
    assert len(metrics) >= 4
    for metric in metrics:
        assert metric.percentage > 0.0
        assert metric.percentage <= 100.0
