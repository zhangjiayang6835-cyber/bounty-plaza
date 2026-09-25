"""Unit tests for platform status meter module."""

import json
from pathlib import Path

from src.status_meter import (
    START_TAG,
    END_TAG,
    StatusMetric,
    generate_progress_bar,
    get_default_metrics,
    load_metrics_from_config,
    format_markdown_table,
    build_status_section,
    inject_status_meter,
    update_readme,
)
from scripts.status_meter import run_check, update_target_file


def test_generate_progress_bar_zero():
    """Verify progress meter output for zero percentage."""
    result = generate_progress_bar(0.0, width=10)
    assert result == "[░░░░░░░░░░] 0.00%"


def test_generate_progress_bar_hundred():
    """Verify progress meter output for 100 percentage."""
    result = generate_progress_bar(100.0, width=10)
    assert result == "[██████████] 100.00%"


def test_generate_progress_bar_half():
    """Verify progress meter output for 50 percentage."""
    result = generate_progress_bar(50.0, width=10)
    assert result == "[█████░░░░░] 50.00%"


def test_generate_progress_bar_clamping():
    """Verify out-of-range percentage values are clamped between 0 and 100."""
    neg_res = generate_progress_bar(-25.0, width=10)
    assert neg_res == "[░░░░░░░░░░] 0.00%"

    high_res = generate_progress_bar(150.0, width=10)
    assert high_res == "[██████████] 100.00%"


def test_generate_progress_bar_custom_chars():
    """Verify progress meter with customized visual characters."""
    res = generate_progress_bar(50.0, width=6, fill_char="#", empty_char="-")
    assert res == "[###---] 50.00%"


def test_get_default_metrics_structure():
    """Verify structure and validity of default metrics list."""
    metrics = get_default_metrics()
    assert len(metrics) >= 5
    for item in metrics:
        assert isinstance(item, StatusMetric)
        assert item.name
        assert item.status in ("OPERATIONAL", "ACTIVE", "OPTIMAL", "VERIFIED")
        assert 0.0 <= item.percentage <= 100.0
        assert item.details


def test_load_metrics_from_config_defaults(tmp_path: Path):
    """Verify fallback to defaults when configuration file does not exist."""
    non_existent = tmp_path / "missing.json"
    metrics = load_metrics_from_config(non_existent)
    assert len(metrics) >= 5
    assert any(m.name == "Settlement Engine" for m in metrics)


def test_load_metrics_from_config_custom(tmp_path: Path):
    """Verify proper metric extraction from structured JSON configuration."""
    cfg_file = tmp_path / "config.json"
    sample_data = {
        "payout_conditions": ["rule1", "rule2"],
        "pricing": {"tiers": [{"max": 100}, {"max": 500}]},
        "platforms": ["github.com", "custom.org"],
    }
    cfg_file.write_text(json.dumps(sample_data), encoding="utf-8")

    metrics = load_metrics_from_config(cfg_file)
    assert len(metrics) == 6
    ingestion_metric = next(m for m in metrics if m.name == "Platform Ingestion")
    assert "github.com" in ingestion_metric.details


def test_load_metrics_from_config_corrupted(tmp_path: Path):
    """Verify graceful fallback when configuration contains invalid JSON syntax."""
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("NOT_JSON{", encoding="utf-8")
    metrics = load_metrics_from_config(corrupt_file)
    assert len(metrics) >= 5


def test_format_markdown_table_english():
    """Verify markdown table formatting with English headers."""
    metrics = [
        StatusMetric("Node A", "OPERATIONAL", 100.0, "Details A", "infra"),
    ]
    table = format_markdown_table(metrics, locale="en")
    assert "| Component | Status | Meter | Value | Details |" in table
    assert "| Node A | `OPERATIONAL` |" in table


def test_format_markdown_table_chinese():
    """Verify markdown table formatting with Chinese headers."""
    metrics = [
        StatusMetric("Node B", "OPTIMAL", 99.9, "Details B", "infra"),
    ]
    table = format_markdown_table(metrics, locale="zh")
    assert "| 组件 / 服务 | 状态 | 运行指示计 | 指标值 | 详情说明 |" in table
    assert "| Node B | `OPTIMAL` |" in table


def test_build_status_section_markers():
    """Verify that build_status_section wraps content inside delimiter markers."""
    block = build_status_section(locale="en")
    assert block.startswith(START_TAG)
    assert block.endswith(END_TAG)
    assert "## Platform Status Meter" in block


def test_inject_status_meter_fresh():
    """Verify injection into document that lacks existing status markers."""
    doc = "# Platform\n\nIntro text.\n\n## Section 1\n\nSection body."
    block = build_status_section(locale="en")
    injected = inject_status_meter(doc, block)
    assert START_TAG in injected
    assert END_TAG in injected
    assert "Intro text." in injected
    assert "## Section 1" in injected


def test_inject_status_meter_replacement():
    """Verify replacement of existing status meter block between markers."""
    doc = f"# Title\n\n{START_TAG}\nOld Content\n{END_TAG}\n\n## Next Section"
    new_block = build_status_section(locale="en")
    updated = inject_status_meter(doc, new_block)
    assert "Old Content" not in updated
    assert START_TAG in updated
    assert END_TAG in updated
    assert "## Next Section" in updated


def test_update_readme_missing_file(tmp_path: Path):
    """Verify update_readme returns False when target file does not exist."""
    non_existent = tmp_path / "no_file.md"
    success = update_readme(non_existent)
    assert not success


def test_update_readme_success(tmp_path: Path):
    """Verify successful file modification by update_readme."""
    target_file = tmp_path / "README_TEST.md"
    target_file.write_text("# Test Title\n\n## Existing Section\nText", encoding="utf-8")
    success = update_readme(target_file, locale="en")
    assert success
    saved_content = target_file.read_text(encoding="utf-8")
    assert START_TAG in saved_content
    assert END_TAG in saved_content


def test_scripts_status_meter_run_check(tmp_path: Path):
    """Verify CLI helper run_check detects presence of markers."""
    valid_file = tmp_path / "valid.md"
    valid_file.write_text(f"# Doc\n{START_TAG}\nContent\n{END_TAG}\n", encoding="utf-8")
    assert run_check(valid_file)

    invalid_file = tmp_path / "invalid.md"
    invalid_file.write_text("# Doc without markers", encoding="utf-8")
    assert not run_check(invalid_file)

    missing_file = tmp_path / "missing.md"
    assert not run_check(missing_file)


def test_scripts_status_meter_update_target(tmp_path: Path):
    """Verify CLI helper update_target_file applies updates."""
    doc = tmp_path / "target.md"
    doc.write_text("# Header\n\n## Details", encoding="utf-8")
    success = update_target_file(doc, "en")
    assert success
    content = doc.read_text(encoding="utf-8")
    assert START_TAG in content
