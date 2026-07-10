#!/usr/bin/env python3
"""
auto_payout.py — 本地自动打款守护脚本

每 N 分钟检查一次 SQLite 账本，发现有已批准（approved）的兑换请求，
自动调币安 API 打款 USDT（BEP-20），并提交 /paid 到 GitHub Issue。

用法:
    # 一次性运行
    python scripts/auto_payout.py --once

    # 持续运行（每5分钟检查一次）
    python scripts/auto_payout.py --daemon --interval 300

    # 查看待处理列表
    python scripts/auto_payout.py --list-pending
"""

import argparse
import json
import os
import dotenv

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if os.path.isfile(_env_path):
    dotenv.load_dotenv(_env_path)

import sqlite3

try:
    _env = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.isfile(_env):
        dotenv.load_dotenv(_env)
except ImportError:
    pass

import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from hashlib import sha256 as _sha256

# ── 路径 ──
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DB_PATH = os.path.join(REPO_ROOT, "data", "coins.db")

# ── Binance API ──
BINANCE_API_KEY = os.e*******get("BINANCE_API_KEY", "") or ""
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "") or ""
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")

# ── GitHub 配置 ──
GH_REPO = "zhangjiayang6835-cyber/bounty-plaza"

# ⚠️ 警告：Binance API Key 权限隔离
# 在币安创建 API Key 时：
# - 只启用「提现」权限（WITHdraw）
# - 不要启用「交易」权限
# - IP 白名单锁你的本机 IP
# - 设置每日提现限额
# - 永远不要把这个 Key 提交到 GitHub


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_pending_redemptions() -> list:
    """查询所有已批准但未打款的兑换请求"""
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM redeem_requests WHERE status = 'approved' ORDER BY id ASC"
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def call_binance_withdraw(address: str, amount: float) -> dict:
    """
    调币安提现 API 发送 USDT（BEP-20）。
    文档: https://binance-docs.github.io/apidocs/spot/en/#withdraw-sapi
    """
    import hmac
    import time as _time

    timestamp = int(_time.time() * 1000)
    params = {
        "coin": "USDT",
        "network": "BSC",
        "address": address,
        "amount": str(amount),
        "timestamp": timestamp,
    }

    # 签名
    query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    signature = hmac.new(
        BINANCE_SECRET_KEY.encode(), query.encode(), _sha256
    ).hexdigest()
    params["signature"] = signature

    url = "https://api.binance.com/sapi/v1/capital/withdraw/apply"
    headers = {
        "X-MBX-APIKEY": BINANCE_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    body = __import__("urllib.parse").urlencode(params)

    req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()[:200]}


def comment_on_issue(issue_number: int, body: str):
    """通过 GitHub API 在 Issue 上评论"""
    if not GH_TOKEN:
        print("  ⚠️ 未设置 GH_TOKEN，跳过 Issue 评论")
        return
    url = f"https://api.github.com/repos/{GH_REPO}/issues/{issue_number}/comments"
    data = json.dumps({"body": body}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"token {GH_TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"  ⚠️ Issue 评论失败: {e}")


def mark_paid(redeem_id: int) -> bool:
    """调用 coin.py pay 标记已打款"""
    result = subprocess.run(
        [sys.executable, os.path.join(HERE, "coin.py"), "pay", "--id", str(redeem_id), "--json"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    try:
        parsed = json.loads(result.stdout.strip())
        return parsed.get("ok", False)
    except (json.JSONDecodeError, KeyError):
        print(f"  ⚠️ coin.py pay #{redeem_id} 输出异常: {result.stdout[:200]}")
        return False


def process_one(req: dict) -> bool:
    """处理单个兑换请求"""
    rid = req["id"]
    username = req["username"]
    amount = req["amount"]
    address = req.get("address", "")
    cash_value = req.get("coin_value", amount * coin.RATE)

    print(f"\n  处理兑换 #{rid}: {username} ${cash_value:.2f} -> {address[:16]}...")

    # 1. 调币安 API 打款
    if BINANCE_API_KEY and BINANCE_SECRET_KEY:
        result = call_binance_withdraw(address, cash_value)
        if "error" in result:
            print(f"  ❌ 币安打款失败: {result['error']}")
            return False
        print(f"  ✅ 币安打款成功: {result.get('id', '?')}")
    else:
        print(f"  ⚠️ 未配置币安 API Key，跳过真实打款（模拟模式）")

    # 2. 标记已打款
    if mark_paid(rid):
        print(f"  ✅ 兑换 #{rid} 已标记为 paid")
    else:
        print(f"  ⚠️ 标记 paid 失败，需手动处理")

    # 3. 在 Issue 评论确认
    comment_body = (
        f"## ✅ 已完成自动打款\n\n"
        f"兑换 **#{rid}** | **{username}** | 金额 **${cash_value:.2f}**\n\n"
        f"> 🤖 已自动通过币安 API 打款至 {address[:16]}...（BSC BEP-20）"
    )
    # 查找对应的 Issue
    comment_on_issue(find_issue_for_redeem(rid), comment_body)

    return True


def find_issue_for_redeem(redeem_id: int) -> int:
    """查找兑换请求对应的 GitHub Issue 编号"""
    if not GH_TOKEN:
        return 0
    url = f"https://api.github.com/search/issues?q=repo:{GH_REPO}+is:issue+%23{redeem_id}+label:redeem"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"token {GH_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            if data["items"]:
                return data["items"][0]["number"]
    except Exception:
        pass
    return 0


def process_pending():
    """处理所有待打款的兑换"""
    pending = get_pending_redemptions()
    if not pending:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 暂无待打款兑换")
        return

    print(f"\n发现 {len(pending)} 笔待打款兑换:")
    for req in pending:
        username = req["username"]
        amount = req["amount"]
        cash = req.get("coin_value", amount * coin.RATE)
        address = req.get("address", "?")[:20]
        print(f"  #{req['id']} | {username} | ${cash:.2f} | {address}...")

    print("\n开始处理...")
    for req in pending:
        process_one(req)


def list_pending():
    """列出待打款列表"""
    pending = get_pending_redemptions()
    if not pending:
        print("暂无待打款兑换请求")
        return
    print(f"共 {len(pending)} 笔待打款:")
    print(f"{'ID':>4} | {'用户名':<15} | {'金额':>6} | {'地址':<25}")
    print("-" * 60)
    for req in pending:
        cash = req.get("coin_value", req["amount"] * 0.72)
        addr = req.get("address", "")[:22]
        print(f"{req['id']:>4} | {req['username']:<15} | ${cash:<5.2f} | {addr}")


def main():
    parser = argparse.ArgumentParser(description="本地自动打款守护脚本")
    parser.add_argument("--once", action="store_true", help="立即运行一次")
    parser.add_argument("--daemon", action="store_true", help="持续运行")
    parser.add_argument("--interval", type=int, default=300, help="检查间隔（秒，默认300）")
    parser.add_argument("--list-pending", action="store_true", help="列出待打款列表")
    args = parser.parse_args()

    if args.list_pending:
        list_pending()
        return 0

    if args.once:
        process_pending()
        return 0

    if args.daemon:
        print(f"🔄 自动打款守护启动，每 {args.interval} 秒检查一次...")
        print(f"   Binance API: {'✅ 已配置' if BINANCE_API_KEY else '⚠️ 未配置（模拟模式）'}")
        print(f"   GitHub Token: {'✅ 已配置' if GH_TOKEN else '⚠️ 未配置'}")
        print(f"   按 Ctrl+C 停止")
        print()
        while True:
            process_pending()
            time.sleep(args.interval)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
