import os
import shutil
import subprocess
import tempfile
import pytest

from tools.generate_changelog import (
    categorize_commit,
    build_changelog_markdown,
    generate_changelog,
)


def test_categorize_commit():
    assert categorize_commit("feat: add automated swap router") == ("Added", "Add automated swap router")
    assert categorize_commit("feat(api)!: add web3 websocket listener") == ("Added", "Add web3 websocket listener")
    assert categorize_commit("fix: resolve off-by-one error in solver") == ("Fixed", "Resolve off-by-one error in solver")
    assert categorize_commit("bug(engine): repair unclosed db session") == ("Fixed", "Repair unclosed db session")
    assert categorize_commit("revert: drop legacy rest poller") == ("Removed", "Drop legacy rest poller")
    assert categorize_commit("remove deprecated telemetry endpoint") == ("Removed", "Deprecated telemetry endpoint")
    assert categorize_commit("refactor(core): streamline worker concurrency") == ("Changed", "Streamline worker concurrency")
    assert categorize_commit("chore: bump dependencies to latest") == ("Changed", "Bump dependencies to latest")
    assert categorize_commit("docs: update runbook instructions") == ("Changed", "Update runbook instructions")


def test_build_changelog_markdown():
    mock_commits = [
        ("abc1234", "Wilian Colombo", "feat: add multi-currency arbitrage engine"),
        ("def5678", "Wilian Colombo", "fix: repair memory leak in websocket subscriber"),
        ("ghi9012", "Wilian Colombo", "refactor: simplify order book snapshot deserialization"),
        ("jkl3456", "Wilian Colombo", "revert: remove unkeyed cache header bypass"),
    ]

    md = build_changelog_markdown(
        mock_commits,
        version="v1.2.0",
        previous_tag="v1.1.0",
        release_date="2026-09-04",
    )

    assert "## [v1.2.0] - 2026-09-04" in md
    assert "*Changes since tag `v1.1.0`*" in md
    assert "### Added" in md
    assert "- Add multi-currency arbitrage engine (`abc1234`)" in md
    assert "### Fixed" in md
    assert "- Repair memory leak in websocket subscriber (`def5678`)" in md
    assert "### Changed" in md
    assert "- Simplify order book snapshot deserialization (`ghi9012`)" in md
    assert "### Removed" in md
    assert "- Remove unkeyed cache header bypass (`jkl3456`)" in md


def test_generate_changelog_in_git_repo():
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize test git repository
        subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True)

        # Commit 1
        with open(os.path.join(temp_dir, "file1.txt"), "w") as f:
            f.write("Initial")
        subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "feat: initial system setup"], cwd=temp_dir, check=True)
        subprocess.run(["git", "tag", "v0.1.0"], cwd=temp_dir, check=True)

        # Commit 2 (after tag)
        with open(os.path.join(temp_dir, "file2.txt"), "w") as f:
            f.write("Feature 2")
        subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "feat: implement high frequency router"], cwd=temp_dir, check=True)

        # Commit 3 (after tag)
        with open(os.path.join(temp_dir, "file1.txt"), "a") as f:
            f.write("\nFix")
        subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "fix: correct slippage calculation"], cwd=temp_dir, check=True)

        changelog_file = os.path.join(temp_dir, "CHANGELOG.md")
        result = generate_changelog(repo_path=temp_dir, output_file=changelog_file, version="v0.2.0")

        assert "## [v0.2.0]" in result
        assert "### Added" in result
        assert "Implement high frequency router" in result
        assert "### Fixed" in result
        assert "Correct slippage calculation" in result

        # Verify physical file written
        assert os.path.exists(changelog_file)
        with open(changelog_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "# Changelog" in content
            assert "Implement high frequency router" in content
    finally:
        shutil.rmtree(temp_dir)
