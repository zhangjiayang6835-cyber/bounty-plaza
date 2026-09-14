"""Automated migration pipeline for legacy Bedrock humanoid client entities."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union


class EntityMigrationPipeline:
    """Migrates legacy humanoid and zombie entity definitions to modern format."""

    TARGET_FORMAT_VERSION = "1.10.0"
    TARGET_GEOMETRY = "geometry.humanoid.custom"
    TARGET_RENDER_CONTROLLER = "controller.render.default"
    TARGET_MATERIAL = "entity_alphatest"

    def migrate_entity_definition(
        self, raw_entity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert a legacy client entity dictionary into modern format."""
        updated = json.loads(json.dumps(raw_entity))
        updated["format_version"] = self.TARGET_FORMAT_VERSION

        client_entity = updated.setdefault("minecraft:client_entity", {})
        description = client_entity.setdefault("description", {})

        materials = description.setdefault("materials", {})
        materials["default"] = self.TARGET_MATERIAL

        geometry = description.setdefault("geometry", {})
        geometry["default"] = self.TARGET_GEOMETRY

        description["render_controllers"] = [self.TARGET_RENDER_CONTROLLER]

        return updated

    def migrate_entity_file(
        self,
        source_path: Union[str, Path],
        target_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Read legacy entity file, transform definition, and save to target path."""
        src = Path(source_path)
        with open(src, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        migrated = self.migrate_entity_definition(data)
        dest = Path(target_path) if target_path else src
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "w", encoding="utf-8") as file_handle:
            json.dump(migrated, file_handle, indent=2)

        return migrated
