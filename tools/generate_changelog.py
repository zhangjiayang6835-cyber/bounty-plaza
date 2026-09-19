"""Structured Git Changelog Generator.
Resolves Issue #490 / claude-builders-bounty/claude-builders-bounty#1 ($50 USD).

Features:
- Inspects git commit log since latest tag (falls back to initial commit if no tags)
- Categorizes commits into Added, Fixed, Changed, and Removed
- Formats standard Keep-a-Changelog Markdown
- Generates or prepends to CHANGELOG.md
"""

from datetime import datetime, timezone
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple


CATEGORY_PATTERNS = {
    "Added": [
        re.compile(r"^(?:feat|add|feature|new)(?:\([^)]*\))?!*[:!]\s*(.+)", re.IGNORECASE),
        re.compile(r"^(?:added|add|create|implement)\s+(.+)", re.IGNORECASE),
    ],
    "Fixed": [
        re.compile(r"^(?:fix|bug|repair|patch|hotfix)(?:\([^)]*\))?!*[:!]\s*(.+)", re.IGNORECASE),
        re.compile(r"^(?:fixed|fix|resolve|resolves|repaired)\s+(.+)", re.IGNORECASE),
    ],
    "Removed": [
        re.compile(r"^(?:revert|remove|drop|deprecate|delete)(?:\([^)]*\))?!*[:!]\s*(.+)", re.IGNORECASE),
        re.compile(r"^(?:remove|removed|delete|deleted|drop|dropped|deprecate|deprecated)\s+(.+)", re.IGNORECASE),
    ],
    "Changed": [
        re.compile(r"^(?:refactor|perf|chore|style|build|ci|docs|test|update|bump)(?:\([^)]*\))?!*[:!]\s*(.+)", re.IGNORECASE),
        re.compile(r"^(?:changed|updated|refactored|improved|bumped)\s+(.+)", re.IGNORECASE),
    ],
}


def run_git_cmd(args: List[str], repo_path: str = ".") -> str:
    """Executes a git command and returns stdout stripped."""
    result = subprocess.run(
        ["git"] + args,
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_latest_tag(repo_path: str = ".") -> Optional[str]:
    """Retrieves the most recent reachable git tag."""
    tag = run_git_cmd(["describe", "--tags", "--abbrev=0"], repo_path=repo_path)
    return tag if tag else None


def get_commits_since(tag: Optional[str] = None, repo_path: str = ".") -> List[Tuple[str, str, str]]:
    """Fetches list of commits as (hash, author, subject)."""
    rev_range = f"{tag}..HEAD" if tag else "HEAD"
    raw_log = run_git_cmd(["log", rev_range, "--pretty=format:%h%x09%an%x09%s"], repo_path=repo_path)
    if not raw_log:
        return []

    commits = []
    for line in raw_log.splitlines():
        parts = line.strip().split("\t")
        if len(parts) >= 3:
            commits.append((parts[0], parts[1], parts[2]))
        elif len(parts) == 2:
            commits.append((parts[0], "Unknown", parts[1]))
    return commits


def categorize_commit(subject: str) -> Tuple[str, str]:
    """Categorizes a commit subject into (Category, CleanedDescription)."""
    clean_sub = subject.strip()

    # Match category patterns
    for cat in ["Added", "Fixed", "Removed", "Changed"]:
        for pat in CATEGORY_PATTERNS[cat]:
            m = pat.match(clean_sub)
            if m:
                desc = m.group(1).strip()
                # Capitalize first letter of description
                if desc:
                    desc = desc[0].upper() + desc[1:]
                return cat, desc

    # Default fallback
    return "Changed", clean_sub


def build_changelog_markdown(
    commits: List[Tuple[str, str, str]],
    version: str = "Unreleased",
    previous_tag: Optional[str] = None,
    release_date: Optional[str] = None,
) -> str:
    """Constructs formatted Keep-a-Changelog Markdown."""
    if not release_date:
        release_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    categorized: Dict[str, List[Tuple[str, str]]] = {
        "Added": [],
        "Fixed": [],
        "Changed": [],
        "Removed": [],
    }

    for commit_hash, author, subject in commits:
        category, desc = categorize_commit(subject)
        categorized[category].append((commit_hash, desc))

    lines = [
        f"## [{version}] - {release_date}",
        "",
    ]
    if previous_tag:
        lines.insert(1, f"*Changes since tag `{previous_tag}`*")
        lines.insert(2, "")

    total_entries = 0
    for cat in ["Added", "Fixed", "Changed", "Removed"]:
        items = categorized[cat]
        if items:
            lines.append(f"### {cat}")
            for c_hash, desc in items:
                lines.append(f"- {desc} (`{c_hash}`)")
                total_entries += 1
            lines.append("")

    if total_entries == 0:
        lines.append("_No notable changes detected._")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def generate_changelog(
    repo_path: str = ".",
    output_file: str = "CHANGELOG.md",
    version: str = "Unreleased",
    dry_run: bool = False,
) -> str:
    """Main generation routine."""
    tag = get_latest_tag(repo_path=repo_path)
    commits = get_commits_since(tag=tag, repo_path=repo_path)
    content = build_changelog_markdown(commits, version=version, previous_tag=tag)

    if not dry_run and output_file:
        existing = ""
        full_out_path = os.path.join(repo_path, output_file) if not os.path.isabs(output_file) else output_file
        if os.path.exists(full_out_path):
            with open(full_out_path, "r", encoding="utf-8") as f:
                existing = f.read()

        header = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
        if existing.startswith("# Changelog"):
            # Insert below header
            body = existing.split("# Changelog\n\n", 1)[-1]
            # Strip standard preamble if present
            if body.startswith("All notable changes to this project will be documented in this file.\n\n"):
                body = body[len("All notable changes to this project will be documented in this file.\n\n"):]
            new_file_content = header + content + "\n" + body.lstrip()
        else:
            new_file_content = header + content + ("\n" + existing if existing else "")

        with open(full_out_path, "w", encoding="utf-8") as f:
            f.write(new_file_content)

    return content


if __name__ == "__main__":
    out = "CHANGELOG.md"
    repo = "."
    dry = "--dry-run" in sys.argv

    res = generate_changelog(repo_path=repo, output_file=out, dry_run=dry)
    print(res)
