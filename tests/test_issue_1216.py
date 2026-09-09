"""Test suite for Issue 1216 zero-allocation pure CSS centering subsystem."""

import subprocess
from pathlib import Path
from packages.css_kernel.compiler import CssCompiler, CssParser
from packages.css_kernel.layout_analyzer import LayoutAnalyzer
from packages.css_kernel.memory_model import LayoutEngineMemoryModel


REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_CSS_PATH = REPO_ROOT / "styles" / "core.css"
PACKAGE_JSON_PATH = REPO_ROOT / "package.json"


def test_css_source_file_exists() -> None:
    """Verify styles/core.css exists and contains valid styling text."""
    assert SOURCE_CSS_PATH.exists()
    content = SOURCE_CSS_PATH.read_text(encoding="utf-8")
    assert len(content.strip()) > 50


def test_package_json_configuration() -> None:
    """Verify package.json specifies build-css-kernel compilation script."""
    assert PACKAGE_JSON_PATH.exists()
    content = PACKAGE_JSON_PATH.read_text(encoding="utf-8")
    assert "build-css-kernel" in content
    assert "node scripts/build-css-kernel.js" in content


def test_center_everything_rule_present() -> None:
    """Verify .center-everything rule is defined in stylesheet."""
    css_text = SOURCE_CSS_PATH.read_text(encoding="utf-8")
    compiler = CssCompiler(css_text)
    rule = compiler.find_rule(".center-everything")
    assert rule is not None
    assert rule.selector == ".center-everything"


def test_center_everything_bidirectional_centering() -> None:
    """Verify .center-everything centers both horizontally and vertically."""
    css_text = SOURCE_CSS_PATH.read_text(encoding="utf-8")
    compiler = CssCompiler(css_text)
    rule = compiler.find_rule(".center-everything")
    assert rule is not None
    result = LayoutAnalyzer.evaluate_rule(rule)
    assert result.horizontal_centered is True
    assert result.vertical_centered is True
    assert result.fully_centered is True


def test_center_everything_layout_containment() -> None:
    """Verify .center-everything declares layout and paint containment."""
    css_text = SOURCE_CSS_PATH.read_text(encoding="utf-8")
    compiler = CssCompiler(css_text)
    rule = compiler.find_rule(".center-everything")
    assert rule is not None
    result = LayoutAnalyzer.evaluate_rule(rule)
    assert result.layout_isolated is True
    assert result.zero_allocation_compliant is True


def test_center_everything_hardware_acceleration() -> None:
    """Verify .center-everything leverages compositing hints."""
    css_text = SOURCE_CSS_PATH.read_text(encoding="utf-8")
    compiler = CssCompiler(css_text)
    rule = compiler.find_rule(".center-everything")
    assert rule is not None
    result = LayoutAnalyzer.evaluate_rule(rule)
    assert result.hardware_composited is True


def test_center_container_spec() -> None:
    """Verify .center-container specifies dimensional bounds and centering."""
    css_text = SOURCE_CSS_PATH.read_text(encoding="utf-8")
    compiler = CssCompiler(css_text)
    rule = compiler.find_rule(".center-container")
    assert rule is not None
    assert rule.get_property("display") == "grid"
    assert rule.get_property("width") == "100%"
    assert rule.get_property("height") == "100%"


def test_alternative_centering_mechanisms() -> None:
    """Verify alternative zero-allocation centering patterns in stylesheet."""
    css_text = SOURCE_CSS_PATH.read_text(encoding="utf-8")
    compiler = CssCompiler(css_text)
    inset_rule = compiler.find_rule(".center-inset")
    assert inset_rule is not None
    result = LayoutAnalyzer.evaluate_rule(inset_rule)
    assert result.fully_centered is True

    abs_rule = compiler.find_rule(".center-absolute")
    assert abs_rule is not None
    result_abs = LayoutAnalyzer.evaluate_rule(abs_rule)
    assert result_abs.fully_centered is True


def test_css_parser_comment_stripping() -> None:
    """Verify CssParser removes block comments without corrupting declarations."""
    raw = "/* Header */ .box { color: blue; /* inline */ margin: 0; }"
    clean = CssParser.strip_comments(raw)
    assert "/*" not in clean
    assert ".box" in clean
    assert "margin: 0" in clean


def test_css_parser_declaration_extraction() -> None:
    """Verify CssParser correctly extracts property names and values."""
    raw = ".demo { display: grid; align-items: center; justify-items: center; }"
    rules = CssParser.parse_rules(raw)
    assert len(rules) == 1
    assert rules[0].get_property("display") == "grid"
    assert rules[0].get_property("align-items") == "center"
    assert rules[0].get_property("justify-items") == "center"


def test_css_compiler_minification() -> None:
    """Verify CssCompiler minifies CSS source code cleanly."""
    raw = "  .demo {\n    color: red;\n    margin: 10px;\n  }\n"
    compiler = CssCompiler(raw)
    minified = compiler.minify()
    assert minified == ".demo{color:red;margin:10px}"


def test_layout_analyzer_grid_evaluation() -> None:
    """Verify LayoutAnalyzer evaluates pure CSS Grid centering."""
    raw = ".grid-center { display: grid; place-items: center; contain: layout paint; }"
    rules = CssParser.parse_rules(raw)
    result = LayoutAnalyzer.evaluate_rule(rules[0])
    assert result.fully_centered is True
    assert result.layout_isolated is True
    assert result.zero_allocation_compliant is True


def test_layout_analyzer_flex_evaluation() -> None:
    """Verify LayoutAnalyzer evaluates CSS Flexbox centering."""
    raw = ".flex-center { display: flex; justify-content: center; align-items: center; }"
    rules = CssParser.parse_rules(raw)
    result = LayoutAnalyzer.evaluate_rule(rules[0])
    assert result.fully_centered is True
    assert result.layout_isolated is False
    assert result.zero_allocation_compliant is False


def test_layout_engine_memory_model_containment() -> None:
    """Verify layout containment produces zero cross-boundary heap allocations."""
    profile = LayoutEngineMemoryModel.simulate_thrashing_cycle(
        layout_type="grid", is_contained=True, mutations_count=5000
    )
    assert profile.heap_allocations_bytes == 0
    assert profile.reflow_passes == 1
    assert profile.frame_rate_fps == 60


def test_layout_engine_memory_model_thrashing_comparison() -> None:
    """Verify contained layout eliminates uncontained reflow overhead."""
    profiles = LayoutEngineMemoryModel.compare_configurations(mutations=1000)
    uncontained = profiles["uncontained_flexbox"]
    contained = profiles["contained_grid"]

    assert uncontained.heap_allocations_bytes > 0
    assert contained.heap_allocations_bytes == 0
    assert contained.frame_rate_fps > uncontained.frame_rate_fps


def test_node_build_css_kernel_execution() -> None:
    """Verify npm run build-css-kernel executes successfully and emits dist files."""
    result = subprocess.run(
        ["npm", "run", "build-css-kernel"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0
    assert "BUILD SUCCESS" in result.stdout

    dist_css = REPO_ROOT / "dist" / "core.css"
    dist_min = REPO_ROOT / "dist" / "core.min.css"
    assert dist_css.exists()
    assert dist_min.exists()
    assert dist_min.stat().st_size <= dist_css.stat().st_size


def test_no_javascript_injection_in_css() -> None:
    """Verify CSS file contains pure declarative CSS with zero script execution."""
    content = SOURCE_CSS_PATH.read_text(encoding="utf-8").lower()
    assert "javascript:" not in content
    assert "expression(" not in content
    assert "<script" not in content
    assert "@import" not in content
