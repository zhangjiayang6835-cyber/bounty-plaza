"""Bedrock block schema verification and invariant enforcement module."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from packages.bedrock_block_schema.block_validator import (
    BedrockBlockValidator,
    BlockFace,
    RenderMethod,
)
from packages.bedrock_block_schema.geometry_builder import (
    BlockGeometryBuilder,
)


@dataclass
class VerificationReport:
    """Consolidated report of all schema invariants and validation checks."""

    is_successful: bool
    passed_invariants: int
    failed_invariants: int
    invariants_verified: List[str] = field(default_factory=list)
    failure_reasons: List[str] = field(default_factory=list)


class BedrockBlockVerifier:
    """Verifies runtime invariants and acceptance criteria for issue 1306."""

    INVARIANTS: List[str] = [
        "SchemaConformityInvariant",
        "MaterialInstancesFaceInvariant",
        "RenderMethodInvariant",
        "IsotropicConfigurationInvariant",
        "SeamlessOutlineInvariant",
        "PackAssetBindingInvariant",
    ]

    @classmethod
    def create_sample_conforming_block(cls) -> Dict[str, Any]:
        """Generate a fully conforming custom ore block definition.

        Returns:
            Dictionary matching Bedrock 1.21.40+ block schema specifications.
        """
        return BedrockBlockValidator.migrate_definition(
            {}, default_render_method=RenderMethod.ALPHA_TEST.value
        )

    @classmethod
    def create_sample_malformed_block(cls) -> Dict[str, Any]:
        """Generate the original malformed block definition triggering issue 1306.

        Returns:
            Dictionary replicating the invalid block definition reported in issue 1306.
        """
        return {
            "format_version": "1.21.40",
            "minecraft:block": {
                "description": {
                    "identifier": "custom:void_crystal_ore",
                    "menu_category": {"category": "nature", "group": "itemGroup.name.ore"},
                },
                "components": {
                    "minecraft:material_instances": {
                        "*": {
                            "texture": "void_crystal_ore",
                            "render_method": "alpha_test_single_side",
                        }
                    },
                    "minecraft:destructible_by_mining": {"seconds_to_destroy": 3.0},
                },
            },
        }

    @classmethod
    def _check_material_invariants(
        cls,
        instances: Dict[str, Any],
        verified: List[str],
        failures: List[str],
    ) -> None:
        """Verify face definitions, render methods, and isotropic properties.

        Args:
            instances: The material_instances configuration dictionary.
            verified: Output accumulator for passed invariant names.
            failures: Output accumulator for failure descriptions.
        """
        if BlockFace.WILDCARD.value in instances:
            failures.append("Invalid face definition '*' present in directional ore block.")
        else:
            verified.append("MaterialInstancesFaceInvariant")

        has_unsupported_method = False
        has_invalid_isotropic = False
        for face_name, conf in instances.items():
            if not isinstance(conf, dict):
                has_unsupported_method = True
                continue
            method = conf.get("render_method")
            if method != RenderMethod.ALPHA_TEST.value:
                has_unsupported_method = True
                failures.append(
                    f"Face '{face_name}' uses render method '{method}' instead of 'alpha_test'."
                )
            if conf.get("isotropic") is not False:
                has_invalid_isotropic = True
                failures.append(
                    f"Face '{face_name}' isotropic flag must be False for directional ore."
                )

        if not has_unsupported_method:
            verified.append("RenderMethodInvariant")
        if not has_invalid_isotropic:
            verified.append("IsotropicConfigurationInvariant")

    @classmethod
    def _check_geometry_and_assets(
        cls,
        components: Dict[str, Any],
        geo_data: Optional[Dict[str, Any]],
        terrain_textures: Optional[Dict[str, Any]],
        verified: List[str],
        failures: List[str],
    ) -> None:
        """Verify geometry bindings, selection outline, and terrain textures.

        Args:
            components: Block components dictionary.
            geo_data: Optional parsed geometry definition.
            terrain_textures: Optional terrain texture mapping dictionary.
            verified: Output accumulator for passed invariant names.
            failures: Output accumulator for failure descriptions.
        """
        outline_ok, outline_errs = BedrockBlockValidator.validate_selection_and_collision(
            components
        )
        if geo_data:
            geo_res = BlockGeometryBuilder.validate_geometry(geo_data)
            if not geo_res.is_valid:
                outline_ok = False
                failures.extend(geo_res.errors)

        if outline_ok and not outline_errs:
            verified.append("SeamlessOutlineInvariant")
        else:
            failures.extend(outline_errs)

        if terrain_textures is not None:
            tex_data = terrain_textures.get("texture_data", {})
            required_keys = {
                "void_crystal_ore_top",
                "void_crystal_ore_bottom",
                "void_crystal_ore_side",
            }
            missing = required_keys - set(tex_data.keys())
            if missing:
                failures.append(f"Missing terrain texture mappings: {sorted(missing)}.")
            else:
                verified.append("PackAssetBindingInvariant")
        else:
            verified.append("PackAssetBindingInvariant")

    @classmethod
    def verify_all_invariants(
        cls,
        block_def: Dict[str, Any],
        geo_data: Optional[Dict[str, Any]] = None,
        terrain_textures: Optional[Dict[str, Any]] = None,
    ) -> VerificationReport:
        """Execute all six schema and runtime invariants.

        Args:
            block_def: Bedrock block definition dictionary.
            geo_data: Optional companion geometry definition.
            terrain_textures: Optional terrain_texture.json dictionary.

        Returns:
            VerificationReport containing pass/fail metrics and diagnostics.
        """
        verified: List[str] = []
        failures: List[str] = []

        validation = BedrockBlockValidator.validate_block_definition(block_def, is_directional=True)
        if validation.is_valid:
            verified.append("SchemaConformityInvariant")
        else:
            failures.extend(validation.errors)

        block_node = block_def.get("minecraft:block", {}) if isinstance(block_def, dict) else {}
        components = block_node.get("components", {}) if isinstance(block_node, dict) else {}
        instances = components.get("minecraft:material_instances", {})

        if isinstance(instances, dict) and instances:
            cls._check_material_invariants(instances, verified, failures)
        else:
            failures.append("Missing material instances component.")

        cls._check_geometry_and_assets(
            components, geo_data, terrain_textures, verified, failures
        )

        all_passed = len(failures) == 0 and len(verified) == len(cls.INVARIANTS)
        return VerificationReport(
            is_successful=all_passed,
            passed_invariants=len(verified),
            failed_invariants=len(cls.INVARIANTS) - len(verified),
            invariants_verified=verified,
            failure_reasons=failures,
        )
