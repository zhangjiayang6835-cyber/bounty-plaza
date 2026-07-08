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

RATE = 0.0001          # 100 积分币 = $0.01
MIN_REDEEM = 10000     # 最低兑换 10,000 积分币


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
            balance     INTEGER NOT NULL DEFAULT 0,
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
    """)
    conn.commit()
    conn.close()


def compute_hash(row: dict) -> str:
    raw = f"{row.get('prev_hash','')}|{row.get('tx_type','')}|{row.get('from_user','')}|{row.get('to_user','')}|{row.get('amount',0)}|{row.get('reason','')}"
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

        from_bal = get_balance(conn, args.from_user)
        if from_bal < args.amount:
            print(f"ERROR: {args.from_user} 余额不足（{from_bal} < {args.amount}）")
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
        conn.execute("UPDATE accounts SET balance = balance - ? WHERE username = ?", (args.amount, args.from_user))
        conn.execute("UPDATE accounts SET balance = balance + ? WHERE username = ?", (args.amount, args.to_user))
        conn.commit()
        print(f"✅ 转账成功: {args.from_user} → {args.to_user} 共 {args.amount} 积分币")
        print(f"   原因: {args.reason}")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        return 1
    finally:
        conn.close()
    return 0


def cmd_redeem(args):
    conn = get_db()
    try:
        balance = get_balance(conn, args.user)
        if balance < args.amount:
            print(f"ERROR: {args.user} 余额不足（{balance} < {args.amount}）")
            return 1
        if args.amount < MIN_REDEEM:
            print(f"ERROR: 最低兑换 {MIN_REDEEM} 积分币")
            return 1

        cash_value = args.amount * RATE
        ensure_account(conn, args.user)
        conn.execute(
            "INSERT INTO redeem_requests (username, amount, coin_value, address, status) VALUES (?,?,?,?,'pending')",
            (args.user, args.amount, cash_value, args.address)
        )
        conn.commit()
        print(f"✅ 兑换申请已提交: {args.user} 兑换 {args.amount} 积分币 = ${cash_value:.2f}")
        print(f"   收款地址: {args.address}")
        print(f"   等待管理员审核（ID: {conn.execute('SELECT last_insert_rowid()').fetchone()[0]}）")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        return 1
    finally:
        conn.close()
    return 0


def cmd_approve(args):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM redeem_requests WHERE id = ? AND status = 'pending'", (args.id,))
        req = cur.fetchone()
        if not req:
            print(f"ERROR: 兑换请求 #{args.id} 不存在或已处理")
            return 1

        username = req["username"]
        amount = req["amount"]

        balance = get_balance(conn, username)
        if balance < amount:
            print(f"ERROR: {username} 余额不足（{balance} < {amount}）")
            return 1

        prev_hash = get_last_hash(conn)
        tx_data = {
            "tx_type": "redeem", "from_user": username, "to_user": None,
            "amount": amount, "reason": f"兑换请求 #{args.id}", "prev_hash": prev_hash,
        }
        tx_data["hash"] = compute_hash(tx_data)

        conn.execute(
            "INSERT INTO transactions (tx_type, from_user, amount, reason, prev_hash, hash, status) VALUES (?,?,?,?,?,?,'approved')",
            ("redeem", username, amount, f"兑换请求 #{args.id}", tx_data["prev_hash"], tx_data["hash"])
        )
        conn.execute("UPDATE accounts SET balance = balance - ? WHERE username = ?", (amount, username))
        conn.execute("UPDATE redeem_requests SET status = 'approved', updated_at = datetime('now') WHERE id = ?", (args.id,))
        conn.commit()

        cash = amount * RATE
        print(f"✅ 兑换 #{args.id} 已批准: {username} 获得 ${cash:.2f}")
        print(f"   打款地址: {req['address']}")
        print(f"   请尽快打款并在打款后标记为已支付: python scripts/coin.py pay --id {args.id}")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        return 1
    finally:
        conn.close()
    return 0


def cmd_pay(args):
    conn = get_db()
    cur = conn.execute("SELECT * FROM redeem_requests WHERE id = ? AND status = 'approved'", (args.id,))
    req = cur.fetchone()
    if not req:
        print(f"ERROR: 兑换请求 #{args.id} 不存在或未批准")
        return 1
    conn.execute("UPDATE redeem_requests SET status = 'paid', updated_at = datetime('now') WHERE id = ?", (args.id,))
    conn.execute("UPDATE transactions SET status = 'completed' WHERE reason = ?", (f"兑换请求 #{args.id}",))
    conn.commit()
    conn.close()
    print(f"✅ 兑换 #{args.id} 已标记为已支付")
    return 0


def cmd_reject(args):
    conn = get_db()
    cur = conn.execute("SELECT * FROM redeem_requests WHERE id = ? AND status = 'pending'", (args.id,))
    req = cur.fetchone()
    if not req:
        print(f"ERROR: 兑换请求 #{args.id} 不存在或已处理")
        return 1
    conn.execute("UPDATE redeem_requests SET status = 'rejected', updated_at = datetime('now') WHERE id = ?", (args.id,))
    conn.commit()
    conn.close()
    print(f"✅ 兑换 #{args.id} 已拒绝")
    return 0


def cmd_ledger(args):
    conn = get_db()
    cur = conn.execute("SELECT username, balance FROM accounts WHERE balance > 0 ORDER BY balance DESC")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("暂无数据")
        return 0
    print(f"{'排名':>4} | {'用户名':<20} | {'积分币':>8} | {'现金价值':>8}")
    print("-" * 50)
    for i, row in enumerate(rows, 1):
        cash = row["balance"] * RATE
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "")
        print(f"{medal}{i:>3} | {row['username']:<20} | {row['balance']:>8} | ${cash:<6.2f}")
    return 0


def cmd_audit(args):
    conn = get_db()
    cur = conn.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("暂无交易记录")
        return 0
    for row in rows:
        print(f"#{row['id']:>4} {row['tx_type']:<8} {row['from_user'] or '':<15} → {row['to_user'] or '':<15} {row['amount']:>8} [{row['status']:<9}] {row['created_at'][:19]}")
        if args.verbose:
            print(f"      hash: {row['hash'][:20]}...  prev: {row['prev_hash'][:20]}...")
    return 0


def cmd_history(args):
    conn = get_db()
    cur = conn.execute("SELECT * FROM redeem_requests ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("暂无兑换记录")
        return 0
    for row in rows:
        print(f"#{row['id']:>4} {row['username']:<20} {row['amount']:>8}积分币 = ${row['coin_value']:<6.2f} [{row['status']:<8}] {row['address'][:30]:<30} {row['created_at'][:19]}")
    return 0


def main():
    init_db()

    parser = argparse.ArgumentParser(description="积分币系统 — Coin System")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("balance", help="查询余额")
    p.add_argument("user")

    p = sub.add_parser("transfer", help="转账")
    p.add_argument("--from", dest="from_user", required=True)
    p.add_argument("--to", dest="to_user", required=True)
    p.add_argument("--amount", type=int, required=True)
    p.add_argument("--reason", default="")

    p = sub.add_parser("redeem", help="发起兑换")
    p.add_argument("--user", required=True)
    p.add_argument("--amount", type=int, required=True)
    p.add_argument("--address", required=True, help="PayPal 邮箱或 USDT 地址")

    p = sub.add_parser("approve", help="批准兑换")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("pay", help="标记已打款")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("reject", help="拒绝兑换")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("ledger", help="查看排行榜")
    p = sub.add_parser("audit", help="审计日志")
    p.add_argument("--verbose", action="store_true")
    p = sub.add_parser("history", help="兑换历史")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "balance": cmd_balance,
        "transfer": cmd_transfer,
        "redeem": cmd_redeem,
        "approve": cmd_approve,
        "pay": cmd_pay,
        "reject": cmd_reject,
        "ledger": cmd_ledger,
        "audit": cmd_audit,
        "history": cmd_history,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
