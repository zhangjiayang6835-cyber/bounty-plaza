"""Comprehensive unit and integration test suite for Bedrock template compiler (Issue #1207)."""

import json
import os
import shutil
import tempfile
from typing import Generator

import pytest

from packages.bedrock_template_compiler import (
    BedrockBuildPipeline,
    JsonteCompilationError,
    JsonteCompiler,
    calculate_file_hash,
    compile_sound_definitions,
    deep_merge,
    derive_sound_category,
    normalize_sound_reference,
    snapshot_directory_hashes,
    strip_json_comments,
    validate_deployment,
)


@pytest.fixture
def temp_workspace() -> Generator[str, None, None]:
    """Provide an isolated temporary workspace directory."""
    path = tempfile.mkdtemp(prefix="bedrock_test_")
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_strip_json_comments_preserves_strings_and_removes_comments():
    """Verify comments are removed while strings with slashes remain untouched."""
    raw = """{
        // Leading comment
        "url": "http://minecraft.net/addon", /* inline comment */
        "comment_inside": "text with // and /* */ intact",
        "nested": {
            "key": "value", // trailing comment
        },
    }"""
    cleaned = strip_json_comments(raw)
    parsed = json.loads(cleaned)
    assert parsed["url"] == "http://minecraft.net/addon"
    assert parsed["comment_inside"] == "text with // and /* */ intact"
    assert parsed["nested"]["key"] == "value"


def test_deep_merge_recursive_overrides():
    """Verify deep merge updates nested dictionaries and child primitives."""
    base = {
        "format_version": "1.20.0",
        "minecraft:item": {
            "description": {"identifier": "custom:base", "category": "Items"},
            "components": {"minecraft:max_stack_size": 64},
        },
    }
    child = {
        "minecraft:item": {
            "description": {"identifier": "custom:override"},
            "components": {"minecraft:hand_equipped": True},
        },
    }
    merged = deep_merge(base, child)
    assert merged["minecraft:item"]["description"]["identifier"] == "custom:override"
    assert merged["minecraft:item"]["description"]["category"] == "Items"
    assert merged["minecraft:item"]["components"]["minecraft:max_stack_size"] == 64
    assert merged["minecraft:item"]["components"]["minecraft:hand_equipped"] is True


def test_jsonte_compiler_variable_interpolation_and_type_preservation():
    """Verify Mustache variables interpolate and preserve native JSON types."""
    compiler = JsonteCompiler()
    raw = """{
        "$scope": {
            "item_id": "amethyst_sword",
            "damage_val": 12,
            "is_enchanted": true
        },
        "format_version": "1.20.0",
        "minecraft:item": {
            "description": {
                "identifier": "custom:{{item_id}}"
            },
            "components": {
                "minecraft:damage": "{{damage_val}}",
                "minecraft:foil": "{{is_enchanted}}"
            }
        }
    }"""
    output = compiler.compile_text(raw)
    data = json.loads(output)
    assert data["format_version"] == "1.20.0"
    assert data["minecraft:item"]["description"]["identifier"] == "custom:amethyst_sword"
    assert data["minecraft:item"]["components"]["minecraft:damage"] == 12
    assert data["minecraft:item"]["components"]["minecraft:foil"] is True
    assert "$scope" not in data


def test_jsonte_compiler_single_and_multilevel_inheritance(temp_workspace: str):
    """Verify $extend resolves through parent and grandparent templates."""
    grandparent_path = os.path.join(temp_workspace, "base_item.jsonte")
    parent_path = os.path.join(temp_workspace, "base_weapon.jsonte")
    child_path = os.path.join(temp_workspace, "ruby_blade.jsonte")

    with open(grandparent_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "format_version": "1.20.0",
            "minecraft:item": {
                "description": {"category": "Equipment"},
                "components": {"minecraft:max_stack_size": 1},
            },
        }))

    with open(parent_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "$extend": "base_item.jsonte",
            "minecraft:item": {
                "components": {
                    "minecraft:hand_equipped": True,
                    "minecraft:weapon": {},
                },
            },
        }))

    child_content = f"""{{
        "$extend": "base_weapon.jsonte",
        "minecraft:item": {{
            "description": {{
                "identifier": "custom:ruby_blade"
            }},
            "components": {{
                "minecraft:damage": 9
            }}
        }}
    }}"""
    with open(child_path, "w", encoding="utf-8") as handle:
        handle.write(child_content)

    compiler = JsonteCompiler()
    compiled = compiler.compile_text(child_content, file_path=child_path, base_dir=temp_workspace)
    data = json.loads(compiled)

    assert data["format_version"] == "1.20.0"
    assert data["minecraft:item"]["description"]["category"] == "Equipment"
    assert data["minecraft:item"]["description"]["identifier"] == "custom:ruby_blade"
    assert data["minecraft:item"]["components"]["minecraft:max_stack_size"] == 1
    assert data["minecraft:item"]["components"]["minecraft:hand_equipped"] is True
    assert data["minecraft:item"]["components"]["minecraft:damage"] == 9
    assert "$extend" not in data


def test_jsonte_compiler_circular_inheritance_detection(temp_workspace: str):
    """Verify circular template loops are detected and rejected."""
    file_a = os.path.join(temp_workspace, "template_a.jsonte")
    file_b = os.path.join(temp_workspace, "template_b.jsonte")

    with open(file_a, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"$extend": "template_b.jsonte", "a": 1}))

    with open(file_b, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"$extend": "template_a.jsonte", "b": 2}))

    compiler = JsonteCompiler()
    with pytest.raises(JsonteCompilationError, match="Circular template inheritance"):
        compiler.compile_text(json.dumps({"$extend": "template_a.jsonte"}), file_path=file_a, base_dir=temp_workspace)


def test_jsonte_compiler_each_array_and_object_loops():
    """Verify loop constructs expand arrays and objects cleanly."""
    compiler = JsonteCompiler()
    raw = """{
        "format_version": "1.20.0",
        "entries": [
            {
                "{{#each ['copper', 'tin', 'bronze']}}": {
                    "name": "custom:{{$value}}_gear",
                    "slot": "{{$index}}"
                }
            }
        ]
    }"""
    output = compiler.compile_text(raw)
    data = json.loads(output)
    entries = data["entries"]
    assert len(entries) == 3
    assert entries[0]["name"] == "custom:copper_gear"
    assert entries[0]["slot"] == 0
    assert entries[1]["name"] == "custom:tin_gear"
    assert entries[1]["slot"] == 1
    assert entries[2]["name"] == "custom:bronze_gear"
    assert entries[2]["slot"] == 2


def test_jsonte_compiler_conditional_evaluation():
    """Verify {{#if}} blocks conditionally include or exclude schema chunks."""
    compiler = JsonteCompiler()
    raw = """{
        "$scope": {
            "has_durability": true,
            "is_shield": false
        },
        "components": {
            "{{#if has_durability}}": {
                "minecraft:durability": {"max_durability": 500}
            },
            "{{#if is_shield}}": {
                "minecraft:block_motion": true
            }
        }
    }"""
    output = compiler.compile_text(raw)
    data = json.loads(output)
    assert "minecraft:durability" in data["components"]
    assert data["components"]["minecraft:durability"]["max_durability"] == 500
    assert "minecraft:block_motion" not in data["components"]


def test_audio_compiler_path_normalization_and_categories(temp_workspace: str):
    """Verify sound definitions aggregate audio files and assign correct categories."""
    sounds_dir = os.path.join(temp_workspace, "sounds", "ambient", "cave")
    os.makedirs(sounds_dir, exist_ok=True)

    with open(os.path.join(sounds_dir, "echo1.ogg"), "w", encoding="utf-8") as handle:
        handle.write("audio_data_1")
    with open(os.path.join(sounds_dir, "echo2.ogg"), "w", encoding="utf-8") as handle:
        handle.write("audio_data_2")

    defs = compile_sound_definitions(os.path.join(temp_workspace, "sounds"))
    assert defs["format_version"] == "1.20.0"
    event_key = "ambient.cave.echo"
    assert event_key in defs["sound_definitions"]
    event = defs["sound_definitions"][event_key]
    assert event["category"] == "ambient"
    assert len(event["sounds"]) == 2
    assert "sounds/ambient/cave/echo1" in event["sounds"]
    assert "sounds/ambient/cave/echo2" in event["sounds"]


def test_build_pipeline_executes_intermediate_filters_and_preserves_source(temp_workspace: str):
    """Verify build pipeline transforms templates without mutating source files."""
    src_dir = os.path.join(temp_workspace, "source", "resources", "data")
    dest_dir = os.path.join(temp_workspace, "game_destination")
    cache_path = os.path.join(temp_workspace, ".cache.json")

    os.makedirs(src_dir, exist_ok=True)
    template_file = os.path.join(src_dir, "test_item.jsonte")
    with open(template_file, "w", encoding="utf-8") as handle:
        handle.write("""{
            "$scope": {"tier": "diamond"},
            "format_version": "1.20.0",
            "minecraft:item": {
                "description": {"identifier": "custom:{{tier}}_halberd"}
            }
        }""")

    static_file = os.path.join(src_dir, "pack_manifest.json")
    with open(static_file, "w", encoding="utf-8") as handle:
        handle.write('{"name": "test_pack", "version": [1, 0, 0]}')

    hashes_before = snapshot_directory_hashes(src_dir)

    pipeline = BedrockBuildPipeline(cache_file=cache_path)
    stats, results = pipeline.build_and_deploy(src_dir, dest_dir)

    assert stats.total_files == 2
    assert stats.compiled_templates == 1
    assert stats.passthrough_files == 1
    assert stats.failed_files == 0

    hashes_after = snapshot_directory_hashes(src_dir)
    assert hashes_before == hashes_after, "Source directory files must remain strictly unmodified"

    dest_compiled = os.path.join(dest_dir, "test_item.json")
    assert os.path.isfile(dest_compiled), "Compiled .json must exist in destination"
    assert not os.path.exists(os.path.join(dest_dir, "test_item.jsonte")), "Raw .jsonte must not exist in destination"

    with open(dest_compiled, "r", encoding="utf-8") as handle:
        compiled_data = json.load(handle)
    assert compiled_data["minecraft:item"]["description"]["identifier"] == "custom:diamond_halberd"
    assert "$scope" not in compiled_data

    report = validate_deployment(src_dir, dest_dir, pre_build_hashes=hashes_before)
    assert report.is_valid is True
    assert report.source_unmodified is True
    assert report.json_valid is True
    assert report.directives_cleared is True
    assert len(report.errors) == 0

    second_stats, _ = pipeline.build_and_deploy(src_dir, dest_dir)
    assert second_stats.cached_files == 2, "Unchanged files must be skipped via incremental cache"


def test_validator_detects_uncompiled_syntax_and_corrupt_files(temp_workspace: str):
    """Verify validator flags illegal directives and unexpanded templates."""
    dest_dir = os.path.join(temp_workspace, "invalid_dest")
    src_dir = os.path.join(temp_workspace, "source")
    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(src_dir, exist_ok=True)

    with open(os.path.join(dest_dir, "bad_file.json"), "w", encoding="utf-8") as handle:
        handle.write('{"$extend": "something", "minecraft:item": "{{unexpanded}}"}')

    report = validate_deployment(src_dir, dest_dir)
    assert report.is_valid is False
    assert report.directives_cleared is False
    assert any("Illegal directive key" in err for err in report.errors)
    assert any("Unexpanded mustache expression" in err for err in report.errors)
