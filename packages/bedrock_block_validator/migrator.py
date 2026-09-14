"""Migration utility upgrading legacy Bedrock block definitions to modern schemas."""

import copy
from typing import Any


class BedrockBlockMigrator:
    """Migrates invalid or legacy block definitions to compliant schemas."""

    TARGET_FORMAT_VERSION = "1.21.50"
    DIRECTIONAL_FACES = ("up", "down", "north", "south", "east", "west")

    @classmethod
    def migrate_definition(cls, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Upgrade block definition JSON structure to compliant schema.

        Args:
            raw_data: Unmigrated block definition dictionary.

        Returns:
            Modernized block definition dictionary passing schema validation.
        """
        output = copy.deepcopy(raw_data)
        output["format_version"] = cls.TARGET_FORMAT_VERSION

        block = output.setdefault("minecraft:block", {})
        description = block.setdefault("description", {})

        has_description_isotropic = description.pop("isotropic", None) is True

        components = block.setdefault("components", {})
        mat_instances = components.setdefault("minecraft:material_instances", {})

        wildcard = mat_instances.get("*", {})
        if wildcard.get("render_method") == "alpha_test":
            wildcard["render_method"] = "opaque"

        base_texture = wildcard.get("texture", "compressed_basalt_side")

        for face in cls.DIRECTIONAL_FACES:
            if face not in mat_instances:
                face_texture = base_texture
                if face == "up":
                    face_texture = "compressed_basalt_top"
                elif face == "down":
                    face_texture = "compressed_basalt_bottom"

                mat_instances[face] = {
                    "texture": face_texture,
                    "render_method": "opaque",
                    "ambient_occlusion": 1.0,
                    "face_dimming": True,
                }
            else:
                if mat_instances[face].get("render_method") == "alpha_test":
                    mat_instances[face]["render_method"] = "opaque"
                mat_instances[face].setdefault("ambient_occlusion", 1.0)
                mat_instances[face].setdefault("face_dimming", True)

        if has_description_isotropic or "up" in mat_instances:
            mat_instances["up"]["isotropic"] = True

        if has_description_isotropic or "down" in mat_instances:
            mat_instances["down"]["isotropic"] = True

        return output
