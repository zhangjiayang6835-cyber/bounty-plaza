"""Migration utilities to move block audio mappings from BP descriptions to RP blocks.json."""

import json
from pathlib import Path
from typing import Any, Dict, Tuple


class MigrationPipeline:
    """Automates upgrading legacy Bedrock block definitions to format 1.26.30 compliance."""

    @staticmethod
    def migrate_block_data(
        bp_data: Dict[str, Any],
        rp_data: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        """Migrate sound property from description into resource pack dictionary."""
        modified = False
        block_body = bp_data.get("minecraft:block")
        if not isinstance(block_body, dict):
            return bp_data, rp_data, modified

        desc = block_body.get("description")
        if not isinstance(desc, dict):
            return bp_data, rp_data, modified

        identifier = desc.get("identifier")
        if not identifier or not isinstance(identifier, str):
            return bp_data, rp_data, modified

        if "sound" in desc:
            sound_profile = desc.pop("sound")
            modified = True
            if identifier not in rp_data or not isinstance(rp_data[identifier], dict):
                rp_data[identifier] = {}
            rp_data[identifier]["sound"] = sound_profile

        return bp_data, rp_data, modified

    @classmethod
    def migrate_files(
        cls,
        bp_path: str,
        rp_path: str,
    ) -> bool:
        """Read BP and RP files, perform migration if needed, and write back to disk."""
        bp_file = Path(bp_path)
        rp_file = Path(rp_path)

        if not bp_file.exists():
            return False

        with open(bp_file, "r", encoding="utf-8") as handle:
            bp_data = json.load(handle)

        rp_data: Dict[str, Any] = {"format_version": [1, 1, 0]}
        if rp_file.exists():
            with open(rp_file, "r", encoding="utf-8") as handle:
                loaded_rp = json.load(handle)
                if isinstance(loaded_rp, dict):
                    rp_data = loaded_rp

        updated_bp, updated_rp, modified = cls.migrate_block_data(bp_data, rp_data)
        if not modified:
            return False

        with open(bp_file, "w", encoding="utf-8") as handle:
            json.dump(updated_bp, handle, indent=2)
            handle.write("\n")

        rp_file.parent.mkdir(parents=True, exist_ok=True)
        with open(rp_file, "w", encoding="utf-8") as handle:
            json.dump(updated_rp, handle, indent=2)
            handle.write("\n")

        return True
