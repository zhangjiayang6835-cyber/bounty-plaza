#!/usr/bin/env python3
"""
Generate a structured CHANGELOG from git commit history.

This script uses GitPython to read commits, groups them by tags (versions),
and outputs a JSON structured changelog.

Usage:
  python scripts/generate_changelog.py [--repo-path PATH] [--output FILE]

If no repo-path is specified, assumes current directory is a git repo.
If no output file is specified, outputs to stdout.
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from git import Repo, TagReference


def get_tag_map(repo):
    """
    Get a dict of tag commit hexsha to tag name, using annotated tags if possible.
    """
    tag_map = {}
    for tag in repo.tags:
        # Use tag.commit.hexsha for lightweight tags,
        # or tag.tag.object.hexsha for annotated tags
        commit_hexsha = None
        try:
            if hasattr(tag, "tag") and tag.tag is not None:
                # annotated tag
                commit_hexsha = tag.tag.object.hexsha
            else:
                # lightweight tag
                commit_hexsha = tag.commit.hexsha
        except Exception:
            # fallback
            commit_hexsha = tag.commit.hexsha
        tag_map[commit_hexsha] = tag.name
    return tag_map


def generate_changelog(repo_path: str):
    repo = Repo(repo_path)
    if repo.bare:
        raise RuntimeError(f"Repository at {repo_path} is bare or invalid")

    tag_map = get_tag_map(repo)

    # Use commits in reverse chronological order
    commits = list(repo.iter_commits('HEAD'))

    # Group commits by tag (version). Commits not reachable by tags go to 'Unreleased'
    changelog = defaultdict(list)

