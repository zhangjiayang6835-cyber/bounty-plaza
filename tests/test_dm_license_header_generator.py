"""Unit tests for DreamMaker (BYOND DM) Codebase License Header & Git Attribution Generator.
Resolves Issue #663: [BOUNTY] [$500] [$1000] Add license information to codebase.
"""

import pytest
from scripts.dm_license_header_generator import (
    DMLicenseHeaderGenerator,
    AuthorContribution,
    FileAttributionReport,
    SPDX_IDENTIFIER,
    DEFAULT_LICENSE_NAME,
)


@pytest.fixture
def generator():
    return DMLicenseHeaderGenerator()


@pytest.fixture
def mock_authors():
    return [
        AuthorContribution(
            author_name="Alice Developer",
            author_email="alice@tgstation.org",
            commit_count=5,
            contribution_summary="Implemented core atmospheric controller datums.",
        ),
        AuthorContribution(
            author_name="Bob Maintainer",
            author_email="bob@tgstation.org",
            commit_count=2,
            contribution_summary="Refactored pipe flow iterations.",
        ),
    ]


def test_build_license_header_formatting(generator, mock_authors):
    """Verifies that generated license header includes SPDX tag, authors, commit counts, and contribution details."""
    header = generator.build_license_header("code/modules/atmospherics/controller.dm", mock_authors)
    assert "/*" in header
    assert "*/" in header
    assert "File: controller.dm" in header
    assert DEFAULT_LICENSE_NAME in header
    assert SPDX_IDENTIFIER in header
    assert "Alice Developer <alice@tgstation.org> (5 commits)" in header
    assert "Implemented core atmospheric controller datums." in header
    assert "Bob Maintainer <bob@tgstation.org> (2 commits)" in header
    assert "GNU Affero General Public License" in header


def test_is_file_already_attributed(generator):
    """Verifies detection of files that already contain license markers."""
    attributed_code = f"/*\n * {SPDX_IDENTIFIER}\n */\n/proc/test()\n"
    assert generator.is_file_already_attributed(attributed_code) is True

    clean_code = "// Simple comment\n/proc/test()\n"
    assert generator.is_file_already_attributed(clean_code) is False


def test_process_file_content_injection(generator, mock_authors):
    """Verifies successful injection of header on non-attributed file."""
    original_code = "/datum/controller/subsystem/air/proc/setup()\n\treturn 1\n"
    new_code, report = generator.process_file_content(
        "code/modules/atmospherics/air.dm",
        original_code,
        authors=mock_authors
    )

    assert report.applied is True
    assert report.already_attributed is False
    assert SPDX_IDENTIFIER in new_code
    assert original_code in new_code
    assert new_code.startswith("/*")


def test_idempotent_skipping_already_attributed(generator, mock_authors):
    """Verifies that files with existing license headers are preserved unchanged."""
    already_attributed_code = f"/*\n * {SPDX_IDENTIFIER}\n */\n/proc/noop()\n"
    new_code, report = generator.process_file_content(
        "code/modules/atmospherics/air.dm",
        already_attributed_code,
        authors=mock_authors
    )

    assert report.applied is False
    assert report.already_attributed is True
    assert new_code == already_attributed_code


def test_git_file_authors_fallback(generator):
    """Verifies that nonexistent or uncommitted files fall back gracefully to default maintainer attribution."""
    authors = generator.get_git_file_authors("nonexistent_virtual_file.dm")
    assert len(authors) >= 1
    assert "TGStation Development Team" in authors[0].author_name
