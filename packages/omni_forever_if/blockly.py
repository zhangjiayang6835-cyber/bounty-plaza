"""Blockly visual programming definitions and code generators for Forever If."""

from typing import Any, Dict, List
from packages.omni_forever_if.models import BlockNode


class OmniBlocksForeverIfIntegration:
    """Generates visual block schemas, XML toolboxes, and multi-language code."""

    @staticmethod
    def get_block_definitions() -> List[Dict[str, Any]]:
        """Return JSON block specifications for the Blockly workspace."""
        definitions = []

        definitions.append({
            "type": "control_forever_if",
            "message0": "forever if %1 then %2",
            "args0": [
                {"type": "input_value", "name": "CONDITION", "check": "Boolean"},
                {"type": "input_statement", "name": "DO"},
            ],
            "previousStatement": None,
            "nextStatement": None,
            "colour": 120,
            "tooltip": "Continuously checks condition and executes body statements while condition is true.",
            "helpUrl": "https://github.com/OmniBlocks/monorepo/issues/794",
        })

        definitions.append({
            "type": "control_forever_if_edge",
            "message0": "forever when %1 becomes true then %2",
            "args0": [
                {"type": "input_value", "name": "CONDITION", "check": "Boolean"},
                {"type": "input_statement", "name": "DO"},
            ],
            "previousStatement": None,
            "nextStatement": None,
            "colour": 120,
            "tooltip": "Executes body statements on rising edge when condition transitions from false to true.",
            "helpUrl": "https://github.com/OmniBlocks/monorepo/issues/794",
        })

        definitions.append({
            "type": "control_stop_forever_if",
            "message0": "stop forever if fiber %1",
            "args0": [
                {"type": "input_value", "name": "FIBER"},
            ],
            "previousStatement": None,
            "nextStatement": None,
            "colour": 120,
            "tooltip": "Permanently halt a running forever if fiber.",
            "helpUrl": "https://github.com/OmniBlocks/monorepo/issues/794",
        })

        definitions.append({
            "type": "logic_condition_expr",
            "message0": "%1 %2 %3",
            "args0": [
                {"type": "field_input", "name": "LEFT", "text": "target_active"},
                {"type": "field_dropdown", "name": "OP", "options": [
                    ["==", "EQ"],
                    ["!=", "NEQ"],
                    [">", "GT"],
                    [">=", "GTE"],
                    ["<", "LT"],
                    ["<=", "LTE"],
                ]},
                {"type": "field_input", "name": "RIGHT", "text": "True"},
            ],
            "output": "Boolean",
            "colour": 210,
            "tooltip": "Relational expression yielding boolean condition result.",
            "helpUrl": "https://github.com/OmniBlocks/monorepo/issues/794",
        })

        return definitions

    @staticmethod
    def generate_python_code(block_type: str, params: Dict[str, Any]) -> str:
        """Generate Python code representing visual block execution."""
        if block_type == "control_forever_if":
            cond = params.get("CONDITION", "True")
            body = params.get("DO", "pass")
            lines = [
                "while True:",
                f"    if {cond}:",
                f"        {body}",
                "    runtime.yield_tick()",
            ]
            return "\n".join(lines)

        if block_type == "control_forever_if_edge":
            cond = params.get("CONDITION", "True")
            body = params.get("DO", "pass")
            var_name = params.get("PREV_VAR", "_prev_cond")
            lines = [
                f"{var_name} = False",
                "while True:",
                f"    _curr = bool({cond})",
                f"    if _curr and not {var_name}:",
                f"        {body}",
                f"    {var_name} = _curr",
                "    runtime.yield_tick()",
            ]
            return "\n".join(lines)

        if block_type == "control_stop_forever_if":
            target = params.get("FIBER", "fiber")
            return f"{target}.stop()"

        if block_type == "logic_condition_expr":
            left = params.get("LEFT", "x")
            op_code = params.get("OP", "EQ")
            right = params.get("RIGHT", "0")
            op_map = {
                "EQ": "==",
                "NEQ": "!=",
                "GT": ">",
                "GTE": ">=",
                "LT": "<",
                "LTE": "<=",
            }
            op_symbol = op_map.get(op_code, "==")
            return f"{left} {op_symbol} {right}"

        raise ValueError(f"Unknown block type: {block_type}")

    @staticmethod
    def generate_javascript_code(block_type: str, params: Dict[str, Any]) -> str:
        """Generate JavaScript code representing visual block execution."""
        if block_type == "control_forever_if":
            cond = params.get("CONDITION", "true")
            body = params.get("DO", "/* noop */;")
            lines = [
                "while (true) {",
                f"  if ({cond}) {{",
                f"    {body}",
                "  }",
                "  await runtime.yieldTick();",
                "}",
            ]
            return "\n".join(lines)

        if block_type == "control_forever_if_edge":
            cond = params.get("CONDITION", "true")
            body = params.get("DO", "/* noop */;")
            var_name = params.get("PREV_VAR", "_prevCond")
            lines = [
                f"let {var_name} = false;",
                "while (true) {",
                f"  const _curr = Boolean({cond});",
                f"  if (_curr && !{var_name}) {{",
                f"    {body}",
                "  }",
                f"  {var_name} = _curr;",
                "  await runtime.yieldTick();",
                "}",
            ]
            return "\n".join(lines)

        if block_type == "control_stop_forever_if":
            target = params.get("FIBER", "fiber")
            return f"{target}.stop();"

        if block_type == "logic_condition_expr":
            left = params.get("LEFT", "x")
            op_code = params.get("OP", "EQ")
            right = params.get("RIGHT", "0")
            op_map = {
                "EQ": "===",
                "NEQ": "!==",
                "GT": ">",
                "GTE": ">=",
                "LT": "<",
                "LTE": "<=",
            }
            op_symbol = op_map.get(op_code, "===")
            return f"{left} {op_symbol} {right}"

        raise ValueError(f"Unknown block type: {block_type}")

    @staticmethod
    def generate_toolbox_xml() -> str:
        """Construct Blockly XML toolbox category for Forever If control blocks."""
        lines = [
            '<category name="Forever If Control" colour="#5b80a5">',
            '  <block type="control_forever_if"></block>',
            '  <block type="control_forever_if_edge"></block>',
            '  <block type="control_stop_forever_if"></block>',
            '  <block type="logic_condition_expr"></block>',
            "</category>",
        ]
        return "\n".join(lines)

    @staticmethod
    def parse_block_node(spec: Dict[str, Any]) -> BlockNode:
        """Parse dictionary representation into structured BlockNode instance."""
        return BlockNode(
            block_id=spec.get("id", "block_root"),
            block_type=spec.get("type", "control_forever_if"),
            condition_expr=spec.get("condition"),
            statements=spec.get("statements", []),
            properties=spec.get("properties", {}),
        )
