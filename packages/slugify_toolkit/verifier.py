"""Verification utilities testing slug parity between environments."""

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from packages.slugify_toolkit.slugifier import Slugifier, slugify


class SlugVerifier:
    """Verifies slugification integrity across test cases and external runtimes."""

    def __init__(self, js_source_path: str | Path | None = None) -> None:
        """Initializes the verifier with optional path to JavaScript implementation."""
        self._js_source_path = Path(js_source_path) if js_source_path else None
        self._slugifier = Slugifier()

    def verify_single(self, input_val: str, expected_output: str) -> bool:
        """Verifies that an input string produces the expected slug.

        Args:
            input_val: The raw input string.
            expected_output: The expected slug outcome.

        Returns:
            True if output matches expectation.
        """
        actual = self._slugifier.slugify(input_val)
        return actual == expected_output

    def verify_matrix(self, test_cases: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
        """Verifies a sequence of test cases and returns any mismatches.

        Args:
            test_cases: List of (input, expected) pairs.

        Returns:
            List of (input, expected, actual) triples for failed cases.
        """
        failures = []
        for inp, expected in test_cases:
            actual = self._slugifier.slugify(inp)
            if actual != expected:
                failures.append((inp, expected, actual))
        return failures

    def execute_node_slugify(self, input_val: Any) -> str:
        """Invokes the JavaScript slugify function via Node subprocess.

        Args:
            input_val: The input value to serialize and pass to Node.js.

        Returns:
            The string output produced by the Node.js implementation.

        Raises:
            RuntimeError: If Node.js execution fails.
        """
        js_code = (
            "const { slugify } = require('./src/slugify');\n"
            "const input = " + json.dumps(input_val) + ";\n"
            "try {\n"
            "  process.stdout.write(slugify(input));\n"
            "} catch (err) {\n"
            "  if (err instanceof TypeError) {\n"
            "    process.stderr.write('TYPE_ERROR');\n"
            "    process.exit(2);\n"
            "  }\n"
            "  process.stderr.write(String(err));\n"
            "  process.exit(1);\n"
            "}\n"
        )
        proc = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 2 and proc.stderr == "TYPE_ERROR":
            raise TypeError("slugify expects a string")
        if proc.returncode != 0:
            raise RuntimeError(f"Node execution error: {proc.stderr}")
        return proc.stdout

    def verify_cross_runtime_parity(self, test_strings: list[str]) -> bool:
        """Confirms that Python and JavaScript slugify outputs are identical.

        Args:
            test_strings: Input strings to evaluate in both runtimes.

        Returns:
            True if all outputs match across both languages.
        """
        for s in test_strings:
            py_res = slugify(s)
            js_res = self.execute_node_slugify(s)
            if py_res != js_res:
                return False
        return True


def run_acceptance_suite() -> int:
    """Executes the standard test matrix and returns zero on full pass.

    Returns:
        Exit code 0 on complete success, 1 on failure.
    """
    verifier = SlugVerifier()
    matrix = [
        ("Hello World", "hello-world"),
        ("Café Déjà Vu", "cafe-deja-vu"),
        ("Hello,   World!!", "hello-world"),
        ("  --Hello World--  ", "hello-world"),
        ("Special @#$% Characters! Here", "special-characters-here"),
        ("Multi----Dash---Sequence", "multi-dash-sequence"),
        ("   ---leading and trailing---   ", "leading-and-trailing"),
    ]
    failures = verifier.verify_matrix(matrix)
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_acceptance_suite())
