"""Comprehensive test suite for Issue #1518: slugify() repeated and trailing hyphens."""

import subprocess
import pytest

from packages.slugify_toolkit import (
    SlugOptions,
    SlugVerifier,
    Slugifier,
    slugify,
)


def test_issue_acceptance_collapses_runs_of_punctuation_and_spaces() -> None:
    """Verifies that runs of punctuation and spaces collapse into a single hyphen."""
    raw_input = "Hello,   World!!"
    expected = "hello-world"
    assert slugify(raw_input) == expected


def test_issue_acceptance_does_not_produce_leading_or_trailing_hyphens() -> None:
    """Verifies that leading and trailing hyphens are completely stripped."""
    raw_input = "  --Hello World--  "
    expected = "hello-world"
    assert slugify(raw_input) == expected


def test_issue_acceptance_lowercases_and_joins_words() -> None:
    """Verifies that letters are converted to lower case and joined with hyphens."""
    raw_input = "Hello World"
    expected = "hello-world"
    assert slugify(raw_input) == expected


def test_issue_acceptance_strips_accents() -> None:
    """Verifies that diacritical accents are stripped from letters."""
    raw_input = "Café Déjà Vu"
    expected = "cafe-deja-vu"
    assert slugify(raw_input) == expected


def test_issue_acceptance_rejects_non_strings() -> None:
    """Verifies that TypeError is raised for non-string inputs."""
    invalid_inputs = [42, None, [], {}, 3.14, True]
    for val in invalid_inputs:
        with pytest.raises(TypeError, match="slugify expects a string"):
            slugify(val)


def test_nodejs_test_suite_execution() -> None:
    """Verifies that native Node.js test runner passes all acceptance tests."""
    result = subprocess.run(
        ["node", "--test", "test/slugify.test.js"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "pass 5" in result.stdout
    assert "fail 0" in result.stdout


def test_nodejs_npm_test_command() -> None:
    """Verifies that npm test succeeds with 0 exit code."""
    result = subprocess.run(
        ["npm", "test"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "fail 0" in result.stdout


def test_cross_runtime_parity_between_node_and_python() -> None:
    """Verifies 100% output parity between JavaScript and Python slugify implementations."""
    verifier = SlugVerifier()
    test_cases = [
        "Hello World",
        "Café Déjà Vu",
        "Hello,   World!!",
        "  --Hello World--  ",
        "Über den Wolken",
        "Crème Brûlée & Häagen-Dazs",
        "Multiple----Dashes----Everywhere",
        "---Prefix and Postfix---",
        "123 numbers and 456 symbols $$$!",
        "Mixed CASE with punctuation: (bracketed) [content]",
    ]
    for case in test_cases:
        py_output = slugify(case)
        js_output = verifier.execute_node_slugify(case)
        assert py_output == js_output


def test_cross_runtime_type_error_parity() -> None:
    """Verifies that non-strings raise TypeError across both runtimes."""
    verifier = SlugVerifier()
    invalid_values = [42, None, [1, 2, 3], {"a": 1}]
    for val in invalid_values:
        with pytest.raises(TypeError):
            slugify(val)
        with pytest.raises(TypeError):
            verifier.execute_node_slugify(val)


def test_edge_case_empty_and_separator_only_strings() -> None:
    """Verifies behavior on empty strings and strings containing only separators."""
    assert slugify("") == ""
    assert slugify("   ") == ""
    assert slugify("---") == ""
    assert slugify("---   !!!   ---") == ""


def test_edge_case_numeric_and_special_characters() -> None:
    """Verifies preservation of alphanumeric digits and proper symbol replacement."""
    assert slugify("Version 2.0.1 Beta") == "version-2-0-1-beta"
    assert slugify("item_100_v2") == "item-100-v2"
    assert slugify("$100 bounty reward!") == "100-bounty-reward"


def test_is_valid_slug_validator() -> None:
    """Verifies slug validation method."""
    assert Slugifier.is_valid_slug("hello-world") is True
    assert Slugifier.is_valid_slug("item-100-v2") is True
    assert Slugifier.is_valid_slug("") is True
    assert Slugifier.is_valid_slug("-leading") is False
    assert Slugifier.is_valid_slug("trailing-") is False
    assert Slugifier.is_valid_slug("double--dash") is False
    assert Slugifier.is_valid_slug("Upper-Case") is False
    assert Slugifier.is_valid_slug("spaces here") is False
    assert Slugifier.is_valid_slug(12345) is False


def test_slug_options_custom_separator() -> None:
    """Verifies custom options such as underscore separator."""
    opts = SlugOptions(separator="_")
    result = slugify("Hello, World!!", options=opts)
    assert result == "hello_world"


def test_slug_options_boundary_preservation() -> None:
    """Verifies option to preserve boundaries if explicitly configured."""
    opts = SlugOptions(strip_boundaries=False)
    result = slugify("  Hello  ", options=opts)
    assert result == "-hello-"
