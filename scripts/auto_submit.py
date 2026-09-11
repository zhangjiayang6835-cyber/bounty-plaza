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
import shutil
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


# ── 模板展开 (JSONTE / Jinja) ─────────────────────────────────────
#
# 构建流水线必须在同步到 .minecraft/development_behavior_packs (com.mojang)
# 之前，于 _temp/ 中完成模板展开，否则 BDS 会因原始模板语法报错：
#   [PackValidator][Error] Failed to parse JSON in 'blocks/custom_stair.json':
#   Syntax error: unexpected character '{' at line 4 column 12
#
# 支持两种模板语法：
#   - JSONTE:  {{ ... }}  (JSON Template Engine)
#   - Jinja2:  {% ... %} / {{ ... }} / {# ... #}

TEMPLATE_MARKERS = ("{{", "}}", "{%", "%}", "{#", "#}")


def _looks_like_template(text: str) -> bool:
    return any(marker in text for marker in TEMPLATE_MARKERS)


def _render_jinja(text: str, context: dict) -> str:
    """使用 Jinja2 渲染；若未安装则回退到极简替换。"""
    try:
        from jinja2 import Environment, StrictUndefined  # type: ignore
    except ImportError:
        # 极简回退：仅处理 {{ var }} 形式
        import re

        def _sub(match):
            key = match.group(1).strip()
            return str(context.get(key, match.group(0)))

        return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", _sub, text)

    env = Environment(
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        autoescape=False,
    )
    return env.from_string(text).render(**context)


def expand_templates_in_dir(root: str, context: dict = None) -> int:
    """
    递归展开 root 目录下所有文本文件中的模板表达式。

    返回被修改的文件数量。展开在 _temp/ 内进行，必须在同步到
    com.mojang 之前调用，以避免 BDS 解析到原始模板语法。
    """
    if context is None:
        context = {}

    expanded = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            # 仅处理文本类文件
            if not fname.lower().endswith(
                (".json", ".jsonte", ".jinja", ".jinja2", ".j2", ".txt", ".mcfunction", ".lang")
            ):
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    original = f.read()
            except (OSError, UnicodeDecodeError):
                continue

            if not _looks_like_template(original):
                continue

            rendered = _render_jinja(original, context)
            if rendered != original:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(rendered)
                expanded += 1

    return expanded


def clean_slate_build(temp_dir: str) -> None:
    """
    清空 _temp/ 以避免缓存模板污染。

    每次构建都从干净状态开始，防止上一次构建残留的已展开/未展开
    文件混入本次同步。
    """
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)


def build_and_sync(
    source_dir: str,
    temp_dir: str,
    dest_dir: str,
    context: dict = None,
) -> None:
    """
    正确的构建流水线顺序：

      1. 清空 _temp/（clean-slate，避免缓存污染）
      2. 将源文件复制到 _temp/
      3. 在 _temp/ 中展开模板表达式
      4. 将展开后的文件同步到目标目录（com.mojang）

    关键点：模板展开必须在同步之前完成，否则 BDS 会因原始
    模板语法（如 '{{'）而解析失败。
    """
    # 1. clean-slate
    clean_slate_build(temp_dir)

    # 2. 复制源文件到 _temp/
    for entry in os.listdir(source_dir):
        src = os.path.join(source_dir, entry)
        dst = os.path.join(temp_dir, entry)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    # 3. 在 _temp/ 中展开模板
    expanded = expand_templates_in_dir(temp_dir, context or {})
    print(f"  模板展开完成: {expanded} 个文件")

    # 4. 同步到目标目录（com.mojang）
    os.makedirs(dest_dir, exist_ok=True)
    for entry in os.listdir(temp_dir):
        src = os.path.join(temp_dir, entry)
        dst = os.path.join(dest_dir, entry)
        if os.path.isdir(src):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    print(f"  已同步到: {dest_dir}")


def apply_and_pr(fork: str, upstream: str, branch: str, code_file: str, message: str, target_file: str):
    """在 fork 上创建分支、提交代码、提 PR"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone fork
        subprocess.run(["git", "clone", f"https://github.com/{fork}.git", tmpdir], capture_output=True, check=True)

        # Create branch
        subprocess.run(["git", "-C", tmpdir, "checkout", "-b", branch], capture_output=True, check=True)

        # Copy winning code to target file
        dest = os.path.realpath(os.path.join(tmpdir, target_file))
        allowed = os.path.realpath(tmpdir)
        if not dest.startswith(allowed):
            raise ValueError(f"目标文件路径不在允许的目录中: {target_file}")
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
    parser.add_argument("--source-dir", default=None, help="行为包源目录（含模板）")
    parser.add_argument("--temp-dir", default="_temp", help="临时构建目录（模板展开在此进行）")
    parser.add_argument("--dest-dir", default=None, help="目标目录（com.mojang 开发文件夹）")
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
        if args.source_dir and args.dest_dir:
            print(f"     5. clean-slate 构建: {args.source_dir} -> {args.temp_dir} (展开模板) -> {args.dest_dir}")
        return 0

    # 若提供了源目录与目标目录，先执行正确的构建流水线：
    # clean-slate -> 复制到 _temp/ -> 展开模板 -> 同步到 com.mojang
    if args.source_dir and args.dest_dir:
        print(f"🔧 构建流水线 (模板展开先于同步)")
        build_and_sync(args.source_dir, args.temp_dir, args.dest_dir)

    fork = ensure_fork(args.upstream)
    apply_and_pr(fork, args.upstream, args.branch, args.code, args.message, args.target)

    print(f"✅ 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())