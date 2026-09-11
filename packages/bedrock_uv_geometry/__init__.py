"""Bedrock UV Geometry Package for custom NPC models and Bedrock 1.21.50+."""

from packages.bedrock_uv_geometry.generator import BedrockHumanoidGenerator
from packages.bedrock_uv_geometry.migrator import BedrockUVMigrator
from packages.bedrock_uv_geometry.models import (
    ArmModelType,
    BedrockGeometry,
    Bone,
    Cube,
    GeometryDescription,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)
from packages.bedrock_uv_geometry.validator import BedrockUVValidator

__all__ = [
    "ArmModelType",
    "BedrockGeometry",
    "BedrockHumanoidGenerator",
    "BedrockUVMigrator",
    "BedrockUVValidator",
    "Bone",
    "Cube",
    "GeometryDescription",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
]
