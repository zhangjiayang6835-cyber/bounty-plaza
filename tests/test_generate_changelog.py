"""Unit tests for Git Changelog Generator & Claude Code Skill Subsystem.
Resolves Issue #504: [BOUNTY $50] SKILL: Generate a structured CHANGELOG from git.
Validates:
- Conventional commit message parsing (type, scope, breaking mark, description, PR numbers)
- Categorization into Added, Fixed, Changed, Removed
- Keep a Changelog Markdown rendering
- Breaking change highlighting
- Git log extraction and fallback handling
"""

import os
import pytest
from scripts.generate_changelog import (
    ChangelogGenerator,
    CommitEntry,
    CATEGORY_MAPPING,
)


def test_conventional_commit_parsing_categories():
    entry_feat = ChangelogGenerator.parse_commit_message("a1b2c3d", "Developer", "2026-09-04", "feat(auth): implement web3 signature login (#42)")
    assert entry_feat.category == "Added"
    assert entry_feat.scope == "auth"
    assert entry_feat.description == "implement web3 signature login (#42)"
    assert entry_feat.pr_number == "42"
    assert entry_feat.breaking is False

    entry_fix = ChangelogGenerator.parse_commit_message("b2c3d4e", "Developer", "2026-09-04", "fix(api): resolve race condition in token refresh")
    assert entry_fix.category == "Fixed"
    assert entry_fix.scope == "api"

    entry_refactor = ChangelogGenerator.parse_commit_message("c3d4e5f", "Developer", "2026-09-04", "refactor(engine): streamline reduction pipeline")
    assert entry_refactor.category == "Changed"
    assert entry_refactor.scope == "engine"

    entry_remove = ChangelogGenerator.parse_commit_message("d4e5f6a", "Developer", "2026-09-04", "remove: deprecate legacy v1 endpoints")
    assert entry_remove.category == "Removed"


def test_breaking_change_detection():
    entry_breaking = ChangelogGenerator.parse_commit_message(
        "e5f6a7b", "Architect", "2026-09-04", "feat(core)!: drop Python 3.8 support and migrate to 3.13"
    )
    assert entry_breaking.breaking is True
    assert entry_breaking.category == "Added"
    assert entry_breaking.scope == "core"


def test_markdown_generation_keep_a_changelog_format():
    commits = [
        CommitEntry(
            commit_hash="1111111",
            author_name="Alice",
            date_str="2026-09-04",
            raw_message="feat(ui): add dark mode switch (#101)",
            category="Added",
            scope="ui",
            description="add dark mode switch (#101)",
            pr_number="101",
            breaking=False,
        ),
        CommitEntry(
            commit_hash="2222222",
            author_name="Bob",
            date_str="2026-09-04",
            raw_message="fix(db): prevent SQLite lock contention",
            category="Fixed",
            scope="db",
            description="prevent SQLite lock contention",
            pr_number=None,
            breaking=False,
        ),
        CommitEntry(
            commit_hash="3333333",
            author_name="Charlie",
            date_str="2026-09-04",
            raw_message="refactor!: redesign plugin architecture",
            category="Changed",
            scope=None,
            description="redesign plugin architecture",
            pr_number=None,
            breaking=True,
        ),
    ]

    gen = ChangelogGenerator()
    md = gen.generate_markdown(commits, version_title="v1.2.0", release_date="2026-09-04")

    assert "## [v1.2.0] - 2026-09-04" in md
    assert "### ⚠️ Breaking Changes" in md
    assert "redesign plugin architecture (3333333)" in md
    assert "### Added" in md
    assert "- **ui**: add dark mode switch (#101) ([`1111111`])" in md
    assert "### Fixed" in md
    assert "- **db**: prevent SQLite lock contention ([`2222222`])" in md
    assert "### Changed" in md


def test_git_tag_and_commit_extraction_in_repo():
    gen = ChangelogGenerator(repo_path=".")
    commits = gen.get_commits(to_ref="HEAD")
    assert isinstance(commits, list)
    if commits:
        assert isinstance(commits[0], CommitEntry)
        assert commits[0].commit_hash
