"""Model configuration validator and migration manager for non-legacy kernels.

This module provides standard configurations for models historically requiring
compatibility bypass flags (such as Falcon, BGE, SDXL, and DeepSeek) and validates
their migration to canonical precision settings.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from packages.tt_metal_precision_kernels.types import PrecisionMode


class ModelArchitecture(str, Enum):
    """Supported neural network architectures historically affected by legacy flags."""

    FALCON_7B = "falcon_7b"
    BGE_LARGE = "bge_large"
    SDXL_BASE = "sdxl_base"
    DEEPSEEK_V3 = "deepseek_v3"


@dataclass
class ModelConfiguration:
    """Canonical model configuration structure without legacy plumbing."""

    model_name: str
    hidden_size: int
    num_heads: int
    num_layers: int
    norm_eps: float
    precision_mode: PrecisionMode
    use_welford: bool

    def __post_init__(self) -> None:
        """Validate that model configuration conforms to modern precision standards."""
        if any("legacy" in attr.lower() for attr in self.__dict__):
            raise ValueError("Legacy attributes are prohibited in ModelConfiguration.")


def migrate_legacy_config(raw_config: dict[str, Any]) -> dict[str, Any]:
    """Migrate a legacy model dictionary to canonical precision settings.

    Parameters:
        raw_config: Dictionary potentially containing obsolete compatibility parameters.

    Returns:
        Sanitized configuration dictionary containing only canonical parameters.
    """
    migrated = dict(raw_config)
    keys_to_remove = [k for k in migrated if "legacy" in k.lower() or "compat" in k.lower()]
    if keys_to_remove:
        migrated["precision_mode"] = PrecisionMode.PRECISE
    for k in keys_to_remove:
        del migrated[k]

    return migrated


def get_canonical_model_config(arch: ModelArchitecture) -> ModelConfiguration:
    """Retrieve canonical configuration for specified model architecture.

    Parameters:
        arch: Target model architecture enum.

    Returns:
        ModelConfiguration object operating strictly with canonical precision.
    """
    if arch == ModelArchitecture.FALCON_7B:
        return ModelConfiguration(
            model_name="Falcon-7B",
            hidden_size=4544,
            num_heads=71,
            num_layers=32,
            norm_eps=1e-5,
            precision_mode=PrecisionMode.PRECISE,
            use_welford=False,
        )
    if arch == ModelArchitecture.BGE_LARGE:
        return ModelConfiguration(
            model_name="BGE-Large-EN",
            hidden_size=1024,
            num_heads=16,
            num_layers=24,
            norm_eps=1e-12,
            precision_mode=PrecisionMode.PRECISE,
            use_welford=True,
        )
    if arch == ModelArchitecture.SDXL_BASE:
        return ModelConfiguration(
            model_name="SDXL-Base-1.0",
            hidden_size=2048,
            num_heads=32,
            num_layers=30,
            norm_eps=1e-5,
            precision_mode=PrecisionMode.APPROXIMATE,
            use_welford=False,
        )
    return ModelConfiguration(
        model_name="DeepSeek-V3",
        hidden_size=7168,
        num_heads=128,
        num_layers=61,
        norm_eps=1e-6,
        precision_mode=PrecisionMode.PRECISE,
        use_welford=True,
    )
