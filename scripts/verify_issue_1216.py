#!/usr/bin/env python3
"""Verification engine for Issue 1216 CSS flexbox centering and zero-allocation kernel."""

import sys
from pathlib import Path

try:
    from packages.css_kernel.compiler import CssCompiler
    from packages.css_kernel.layout_analyzer import LayoutAnalyzer
    from packages.css_kernel.memory_model import LayoutEngineMemoryModel
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from packages.css_kernel.compiler import CssCompiler
    from packages.css_kernel.layout_analyzer import LayoutAnalyzer
    from packages.css_kernel.memory_model import LayoutEngineMemoryModel


def validate_repository_artifacts(repo_root: Path) -> None:
    """Ensure essential configuration and stylesheet files exist."""
    source_file = repo_root / "styles" / "core.css"
    package_json = repo_root / "package.json"

    if not source_file.exists():
        raise FileNotFoundError("Source stylesheet styles/core.css does not exist")

    if not package_json.exists():
        raise FileNotFoundError("package.json configuration does not exist")


def validate_centering_rules(source_css: str) -> None:
    """Verify bidirectional centering and layout containment."""
    compiler = CssCompiler(source_css)
    center_rule = compiler.find_rule(".center-everything")
    if not center_rule:
        raise ValueError("Target selector .center-everything missing")

    eval_result = LayoutAnalyzer.evaluate_rule(center_rule)
    if not eval_result.fully_centered:
        raise ValueError(".center-everything failed horizontal/vertical centering")

    if not eval_result.layout_isolated:
        raise ValueError(".center-everything failed layout isolation containment")


def run_verification() -> int:
    """Execute validation suite for Issue 1216 CSS kernel specifications."""
    repo_root = (
        Path(__file__).resolve().parent.parent
        if "__file__" in globals()
        else Path.cwd()
    )
    try:
        validate_repository_artifacts(repo_root)
        source_file = repo_root / "styles" / "core.css"
        source_css = source_file.read_text(encoding="utf-8")
        validate_centering_rules(source_css)

        profiles = LayoutEngineMemoryModel.compare_configurations(mutations=1000)
        if profiles["contained_grid"].heap_allocations_bytes != 0:
            raise ValueError("Memory model verification failed for zero-allocation")

        compiler = CssCompiler(source_css)
        minified = compiler.minify()
        dist_dir = repo_root / "dist"
        dist_dir.mkdir(parents=True, exist_ok=True)
        (dist_dir / "core.css").write_text(source_css, encoding="utf-8")
        (dist_dir / "core.min.css").write_text(minified, encoding="utf-8")

        sys.stdout.write("All Issue 1216 checks PASSED: pure CSS centering verified\n")
        return 0
    except (FileNotFoundError, ValueError) as err:
        sys.stderr.write(f"Verification error: {err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_verification())
