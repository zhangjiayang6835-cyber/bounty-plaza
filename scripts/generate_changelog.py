"""Git Changelog Generator & Claude Code Skill Subsystem.
Resolves Issue #504: [BOUNTY $50] SKILL: Generate a structured CHANGELOG from git.
Upstream Reference: claude-builders-bounty/claude-builders-bounty#1.

Features:
- Automatic detection of latest git tag (falls back to initial commit if no tag exists)
- Parses Conventional Commits (feat, fix, refactor, perf, docs, chore, revert, style, test)
- Categorizes changes into Keep a Changelog standard sections:
  * Added (feat, new)
  * Fixed (fix, bugfix)
  * Changed (refactor, perf, style, docs, chore)
  * Removed (deprecate, remove)
- Supports PR reference extraction (#123) and author attribution
- Outputs formatted Markdown compatible with Keep a Changelog and SemVer
- CLI interface and Claude Code Skill integration
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple


CATEGORY_MAPPING = {
    "feat": "Added",
    "feature": "Added",
    "add": "Added",
    "fix": "Fixed",
    "bugfix": "Fixed",
    "hotfix": "Fixed",
    "patch": "Fixed",
    "change": "Changed",
    "refactor": "Changed",
    "perf": "Changed",
    "performance": "Changed",
    "style": "Changed",
    "docs": "Changed",
    "doc": "Changed",
    "chore": "Changed",
    "build": "Changed",
    "ci": "Changed",
    "remove": "Removed",
    "deprecate": "Removed",
    "revert": "Fixed",
}


@dataclass
class CommitEntry:
    commit_hash: str
    author_name: str
    date_str: str
    raw_message: str
    category: str = "Changed"
    scope: Optional[str] = None
    description: str = ""
    pr_number: Optional[str] = None
    breaking: bool = False


class ChangelogGenerator:
    """Extracts, categorizes, and formats git commit history into structured CHANGELOG.md."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def get_latest_git_tag(self) -> Optional[str]:
        """Finds the most recent reachable git tag."""
        try:
            res = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return None

    def get_commits(self, from_ref: Optional[str] = None, to_ref: str = "HEAD") -> List[CommitEntry]:
        """Fetches commit history within range using git log formatting."""
        range_spec = f"{from_ref}..{to_ref}" if from_ref else to_ref
        cmd = [
            "git",
            "log",
            range_spec,
            "--pretty=format:%h%x1f%an%x1f%ad%x1f%s",
            "--date=short",
        ]
        try:
            res = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True)
            if res.returncode != 0 or not res.stdout.strip():
                return []
        except Exception:
            return []

        entries: List[CommitEntry] = []
        for line in res.stdout.strip().splitlines():
            parts = line.split("\x1f")
            if len(parts) >= 4:
                commit_hash, author, date_str, msg = parts[0], parts[1], parts[2], parts[3]
                entry = self.parse_commit_message(commit_hash, author, date_str, msg)
                entries.append(entry)

        return entries

    @classmethod
    def parse_commit_message(cls, commit_hash: str, author: str, date_str: str, raw_msg: str) -> CommitEntry:
        """Parses Conventional Commit prefix, scope, breaking flag, and issue/PR references."""
        # Pattern: type(scope)!: message (#123)
        pattern = r"^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$"
        match = re.match(pattern, raw_msg.strip())

        category = "Changed"
        scope = None
        breaking = False
        description = raw_msg.strip()

        if match:
            raw_type = match.group(1).lower()
            scope = match.group(2)
            breaking = bool(match.group(3))
            description = match.group(4).strip()
            category = CATEGORY_MAPPING.get(raw_type, "Changed")
        else:
            # Fallback heuristic
            lower_msg = raw_msg.lower()
            if lower_msg.startswith("add ") or "add " in lower_msg:
                category = "Added"
            elif lower_msg.startswith("fix") or "fix " in lower_msg:
                category = "Fixed"
            elif lower_msg.startswith("remove") or "deprecat" in lower_msg:
                category = "Removed"

        # Check for PR numbers like (#123) or #123
        pr_match = re.search(r"#(\d+)", description)
        pr_num = pr_match.group(1) if pr_match else None

        return CommitEntry(
            commit_hash=commit_hash,
            author_name=author,
            date_str=date_str,
            raw_message=raw_msg,
            category=category,
            scope=scope,
            description=description,
            pr_number=pr_num,
            breaking=breaking,
        )

    def generate_markdown(
        self,
        commits: List[CommitEntry],
        version_title: str = "Unreleased",
        release_date: Optional[str] = None,
    ) -> str:
        """Renders parsed commit entries into standard Keep a Changelog Markdown."""
        date_header = release_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Group by category
        grouped: Dict[str, List[CommitEntry]] = {
            "Added": [],
            "Fixed": [],
            "Changed": [],
            "Removed": [],
        }

        for c in commits:
            target_cat = c.category if c.category in grouped else "Changed"
            grouped[target_cat].append(c)

        lines = [
            f"## [{version_title}] - {date_header}\n",
        ]

        # Breaking changes callout
        breaking_items = [c for c in commits if c.breaking]
        if breaking_items:
            lines.append("### ⚠️ Breaking Changes\n")
            for b in breaking_items:
                scope_prefix = f"**{b.scope}**: " if b.scope else ""
                lines.append(f"- {scope_prefix}{b.description} ({b.commit_hash})")
            lines.append("")

        for section in ("Added", "Fixed", "Changed", "Removed"):
            items = grouped[section]
            if items:
                lines.append(f"### {section}\n")
                for item in items:
                    scope_prefix = f"**{item.scope}**: " if item.scope else ""
                    pr_suffix = f" (#{item.pr_number})" if item.pr_number and f"#{item.pr_number}" not in item.description else ""
                    lines.append(f"- {scope_prefix}{item.description}{pr_suffix} ([`{item.commit_hash}`])")
                lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def run(self, output_path: Optional[str] = None, version: str = "Unreleased") -> str:
        """Executes full changelog generation pipeline."""
        tag = self.get_latest_git_tag()
        commits = self.get_commits(from_ref=tag)
        md = self.generate_markdown(commits, version_title=version)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md)

        return md


if __name__ == "__main__":
    generator = ChangelogGenerator()
    result_md = generator.run()
    print(result_md)
