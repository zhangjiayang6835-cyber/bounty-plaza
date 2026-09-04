"""Unit tests for Comment Standardization, Workplace-Friendly Lexicon & Bilingual Translation Engine.
Resolves Issue #671: [BOUNTY] [$250] Comment Standardization.
Upstream Reference: Iamgoofball/-tg-station#232.

Validates:
1. Standard English capitalization and punctuation normalization on raw comments.
2. Workplace-friendly lexicon replacement (sanitizing informal or unprofessional jargon).
3. Multiline comment structure generation for DreamMaker (/* ... */) and Python (# ...).
4. Simplified Chinese (ZH-CN) translation accuracy and technical semantic retention.
5. End-to-end source text processing across multi-language source snippets.
"""

import unittest
from scripts.comment_standardization_engine import (
    CommentStandardizationEngine,
    CommentTransformationResult,
)


class TestCommentStandardizationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = CommentStandardizationEngine()

    def test_capitalization_and_punctuation_normalization(self):
        """Validates first-letter capitalization and terminal punctuation enforcement."""
        raw_inputs = [
            ("// initialize the atmospheric pumps", "Initialize the atmospheric pumps."),
            ("# check buffer size before write", "Check buffer size before write."),
            ("/* verify user credentials */", "Verify user credentials."),
            ("// already formatted correctly.", "Already formatted correctly."),
            ("// trailing comma,", "Trailing comma."),
        ]
        for raw, expected in raw_inputs:
            normalized = self.engine.normalize_capitalization_and_punctuation(raw)
            self.assertEqual(normalized, expected)

    def test_workplace_language_sanitization(self):
        """Verifies inappropriate or informal jargon is replaced with professional equivalents."""
        informal_comment = "This hacky fix avoids the stupid bug where the controller craps out."
        safe_comment, rules = self.engine.sanitize_workplace_language(informal_comment)

        self.assertNotIn("hacky", safe_comment.lower())
        self.assertNotIn("stupid", safe_comment.lower())
        self.assertNotIn("craps out", safe_comment.lower())

        self.assertIn("provisional", safe_comment.lower())
        self.assertIn("unintuitive", safe_comment.lower())
        self.assertIn("experiences an unexpected fault", safe_comment.lower())
        self.assertGreater(len(rules), 0)

    def test_simplified_chinese_translation(self):
        """Verifies technical accuracy of generated Simplified Chinese annotations."""
        test_cases = [
            ("Initialize subsystem components and controllers.", "初始化子系统组件与生命周期控制器。"),
            ("Provisional workaround pending refactoring.", "生产环境临时规避方案，待后续架构重构时统一归档。"),
            ("Validate input parameters and verify preconditions.", "验证输入参数与前置条件的正确性。"),
            ("Safely clean up memory and teardown resources.", "安全释放系统资源，执行重置与拆卸清理。"),
        ]
        for en, expected_zh in test_cases:
            zh = self.engine.translate_to_simplified_chinese(en)
            self.assertEqual(zh, expected_zh)

    def test_multiline_formatting_dm_and_python(self):
        """Verifies comment formatting adheres to multiline conventions."""
        en = "Verify network payload integrity."
        zh = "验证网络有效载荷正确性。"

        dm_formatted = self.engine.format_as_multiline_dm(en, zh, indent="\t")
        self.assertTrue(dm_formatted.startswith("\t/*"))
        self.assertTrue(dm_formatted.endswith("\t */"))
        self.assertIn("[EN] " + en, dm_formatted)
        self.assertIn("[ZH-CN] " + zh, dm_formatted)

        py_formatted = self.engine.format_as_multiline_python(en, zh, indent="    ")
        self.assertIn("# ========================================================", py_formatted)
        self.assertIn("# [EN] " + en, py_formatted)
        self.assertIn("# [ZH-CN] " + zh, py_formatted)

    def test_end_to_end_source_text_processing(self):
        """Validates transforming full source file snippets with single-line comments."""
        dm_source = (
            "/datum/controller/subsystem/air\n"
            "\t// initialize the atmospheric subsystem\n"
            "\tvar/pressure = 101.3\n"
            "\t// hack to prevent pressure drops\n"
            "\tproc/fire()\n"
        )
        transformed, results = self.engine.process_source_text(dm_source, language="dm")

        self.assertEqual(len(results), 2)
        self.assertNotIn("// initialize", transformed)
        self.assertNotIn("// hack", transformed)
        self.assertIn("/*", transformed)
        self.assertIn("*/", transformed)
        self.assertIn("[ZH-CN]", transformed)


if __name__ == "__main__":
    unittest.main()
