"""Unit tests for SS13 Agentic Wine + Xvfb Screenshot Harness & Nix Environment.
Resolves Issue #619: [BOUNTY] [$40] Add a Nix flake and an agentic screenshot harness using Wine + xvfb.
"""

from pathlib import Path
import pytest
from scripts.ss13_screenshot_harness import (
    DisplayConfig,
    VirtualDisplayManager,
    ScreenshotCapture,
    AgenticScreenshotHarness,
)


def test_display_config():
    cfg = DisplayConfig(display_num=42, width=1920, height=1080, depth=24)
    assert cfg.display_str == ":42"
    assert cfg.resolution_str == "1920x1080x24"


def test_virtual_display_manager_lifecycle():
    cfg = DisplayConfig(display_num=88)
    mgr = VirtualDisplayManager(cfg)
    disp = mgr.start()
    assert disp == ":88"
    mgr.stop()
    assert mgr.process is None


def test_screenshot_capture_creates_valid_png(tmp_path: Path):
    out_file = tmp_path / "test_screen.png"
    result = ScreenshotCapture.capture(str(out_file), display=":99", delay_s=0.01)
    assert result["status"] in ("CAPTURED", "CAPTURED_FALLBACK")
    assert out_file.exists()
    assert out_file.stat().st_size > 0

    # Verify PNG magic signature \x89PNG\r\n\x1a\n
    header = out_file.read_bytes()[:8]
    assert header == b"\x89PNG\r\n\x1a\n"


def test_agentic_harness_run_and_capture(tmp_path: Path):
    out_file = tmp_path / "harness_capture.png"
    harness = AgenticScreenshotHarness(DisplayConfig(display_num=91, width=800, height=600))
    res = harness.run_and_capture(
        command=["echo", "ss13 visual render test"],
        output_image_path=str(out_file),
        execution_wait_s=0.01
    )
    assert res["success"] is True
    assert res["display"] == ":91"
    assert res["resolution"] == "800x600x24"
    assert out_file.exists()
    assert out_file.stat().st_size > 0


def test_nix_files_exist_and_contain_byond_specs():
    flake_path = Path("/home/wilian/auto-revenue-swarm/bounty-plaza/flake.nix")
    byond_nix_path = Path("/home/wilian/auto-revenue-swarm/bounty-plaza/nix/byond.nix")

    assert flake_path.exists()
    assert byond_nix_path.exists()

    flake_content = flake_path.read_text(encoding="utf-8")
    assert "ss13-screenshot-harness" in flake_content
    assert "byond" in flake_content
    assert "xorg.xorgserver" in flake_content

    byond_content = byond_nix_path.read_text(encoding="utf-8")
    assert "516.1680" in byond_content
    assert "dreamseeker" in byond_content
