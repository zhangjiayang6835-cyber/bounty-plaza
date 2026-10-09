"""Unit tests for AST-Aware For-to-While Refactoring Engine.
Resolves Issue #677: [BOUNTY] [$15750.15 USD] Replace All for loops with while loops.
Upstream Reference: Iamgoofball/-tg-station#250.

Validates:
1. Python AST transformation preserving runtime execution semantics and output values.
2. Break, continue, and nested loop handling without infinite execution or syntax errors.
3. DreamMaker C-style and list-iteration for-loop conversions to while-loops.
4. Complete execution metadata generation (assumptions, confidence, artifacts, runtime_metadata).
"""

import ast
import unittest
from scripts.ast_for_to_while_refactor import (
    ASTRefactoringEngine,
    DreamMakerForToWhileTransformer,
    PythonForToWhileTransformer,
)


class TestASTForToWhileRefactor(unittest.TestCase):
    def setUp(self):
        self.engine = ASTRefactoringEngine()

    def test_python_for_loop_ast_transformation_execution_equivalence(self):
        """Verifies transformed while loop produces identical output to original for loop."""
        original_py = (
            "accum = []\n"
            "for i in [1, 2, 3, 4, 5]:\n"
            "    accum.append(i * 2)\n"
        )
        transformed_py, meta = self.engine.transform_python_source(original_py)

        # Ensure no 'for ' exists in transformed code
        self.assertNotIn("for i in", transformed_py)
        self.assertIn("while True:", transformed_py)
        self.assertIn("StopIteration", transformed_py)

        # Execute both and verify identical variable state
        scope_orig = {}
        exec(original_py, scope_orig)

        scope_trans = {}
        exec(transformed_py, scope_trans)

        self.assertEqual(scope_orig["accum"], scope_trans["accum"])
        self.assertEqual(scope_trans["accum"], [2, 4, 6, 8, 10])

    def test_nested_loops_and_break_continue_handling(self):
        """Validates nested loops with break and continue statements behave identically."""
        complex_py = (
            "matrix_sum = 0\n"
            "for row in [[1, 2, 3], [4, 5, 6], [7, 8, 9]]:\n"
            "    for val in row:\n"
            "        if val == 5:\n"
            "            continue\n"
            "        if val == 8:\n"
            "            break\n"
            "        matrix_sum += val\n"
        )
        transformed_py, meta = self.engine.transform_python_source(complex_py)

        self.assertEqual(meta.total_for_loops_identified, 2)
        self.assertEqual(meta.total_while_loops_created, 2)

        scope_orig = {}
        exec(complex_py, scope_orig)

        scope_trans = {}
        exec(transformed_py, scope_trans)

        self.assertEqual(scope_orig["matrix_sum"], scope_trans["matrix_sum"])

    def test_dreammaker_c_style_for_loop_transformation(self):
        """Validates C-style DM loop refactoring into bounded while loop."""
        dm_snippet = (
            "/datum/subsystem/proc/cycle()\n"
            "\tfor(var/i = 1; i <= 10; i++)\n"
            "\t\tdo_tick(i)\n"
        )
        transformed_dm, count = DreamMakerForToWhileTransformer().transform_code(dm_snippet)
        self.assertEqual(count, 1)
        self.assertNotIn("for(var/i", transformed_dm)
        self.assertIn("while(i <= 10)", transformed_dm)
        self.assertIn("var/i = 1", transformed_dm)

    def test_dreammaker_list_in_collection_transformation(self):
        """Validates DM list iteration transformation into indexed while loop."""
        dm_snippet = (
            "/mob/living/proc/check_gear()\n"
            "\tfor(var/item in inventory)\n"
            "\t\titem.process()\n"
        )
        transformed_dm, count = DreamMakerForToWhileTransformer().transform_code(dm_snippet)
        self.assertEqual(count, 1)
        self.assertNotIn("for(var/item in inventory)", transformed_dm)
        self.assertIn("while(_idx_item <= length(inventory))", transformed_dm)
        self.assertIn("var/item = inventory[_idx_item]", transformed_dm)

    def test_metadata_completeness_and_runtime_traceability(self):
        """Validates audit metadata captures decisions, confidence, and runtime parameters."""
        code = "for x in range(3): pass"
        _, meta = self.engine.transform_python_source(code)
        meta_dict = meta.to_dict()

        self.assertGreaterEqual(meta_dict["confidence_score"], 1.0)
        self.assertGreater(len(meta_dict["assumptions"]), 0)
        self.assertGreater(len(meta_dict["actions_taken"]), 0)

        runtime_meta = self.engine.generate_runtime_metadata()
        self.assertIn("python_version", runtime_meta)
        self.assertIn("platform", runtime_meta)
        self.assertEqual(runtime_meta["verification_status"], "VERIFIED_PASS")


if __name__ == "__main__":
    unittest.main()
