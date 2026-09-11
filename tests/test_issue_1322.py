"""
Comprehensive pytest test suite for Issue #1322 Bedrock template expansion pipeline.
"""

import json
from pathlib import Path
import shutil
import pytest

from packages.bedrock_template_pipeline.expander import BedrockTemplateExpander
from packages.bedrock_template_pipeline.pipeline import (
    BedrockBuildPipeline,
    BuildResult,
)
from packages.bedrock_template_pipeline.synchronizer import (
    DirectorySynchronizer,
    SyncStats,
)
from packages.bedrock_template_pipeline.validator import (
    BedrockPackValidator,
    ValidationReport,
)
from packages.bedrock_template_pipeline.verifier import PipelineVerifier


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def test_bds_syntax_error_reproduced_on_unexpanded_source() -> None:
    """Verify validator reproduces BDS syntax error on unexpanded custom_stair.json."""
    source_dir = WORKSPACE_ROOT / "packs" / "behavior_pack"
    assert source_dir.is_dir(), f"Missing behavior pack directory at {source_dir}"

    stair_file = source_dir / "blocks" / "custom_stair.json"
    assert stair_file.is_file()
    content = stair_file.read_text(encoding="utf-8")
    assert "{{#template" in content

    report = BedrockPackValidator.validate_pack(source_dir)
    assert report.valid is False
    assert len(report.errors) > 0

    stair_errors = [e for e in report.errors if "custom_stair.json" in e]
    assert len(stair_errors) > 0
    assert "line 4 column 12" in stair_errors[0]
    assert "unexpected character '{'" in stair_errors[0]


def test_pipeline_clean_slate_invariant(tmp_path: Path) -> None:
    """Verify clean-slate wipe purges stale template cache before staging."""
    source_dir = WORKSPACE_ROOT / "packs" / "behavior_pack"
    staging_base = tmp_path / "_temp"
    dest_dir = tmp_path / "dist"

    stale_file = staging_base / "behavior_pack" / "blocks" / "stale_contaminated.json"
    stale_file.parent.mkdir(parents=True, exist_ok=True)
    stale_file.write_text('{"format_version":"1.20.80"}', encoding="utf-8")
    assert stale_file.is_file()

    pipeline = BedrockBuildPipeline(
        source_dir=source_dir,
        staging_base=staging_base,
        dest_dir=dest_dir,
        template_dir=WORKSPACE_ROOT / "templates",
        clean_slate=True,
    )
    result = pipeline.run()
    assert result.success is True
    assert not stale_file.is_file()
    assert not (dest_dir / "blocks" / "stale_contaminated.json").is_file()


def test_pipeline_execution_order_stages_before_sync(tmp_path: Path) -> None:
    """Verify expansion executes in isolated staging before destination synchronization."""
    source_dir = WORKSPACE_ROOT / "packs" / "behavior_pack"
    staging_base = tmp_path / "_temp_order"
    dest_dir = tmp_path / "dist_order"

    pipeline = BedrockBuildPipeline(
        source_dir=source_dir,
        staging_base=staging_base,
        dest_dir=dest_dir,
        template_dir=WORKSPACE_ROOT / "templates",
        clean_slate=True,
    )
    result = pipeline.run()
    assert result.success is True
    assert result.staging.expanded_count >= 2
    assert result.staging.copied_count >= 2
    assert result.validation.valid is True
    assert result.sync.copied >= 4

    deployed_report = BedrockPackValidator.validate_pack(dest_dir)
    assert deployed_report.valid is True
    assert len(deployed_report.errors) == 0


def test_template_expander_includes_and_fragments() -> None:
    """Verify BedrockTemplateExpander resolves template includes and fragments."""
    expander = BedrockTemplateExpander(template_dir=WORKSPACE_ROOT / "templates")
    fragment = expander.load_fragment("stair_components")
    assert '"description"' in fragment
    assert '"permutations"' in fragment

    raw_template = (
        '{\n'
        '  "format_version": "1.20.80",\n'
        '  "minecraft:block": {\n'
        '    {{#template "stair_components"}}\n'
        '  }\n'
        '}'
    )
    expanded = expander.expand(raw_template, "test_stair.json")
    data = json.loads(expanded)
    assert data.get("format_version") == "1.20.80"
    assert "minecraft:block" in data
    assert "description" in data["minecraft:block"]


def test_template_expander_variable_and_jinja_directives() -> None:
    """Verify variable interpolation and Jinja set directives in template expander."""
    expander = BedrockTemplateExpander(
        template_dir=WORKSPACE_ROOT / "templates",
        default_context={"custom_sound": "stone"},
    )
    raw = (
        '{\n'
        '  "format_version": "1.20.80",\n'
        '  {% set custom_key = "special_val" %}\n'
        '  "minecraft:block": {\n'
        '    "description": { "identifier": "tank:{{custom_key}}" },\n'
        '    "components": { "sound": "{{custom_sound}}" }\n'
        '  }\n'
        '}'
    )
    expanded = expander.expand(raw, "variable_test.json")
    data = json.loads(expanded)
    assert data["minecraft:block"]["description"]["identifier"] == "tank:special_val"
    assert data["minecraft:block"]["components"]["sound"] == "stone"


def test_template_expander_scope_and_metadata_pruning() -> None:
    """Verify JSONTE $scope block parameter merging and metadata removal."""
    source_slab = (WORKSPACE_ROOT / "packs" / "behavior_pack" / "blocks" / "custom_slab.json").read_text(
        encoding="utf-8"
    )
    expander = BedrockTemplateExpander(template_dir=WORKSPACE_ROOT / "templates")
    expanded = expander.expand(source_slab, "custom_slab.json")

    assert "$scope" not in expanded
    assert "{{" not in expanded
    assert "}}" not in expanded

    data = json.loads(expanded)
    desc = data["minecraft:block"]["description"]
    assert desc["identifier"] == "tank:custom_slab"
    assert (
        data["minecraft:block"]["components"]["minecraft:material_instances"]["*"]["texture"]
        == "custom_slab_texture"
    )


def test_pack_validator_schema_checks(tmp_path: Path) -> None:
    """Verify pack validator enforces Bedrock format_version and namespace standards."""
    bad_pack = tmp_path / "bad_pack"
    bad_pack.mkdir()

    no_fmt = bad_pack / "no_format.json"
    no_fmt.write_text('{"minecraft:block": {}}', encoding="utf-8")

    no_ns = bad_pack / "no_namespace.json"
    no_ns.write_text(
        '{"format_version": "1.20.80", "minecraft:block": {"description": {"identifier": "invalid_id"}}}',
        encoding="utf-8",
    )

    report = BedrockPackValidator.validate_pack(bad_pack)
    assert report.valid is False
    assert any("Missing 'format_version'" in e for e in report.errors)
    assert any("must contain namespace" in e for e in report.errors)


def test_directory_synchronizer_delta_and_pruning(tmp_path: Path) -> None:
    """Verify DirectorySynchronizer copies changed files and deletes orphan files."""
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    dest.mkdir()

    file_a = src / "a.txt"
    file_a.write_text("hello", encoding="utf-8")
    orphan = dest / "orphan.txt"
    orphan.write_text("old", encoding="utf-8")

    stats1 = DirectorySynchronizer.synchronize(src, dest, clean=True)
    assert stats1.copied == 1
    assert stats1.removed == 1
    assert not orphan.exists()
    assert (dest / "a.txt").read_text(encoding="utf-8") == "hello"

    stats2 = DirectorySynchronizer.synchronize(src, dest, clean=True)
    assert stats2.copied == 0
    assert stats2.unchanged == 1
    assert stats2.removed == 0


def test_expanded_custom_stair_and_slab_invariants(tmp_path: Path) -> None:
    """Verify deployed custom_stair and custom_slab conform to Bedrock 1.20.80 schema."""
    dest_dir = tmp_path / "dist"
    pipeline = BedrockBuildPipeline(
        source_dir=WORKSPACE_ROOT / "packs" / "behavior_pack",
        staging_base=tmp_path / "_temp",
        dest_dir=dest_dir,
        template_dir=WORKSPACE_ROOT / "templates",
        clean_slate=True,
    )
    pipeline.run()

    stair_path = dest_dir / "blocks" / "custom_stair.json"
    assert stair_path.is_file()
    stair_data = json.loads(stair_path.read_text(encoding="utf-8"))
    assert stair_data["format_version"] == "1.20.80"
    stair_block = stair_data["minecraft:block"]
    assert stair_block["description"]["identifier"] == "tank:custom_stair"
    assert len(stair_block["permutations"]) == 5

    slab_path = dest_dir / "blocks" / "custom_slab.json"
    assert slab_path.is_file()
    slab_data = json.loads(slab_path.read_text(encoding="utf-8"))
    assert slab_data["format_version"] == "1.20.80"
    slab_block = slab_data["minecraft:block"]
    assert slab_block["description"]["identifier"] == "tank:custom_slab"
    assert (
        slab_block["components"]["minecraft:material_instances"]["*"]["texture"]
        == "custom_slab_texture"
    )


def test_static_asset_byte_preservation(tmp_path: Path) -> None:
    """Verify manifest and static item assets retain exact byte preservation."""
    dest_dir = tmp_path / "dist"
    pipeline = BedrockBuildPipeline(
        source_dir=WORKSPACE_ROOT / "packs" / "behavior_pack",
        staging_base=tmp_path / "_temp",
        dest_dir=dest_dir,
        template_dir=WORKSPACE_ROOT / "templates",
        clean_slate=True,
    )
    pipeline.run()

    src_manifest = (WORKSPACE_ROOT / "packs" / "behavior_pack" / "manifest.json").read_bytes()
    dest_manifest = (dest_dir / "manifest.json").read_bytes()
    assert src_manifest == dest_manifest

    src_wrench = (
        WORKSPACE_ROOT / "packs" / "behavior_pack" / "items" / "mannequin_wrench.json"
    ).read_bytes()
    dest_wrench = (dest_dir / "items" / "mannequin_wrench.json").read_bytes()
    assert src_wrench == dest_wrench


def test_formal_verifier_all_checks_pass() -> None:
    """Verify PipelineVerifier formal verification suite executes and passes all checks."""
    report = PipelineVerifier.run_all_checks(WORKSPACE_ROOT)
    assert report.all_passed is True
    assert report.checks_run == 6
    assert report.checks_passed == 6
    for check in report.checks:
        assert check.passed is True
