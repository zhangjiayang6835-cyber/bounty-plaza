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
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"API ERROR [{e.code}]: {err[:200]}", file=sys.stderr)
        sys.exit(1)


def ensure_fork(upstream: str) -> str:
    """确保已 fork 上游仓库，返回 fork 的 full_name"""
    owner = "zhangjiayang6835-cyber"
    fork_name = upstream.split("/")[1]

    # 检查是否已有 fork
    existing = api("GET", f"/repos/{owner}/{fork_name}")
    if existing.get("id"):
        print(f"  已存在 fork: {owner}/{fork_name}")
        return f"{owner}/{fork_name}"

    # 创建 fork
    print(f"  正在 fork {upstream}...")
    result = api("POST", f"/repos/{upstream}/forks")
    if result.get("full_name"):
        print(f"  Fork 成功: {result['full_name']}")
        return result["full_name"]
    print("  Fork 失败", file=sys.stderr)
    sys.exit(1)


def apply_and_pr(fork: str, upstream: str, branch: str, code_file: str, message: str, target_file: str):
    """在 fork 上创建分支、提交代码、提 PR"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone fork
        subprocess.run(["git", "clone", f"https://github.com/{fork}.git", tmpdir], capture_output=True, check=True)

        # Create branch
        subprocess.run(["git", "-C", tmpdir, "checkout", "-b", branch], capture_output=True, check=True)

        # Copy winning code to target file
        import shutil
        dest = os.path.join(tmpdir, target_file)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(code_file, dest)

        # Git add, commit, push
        subprocess.run(["git", "-C", tmpdir, "add", target_file], capture_output=True, check=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", message], capture_output=True, check=True)
        subprocess.run(["git", "-C", tmpdir, "push", "origin", branch], capture_output=True, check=True)

    # Create PR
    pr = api("POST", f"/repos/{upstream}/pulls", {
        "title": message,
        "head": f"{fork.split('/')[0]}:{branch}",
        "base": "main",
        "body": f"🤖 由 bounty-plaza 自动提交\n\n此修复由 bounty-plaza 贡献者完成，已通过自动评分（≥90 分）。",
    })
    print(f"  PR 已创建: {pr.get('html_url', '?')}")
    return pr.get("number")


def main():
    parser = argparse.ArgumentParser(description="自动代提交到上游仓库")
    parser.add_argument("--upstream", required=True, help="上游仓库 owner/repo")
    parser.add_argument("--branch", default="fix/bounty", help="分支名")
    parser.add_argument("--code", required=True, help="获胜代码文件路径")
    parser.add_argument("--target", default="fix.py", help="上游仓库中的目标文件路径")
    parser.add_argument("--message", default="fix: security vulnerability", help="PR 标题")
    parser.add_argument("--dry-run", action="store_true", help="仅打印将执行的操作")
    args = parser.parse_args()

    print(f"🚀 自动代提交流程")
    print(f"   上游: {args.upstream}")
    print(f"   代码: {args.code}")

    if args.dry_run:
        print(f"   将执行:")
        print(f"     1. fork {args.upstream}")
        print(f"     2. 创建分支 {args.branch}")
        print(f"     3. 应用代码到 {args.target}")
        print(f"     4. push + 提 PR")
        return 0

    fork = ensure_fork(args.upstream)
    apply_and_pr(fork, args.upstream, args.branch, args.code, args.message, args.target)

    print(f"✅ 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
