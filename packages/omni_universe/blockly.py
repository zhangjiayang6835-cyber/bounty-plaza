"""
Blockly visual block schemas, XML toolboxes, and code generators for OmniBlocks.
"""

from __future__ import annotations
import json
from typing import Any


class UniverseBlockly:
    """Blockly schema registry and multi-language transpiler for OmniBlocks visual programming."""

    BLOCK_DEFINITIONS: list[dict[str, Any]] = [
        {
            "type": "universe_create_cosmos",
            "message0": "create universe with seed %1 epoch %2 age %3 Gyr",
            "args0": [
                {"type": "field_input", "name": "SEED", "text": "omniblocks_universe_genesis"},
                {
                    "type": "field_dropdown",
                    "name": "EPOCH",
                    "options": [
                        ["Stelliferous", "stelliferous"],
                        ["Planck", "planck"],
                        ["Inflationary", "inflationary"],
                        ["Dark Ages", "dark_ages"],
                        ["Reionization", "reionization"],
                        ["Degenerate", "degenerate"],
                        ["Black Hole Era", "black_hole_era"],
                        ["Heat Death", "heat_death"],
                    ],
                },
                {"type": "field_number", "name": "AGE_GYR", "value": 13.8, "min": 0, "max": 100000},
            ],
            "output": "Universe",
            "colour": 260,
            "tooltip": "Initialize a deterministic cosmic universe instance.",
        },
        {
            "type": "universe_spawn_galaxy",
            "message0": "in universe %1 spawn galaxy %2 morphology %3 stars %4",
            "args0": [
                {"type": "input_value", "name": "UNIVERSE", "check": "Universe"},
                {"type": "field_input", "name": "NAME", "text": "MilkyWay"},
                {
                    "type": "field_dropdown",
                    "name": "MORPHOLOGY",
                    "options": [
                        ["Spiral", "spiral"],
                        ["Barred Spiral", "barred_spiral"],
                        ["Elliptical", "elliptical"],
                        ["Irregular", "irregular"],
                    ],
                },
                {"type": "field_number", "name": "STARS", "value": 5, "min": 1, "max": 1000},
            ],
            "output": "Galaxy",
            "colour": 210,
            "tooltip": "Procedurally spawn a galaxy with supermassive black hole core and stars.",
        },
        {
            "type": "universe_step_time",
            "message0": "advance universe %1 by %2 years in %3 substeps",
            "args0": [
                {"type": "input_value", "name": "UNIVERSE", "check": "Universe"},
                {"type": "field_number", "name": "YEARS", "value": 1000, "min": 1},
                {"type": "field_number", "name": "SUBSTEPS", "value": 10, "min": 1, "max": 1000},
            ],
            "previousStatement": None,
            "nextStatement": None,
            "colour": 180,
            "tooltip": "Step gravitational N-body physics forward in time.",
        },
        {
            "type": "universe_trigger_supernova",
            "message0": "in universe %1 trigger supernova for star %2",
            "args0": [
                {"type": "input_value", "name": "UNIVERSE", "check": "Universe"},
                {"type": "field_input", "name": "STAR_ID", "text": "star_1"},
            ],
            "previousStatement": None,
            "nextStatement": None,
            "colour": 0,
            "tooltip": "Trigger stellar core collapse, nucleosynthesis ejecta, and compact remnant.",
        },
        {
            "type": "universe_settle_bounty",
            "message0": "settle bounty #1575 recipient EVM %1 Stellar %2",
            "args0": [
                {"type": "field_input", "name": "EVM", "text": "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"},
                {
                    "type": "field_input",
                    "name": "STELLAR",
                    "text": "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC",
                },
            ],
            "output": "SettlementReceipt",
            "colour": 120,
            "tooltip": "Calculate exact arbitrary-precision settlement for Issue #1575.",
        },
    ]

    @classmethod
    def get_block_definitions_json(cls) -> str:
        """Export block schemas as formatted JSON string for Blockly registration."""
        return json.dumps(cls.BLOCK_DEFINITIONS, indent=2)

    @classmethod
    def get_toolbox_xml(cls) -> str:
        """Generate XML toolbox fragment for OmniBlocks editor palette."""
        xml_parts = [
            '<category name="OmniUniverse" colour="#7B1FA2">',
            '  <block type="universe_create_cosmos"></block>',
            '  <block type="universe_spawn_galaxy"></block>',
            '  <block type="universe_step_time"></block>',
            '  <block type="universe_trigger_supernova"></block>',
            '  <block type="universe_settle_bounty"></block>',
            "</category>",
        ]
        return "\n".join(xml_parts)

    @staticmethod
    def transpile_create_cosmos(seed: str, epoch: str, age_gyr: float, target_lang: str) -> str:
        """Emit code snippet to instantiate universe."""
        if target_lang.lower() == "javascript":
            return (
                f"const cosmos = new OmniUniverse({json.dumps(seed)});\n"
                f"cosmos.setEpoch({json.dumps(epoch)});\n"
                f"cosmos.setAgeGyr({age_gyr});"
            )
        return (
            f"cosmos = OmniUniverse(seed={json.dumps(seed)})\n"
            f"cosmos.set_epoch({json.dumps(epoch)})\n"
            f"cosmos.set_age_gyr({age_gyr})"
        )

    @staticmethod
    def transpile_spawn_galaxy(
        name: str,
        morphology: str,
        stars: int,
        target_lang: str,
    ) -> str:
        """Emit code snippet to spawn galaxy."""
        if target_lang.lower() == "javascript":
            return f"cosmos.spawnGalaxy({json.dumps(name)}, {json.dumps(morphology)}, {stars});"
        return f"cosmos.spawn_galaxy({json.dumps(name)}, {json.dumps(morphology)}, {stars})"

    @staticmethod
    def transpile_settlement(evm: str, stellar: str, target_lang: str) -> str:
        """Emit code snippet to execute settlement."""
        if target_lang.lower() == "javascript":
            return (
                f"const receipt = QuadrillionSettlementEngine.calculateSettlement("
                f"{json.dumps(evm)}, {json.dumps(stellar)});"
            )
        return (
            f"receipt = QuadrillionSettlementEngine.calculate_settlement("
            f"evm_address={json.dumps(evm)}, stellar_address={json.dumps(stellar)})"
        )
