"""Minecraft Bedrock template compiler and incremental build pipeline."""

from packages.bedrock_template_compiler.audio import (
    VALID_SOUND_CATEGORIES,
    compile_sound_definitions,
    derive_sound_category,
    normalize_sound_reference,
)
from packages.bedrock_template_compiler.jsonte import (
    JsonteCompilationError,
    JsonteCompiler,
    deep_merge,
    strip_json_comments,
)
from packages.bedrock_template_compiler.models import (
    BuildStats,
    CompilationResult,
    SoundDefinitionEntry,
    ValidationReport,
)
from packages.bedrock_template_compiler.pipeline import (
    BedrockBuildPipeline,
    calculate_file_hash,
    detect_template_dependencies,
    snapshot_directory_hashes,
)
from packages.bedrock_template_compiler.validator import validate_deployment

__all__ = [
    "BedrockBuildPipeline",
    "BuildStats",
    "CompilationResult",
    "JsonteCompilationError",
    "JsonteCompiler",
    "SoundDefinitionEntry",
    "VALID_SOUND_CATEGORIES",
    "ValidationReport",
    "calculate_file_hash",
    "compile_sound_definitions",
    "deep_merge",
    "derive_sound_category",
    "detect_template_dependencies",
    "normalize_sound_reference",
    "snapshot_directory_hashes",
    "strip_json_comments",
    "validate_deployment",
]
