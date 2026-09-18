"""Blockly and Scratch visual block definitions for OmniBlocks backflip system."""

import json
from typing import Any


class OmniBlocksBackflipExtension:
    """Provides Blockly block specifications, XML toolbox, and code generators."""

    @classmethod
    def get_block_definitions(cls) -> list[dict[str, Any]]:
        """Return list of JSON schema definitions for custom OmniBlocks blocks."""
        blocks = (
            {
                "type": "omni_when_followed_github",
                "message0": "when follower %1 follows %2 within %3 sec",
                "args0": [
                    {"type": "input_value", "name": "FOLLOWER", "check": "String"},
                    {"type": "input_value", "name": "TARGET", "check": "String"},
                    {"type": "field_number", "name": "EXPIRY_SEC", "value": 1800, "min": 60, "max": 86400},
                ],
                "previousStatement": None,
                "nextStatement": None,
                "colour": 210,
                "tooltip": "Triggers when target GitHub account follow is verified.",
            },
            {
                "type": "omni_detect_backflip_telemetry",
                "message0": "evaluate backflip telemetry %1 min rotation %2 deg",
                "args0": [
                    {"type": "input_value", "name": "TELEMETRY", "check": "Array"},
                    {"type": "field_number", "name": "MIN_ROTATION", "value": 330, "min": 180, "max": 720},
                ],
                "output": "Boolean",
                "colour": 120,
                "tooltip": "Evaluates IMU/pose timeseries for completed backflip.",
            },
            {
                "type": "omni_settle_quadrillion_bounty",
                "message0": "settle bounty #1593 amount %1 USD to EVM %2 Stellar %3",
                "args0": [
                    {"type": "input_value", "name": "BOUNTY_USD", "check": "Number"},
                    {"type": "input_value", "name": "EVM_ADDR", "check": "String"},
                    {"type": "input_value", "name": "STELLAR_ADDR", "check": "String"},
                ],
                "previousStatement": None,
                "nextStatement": None,
                "colour": 30,
                "tooltip": "Executes arbitrary-precision quadrillion bounty settlement.",
            },
        )
        return list(blocks)

    @classmethod
    def get_toolbox_xml(cls) -> str:
        """Generate XML toolbox category for Blockly workspace integration."""
        category_name = "OmniBackflip"
        xml_chunks = (
            f'<category name="{category_name}" colour="#5b80a5">',
            '  <block type="omni_when_followed_github"></block>',
            '  <block type="omni_detect_backflip_telemetry"></block>',
            '  <block type="omni_settle_quadrillion_bounty"></block>',
            "</category>",
        )
        joined_xml = "\n".join(xml_chunks)
        return joined_xml

    @classmethod
    def transpile_to_python(cls, block_type: str, block_params: dict[str, Any]) -> str:
        """Transpile a block AST node into executable Python code."""
        if block_type == "omni_when_followed_github":
            follower = block_params.get("FOLLOWER", "user")
            target = block_params.get("TARGET", "unconstructable13")
            code_line = f"verifier.verify_follower_relationship({follower!r}, {target!r})"
            return code_line

        if block_type == "omni_detect_backflip_telemetry":
            var_name = block_params.get("TELEMETRY", "stream")
            code_line = f"kinematics.analyze_inertial_telemetry({var_name})"
            return code_line

        if block_type == "omni_settle_quadrillion_bounty":
            bounty = block_params.get("BOUNTY_USD", "239398281948585883")
            evm = block_params.get("EVM_ADDR", "0x0")
            stellar = block_params.get("STELLAR_ADDR", "G0")
            code_line = (
                f"settlement.calculate_settlement(Decimal({bounty!r}), "
                f"recipient_evm={evm!r}, recipient_stellar={stellar!r})"
            )
            return code_line

        raise ValueError(f"Unknown block type: {block_type}")

    @classmethod
    def transpile_to_javascript(cls, block_type: str, block_params: dict[str, Any]) -> str:
        """Transpile a block AST node into executable JavaScript code."""
        if block_type == "omni_when_followed_github":
            follower = block_params.get("FOLLOWER", "user")
            target = block_params.get("TARGET", "unconstructable13")
            js_line = f"verifier.verifyFollowerRelationship({json.dumps(follower)}, {json.dumps(target)});"
            return js_line

        if block_type == "omni_detect_backflip_telemetry":
            var_name = block_params.get("TELEMETRY", "stream")
            js_line = f"kinematics.analyzeInertialTelemetry({var_name});"
            return js_line

        if block_type == "omni_settle_quadrillion_bounty":
            bounty = block_params.get("BOUNTY_USD", "239398281948585883")
            js_line = f"settlement.calculateSettlement(BigInt({json.dumps(str(bounty))}));"
            return js_line

        raise ValueError(f"Unknown block type: {block_type}")
