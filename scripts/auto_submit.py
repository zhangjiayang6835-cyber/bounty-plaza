#!/usr/bin/env python3
"""
自动代提交脚本 — Auto Submit
将获胜者的代码自动提交到上游 GitHub 仓库（提 PR）。

流程:
  1. fork 上游仓库（如果还没 fork）
  2. 创建新分支
  3. 应用获胜代码
  4. git push
  5. 向上游提 PR

用法:
    python scripts/auto_submit.py --upstream <owner/repo> --branch <branch> --code <file> --message "<PR title>"
    python scripts/auto_submit.py --dry-run --upstream <owner/repo> --code <file>
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request


def api(method: str, path: str, data: dict = None) -> dict:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("FATAL: 设置 GH_TOKEN 环境变量", file=sys.stderr)
        sys.exit(1)
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"token {token}",
        "User-Agent": "bounty-plaza-bot",
        "Accept": "application/vnd.github+json",
    }
    body = json.dumps(data).encode() if data else None
