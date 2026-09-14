"""Generators for schema-compliant Bedrock block definitions and supporting assets."""

from typing import Any

from packages.bedrock_block_validator.models import (
    BedrockBlockDefinition,
    BlockComponents,
    BlockDescription,
    MaterialInstance,
    RenderMethod,
)


class BedrockBlockGenerator:
    """Provides methods for constructing valid Bedrock asset definitions."""

    @classmethod
    def create_compressed_basalt_model(cls) -> BedrockBlockDefinition:
        """Construct a schema-compliant BedrockBlockDefinition object."""
        instances = {
            "up": MaterialInstance(
                texture="compressed_basalt_top",
                render_method=RenderMethod.OPAQUE,
                face_dimming=True,
                ambient_occlusion=1.0,
                isotropic=True,
            ),
            "down": MaterialInstance(
                texture="compressed_basalt_bottom",
                render_method=RenderMethod.OPAQUE,
                face_dimming=True,
                ambient_occlusion=1.0,
                isotropic=True,
            ),
            "north": MaterialInstance(
                texture="compressed_basalt_side",
                render_method=RenderMethod.OPAQUE,
                face_dimming=True,
                ambient_occlusion=1.0,
            ),
            "south": MaterialInstance(
                texture="compressed_basalt_side",
                render_method=RenderMethod.OPAQUE,
                face_dimming=True,
                ambient_occlusion=1.0,
            ),
            "east": MaterialInstance(
                texture="compressed_basalt_side",
                render_method=RenderMethod.OPAQUE,
                face_dimming=True,
                ambient_occlusion=1.0,
            ),
            "west": MaterialInstance(
                texture="compressed_basalt_side",
                render_method=RenderMethod.OPAQUE,
                face_dimming=True,
                ambient_occlusion=1.0,
            ),
            "*": MaterialInstance(
                texture="compressed_basalt_side",
                render_method=RenderMethod.OPAQUE,
                face_dimming=True,
                ambient_occlusion=1.0,
            ),
        }

        components = BlockComponents(
            material_instances=instances,
            geometry={"identifier": "geometry.compressed_basalt"},
            collision_box={"origin": [-8, 0, -8], "size": [16, 16, 16]},
            selection_box={"origin": [-8, 0, -8], "size": [16, 16, 16]},
            destructible_by_mining={"seconds_to_destroy": 2.5},
            destructible_by_explosion={"explosion_resistance": 6.0},
            friction=0.6,
            map_color="#474F52",
        )

        description = BlockDescription(
            identifier="custom:compressed_basalt",
            menu_category={
                "category": "construction",
                "group": "itemGroup.name.stone",
            },
        )

        return BedrockBlockDefinition(
            format_version="1.21.50",
            description=description,
            components=components,
        )

    @classmethod
    def create_compressed_basalt_dict(cls) -> dict[str, Any]:
        """Produce dictionary adhering to Bedrock 1.21+/1.26+ block schema."""
        return cls.create_compressed_basalt_model().to_dict()

    @classmethod
    def create_culling_definition(cls) -> dict[str, Any]:
        """Produce culling rules for the 16x16x16 cube geometry."""
        directions = ["up", "down", "north", "south", "east", "west"]
        return {
            "format_version": "1.21.50",
            "minecraft:block_culling_rules": {
                "description": {
                    "identifier": "custom:compressed_basalt_culling"
                },
                "rules": [
                    {
                        "direction": d,
                        "geometry_part": {
                            "cube": 0,
                            "face": d,
                        },
                    }
                    for d in directions
                ],
            },
        }

    @classmethod
    def create_terrain_texture_atlas(cls) -> dict[str, Any]:
        """Produce terrain texture atlas mapping for compressed basalt textures."""
        return {
            "resource_pack_name": "bounty-plaza-block-pack",
            "texture_name": "atlas.terrain",
            "texture_data": {
                "compressed_basalt_top": {
                    "textures": "textures/blocks/compressed_basalt_top"
                },
                "compressed_basalt_bottom": {
                    "textures": "textures/blocks/compressed_basalt_bottom"
                },
                "compressed_basalt_side": {
                    "textures": "textures/blocks/compressed_basalt_side"
                },
            },
        }
