#!/usr/bin/env python3
"""
积分币系统 — Coin System
独立账本，SQLite 存储，完整审计日志。
每笔交易防篡改，每笔兑换可追溯。

用法:
    python scripts/coin.py balance <user>
    python scripts/coin.py transfer --from <sender> --to <receiver> --amount <n> --reason "<text>"
    python scripts/coin.py redeem --user <user> --amount <n> --address "<paypal/usdt>"
    python scripts/coin.py approve --id <redeem_id>
    python scripts/coin.py reject --id <redeem_id>
    python scripts/coin.py ledger
    python scripts/coin.py audit
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "coins.db")

RATE = 0.72            # 1 积分 = 0.72 USD
MIN_REDEEM = 1          # 无最低限制（1积分即可兑换）


def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            username    TEXT PRIMARY KEY,
            balance     INTEGER NOT NULL DEFAULT 0 CHECK(balance >= 0),
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_type     TEXT NOT NULL CHECK(tx_type IN ('transfer','redeem','approve','reject','cancel')),
            from_user   TEXT,
            to_user     TEXT,
            amount      INTEGER NOT NULL,
            reason      TEXT,
            ref_id      TEXT,
            prev_hash   TEXT NOT NULL,
            hash        TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'completed' CHECK(status IN ('completed','pending','approved','rejected','cancelled')),
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (from_user) REFERENCES accounts(username),
            FOREIGN KEY (to_user) REFERENCES accounts(username)
        );

        CREATE TABLE IF NOT EXISTS redeem_requests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL,
            amount      INTEGER NOT NULL,
            coin_value  REAL NOT NULL,
            address     TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected','paid')),
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (username) REFERENCES accounts(username)
        );

        CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(from_user, to_user);
        CREATE INDEX IF NOT EXISTS idx_redeem_user ON redeem_requests(username);
        CREATE INDEX IF NOT EXISTS idx_redeem_status ON redeem_requests(status);
        CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions(status);
        CREATE INDEX IF NOT EXISTS idx_tx_created ON transactions(created_at);
    """)
    conn.commit()
    conn.close()


def compute_hash(row: dict) -> str:
    raw = f"{str(row.get('prev_hash') or '')}|{str(row.get('tx_type') or '')}|{str(row.get('from_user') or '')}|{str(row.get('to_user') or '')}|{row.get('amount',0)}|{str(row.get('reason') or '')}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_last_hash(conn) -> str:
    cur = conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    return row["hash"] if row else "0" * 64


def get_balance(conn, username: str) -> int:
    cur = conn.execute("SELECT balance FROM accounts WHERE username = ?", (username,))
    row = cur.fetchone()
    return row["balance"] if row else 0


def ensure_account(conn, username: str):
    cur = conn.execute("SELECT 1 FROM accounts WHERE username = ?", (username,))
    if not cur.fetchone():
        conn.execute("INSERT INTO accounts (username, balance) VALUES (?, 0)", (username,))


def cmd_balance(args):
    conn = get_db()
    if args.init:
        ensure_account(conn, "admin")
        cur = conn.execute("SELECT balance FROM accounts WHERE username = 'admin'")
        bal = cur.fetchone()[0]
        if bal == 0:
            conn.execute("UPDATE accounts SET balance = 100000, updated_at = datetime('now') WHERE username = 'admin'")
            conn.commit()
            bal = 100000
            print("✅ Admin account initialized with 100,000 coins")
        else:
            print(f"Admin account ready (balance: {bal} coins)")
    balance = get_balance(conn, args.user)
    conn.close()
    cash = balance * RATE
    print(f"{args.user}: {balance} 积分币 = ${cash:.2f}")
    return 0


def cmd_transfer(args):
    conn = get_db()
    try:
        ensure_account(conn, args.from_user)
        ensure_account(conn, args.to_user)

        # 原子扣款：balance >= amount 时才扣，避免竞态双花
        cur = conn.execute(
            "UPDATE accounts SET balance = balance - ? WHERE username = ? AND balance >= ?",
            (args.amount, args.from_user, args.amount)
        )
        if cur.rowcount == 0:
            print(f"ERROR: {args.from_user} 余额不足或并发冲突")
            return 1

        prev_hash = get_last_hash(conn)
        tx_data = {
            "tx_type": "transfer", "from_user": args.from_user,
            "to_user": args.to_user, "amount": args.amount,
            "reason": args.reason, "prev_hash": prev_hash,
        }
        tx_data["hash"] = compute_hash(tx_data)

        conn.execute(
            "INSERT INTO transactions (tx_type, from_user, to_user, amount, reason, prev_hash, hash) VALUES (?,?,?,?,?,?,?)",
            (tx_data["tx_type"], tx_data["from_user"], tx_data["to_user"],
             tx_data["amount"], tx_data["reason"], tx_data["prev_hash"], tx_data["hash"])
        )
        conn.execute(
            "UPDATE accounts SET balance = balance + ?, updated_at = datetime('now') WHERE username = ?",
            (args.amount, args.to_user)
        )
        conn.commit()
        print(f"✅ 转账成功: {args.from_user} → {args.to_user} {args.amount} 积分币")
        return 0
    finally:
        conn.close()


def cmd_redeem(args):
    conn = get_db()
    try:
        ensure_account(conn, args.user)
        balance = get_balance(conn, args.user)
        if balance < args.amount:
            print(f"ERROR: {args.user} 余额不足 ({balance} < {args.amount})")
            return 1
        if args.amount < MIN_REDEEM:
            print(f"ERROR: 兑换数量低于最低限制 ({MIN_REDEEM})")
            return 1

        coin_value = args.amount * RATE
        cur = conn.execute(
            "INSERT INTO redeem_requests (username, amount, coin_value, address, status) VALUES (?,?,?,?, 'pending')",
            (args.user, args.amount, coin_value, args.address)
        )
        redeem_id = cur.lastrowid

        # 冻结余额
        conn.execute(
            "UPDATE accounts SET balance = balance - ?, updated_at = datetime('now') WHERE username = ?",
            (args.amount, args.user)
        )

        prev_hash = get_last_hash(conn)
        tx_data = {
            "tx_type": "redeem", "from_user": args.user,
            "to_user": None, "amount": args.amount,
            "reason": f"redeem #{redeem_id} → {args.address}", "prev_hash": prev_hash,
        }
        tx_data["hash"] = compute_hash(tx_data)
        conn.execute(
            "INSERT INTO transactions (tx_type, from_user, to_user, amount, reason, ref_id, prev_hash, hash, status) VALUES (?,?,?,?,?,?,?,?, 'pending')",
            (tx_data["tx_type"], tx_data["from_user"], tx_data["to_user"],
             tx_data["amount"], tx_data["reason"], str(redeem_id),
             tx_data["prev_hash"], tx_data["hash"])
        )
        conn.commit()

        if getattr(args, "json", False):
            print(json.dumps({
                "ok": True, "redeem_id": redeem_id, "user": args.user,
                "amount": args.amount, "coin_value": coin_value,
                "address": args.address, "status": "pending",
            }, ensure_ascii=False))
        else:
            print(f"✅ 兑换申请已提交 #{redeem_id}: {args.amount} 积分币 = ${coin_value:.2f}")
            print(f"   收款地址: {args.address}")
            print(f"   状态: pending（等待管理员审批）")
        return 0
    finally:
        conn.close()


def cmd_approve(args):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM redeem_requests WHERE id = ?", (args.id,))
        req = cur.fetchone()
        if not req:
            print(f"ERROR: 兑换申请 #{args.id} 不存在")
            return 1
        if req["status"] != "pending":
            print(f"ERROR: 兑换申请 #{args.id} 状态为 {req['status']}，无法审批")
            return 1

        conn.execute(
            "UPDATE redeem_requests SET status = 'approved', updated_at = datetime('now') WHERE id = ?",
            (args.id,)
        )
        conn.execute(
            "UPDATE transactions SET status = 'approved' WHERE ref_id = ? AND tx_type = 'redeem'",
            (str(args.id),)
        )
        conn.commit()
        print(f"✅ 兑换申请 #{args.id} 已批准")
        return 0
    finally:
        conn.close()


def cmd_reject(args):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM redeem_requests WHERE id = ?", (args.id,))
        req = cur.fetchone()
        if not req:
            print(f"ERROR: 兑换申请 #{args.id} 不存在")
            return 1
        if req["status"] != "pending":
            print(f"ERROR: 兑换申请 #{args.id} 状态为 {req['status']}，无法拒绝")
            return 1

        # 退还余额
        conn.execute(
            "UPDATE accounts SET balance = balance + ?, updated_at = datetime('now') WHERE username = ?",
            (req["amount"], req["username"])
        )
        conn.execute(
            "UPDATE redeem_requests SET status = 'rejected', updated_at = datetime('now') WHERE id = ?",
            (args.id,)
        )
        conn.execute(
            "UPDATE transactions SET status = 'rejected' WHERE ref_id = ? AND tx_type = 'redeem'",
            (str(args.id),)
        )
        conn.commit()
        print(f"✅ 兑换申请 #{args.id} 已拒绝，{req['amount']} 积分币已退还 {req['username']}")
        return 0
    finally:
        conn.close()


def cmd_ledger(args):
    conn = get_db()
    cur = conn.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (args.limit,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("(无交易记录)")
        return 0
    print(f"{'ID':<6} {'类型':<10} {'从':<16} {'到':<16} {'数量':<10} {'状态':<10} {'时间'}")
    print("-" * 90)
    for r in rows:
        print(f"{r['id']:<6} {r['tx_type']:<10} {str(r['from_user'] or '-'):<16} "
              f"{str(r['to_user'] or '-'):<16} {r['amount']:<10} {r['status']:<10} {r['created_at']}")
    return 0


def cmd_audit(args):
    conn = get_db()
    cur = conn.execute("SELECT * FROM transactions ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    prev = "0" * 64
    broken = 0
    for r in rows:
        expected = compute_hash({
            "prev_hash": prev, "tx_type": r["tx_type"],
            "from_user": r["from_user"], "to_user": r["to_user"],
            "amount": r["amount"], "reason": r["reason"],
        })
        if r["prev_hash"] != prev or r["hash"] != expected:
            print(f"❌ 交易 #{r['id']} 哈希链断裂")
            broken += 1
        prev = r["hash"]

    if broken == 0:
        print(f"✅ 审计通过：{len(rows)} 笔交易哈希链完整")
        return 0
    print(f"❌ 审计失败：{broken} 笔交易异常")
    return 1


def main():
    parser = argparse.ArgumentParser(description="积分币系统")
    sub = parser.add_subparsers(dest="command", required=True)

    p_bal = sub.add_parser("balance", help="查询余额")
    p_bal.add_argument("user")
    p_bal.add_argument("--init", action="store_true", help="初始化 admin 账户")
    p_bal.set_defaults(func=cmd_balance)

    p_tr = sub.add_parser("transfer", help="转账")
    p_tr.add_argument("--from", dest="from_user", required=True)
    p_tr.add_argument("--to", dest="to_user", required=True)
    p_tr.add_argument("--amount", type=int, required=True)
    p_tr.add_argument("--reason", default="")
    p_tr.set_defaults(func=cmd_transfer)

    p_rd = sub.add_parser("redeem", help="兑换")
    p_rd.add_argument("--user", required=True)
    p_rd.add_argument("--amount", type=int, required=True)
    p_rd.add_argument("--address", required=True)
    p_rd.add_argument("--note", default="")
    p_rd.add_argument("--auto", action="store_true")
    p_rd.add_argument("--json", action="store_true")
    p_rd.set_defaults(func=cmd_redeem)

    p_ap = sub.add_parser("approve", help="批准兑换")
    p_ap.add_argument("--id", type=int, required=True)
    p_ap.set_defaults(func=cmd_approve)

    p_rj = sub.add_parser("reject", help="拒绝兑换")
    p_rj.add_argument("--id", type=int, required=True)
    p_rj.set_defaults(func=cmd_reject)

    p_lg = sub.add_parser("ledger", help="查看账本")
    p_lg.add_argument("--limit", type=int, default=50)
    p_lg.set_defaults(func=cmd_ledger)

    p_au = sub.add_parser("audit", help="审计哈希链")
    p_au.set_defaults(func=cmd_audit)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())