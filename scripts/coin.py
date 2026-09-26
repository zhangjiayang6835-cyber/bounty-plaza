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
import math
import os
import sqlite3
import sys
from datetime import datetime, timezone

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.environ.get("COIN_DB_PATH") or os.path.join(DB_DIR, "coins.db")

RATE = 0.72            # 1 积分 = 0.72 USD
MIN_REDEEM = 1          # 无最低限制（1积分即可兑换）
BOUNTY_TO_COIN_RATE = 1.25  # 1 USD = 1.25 积分标价
MIN_BOUNTY_USD = 25         # 最低赏金门槛 ($25)


def get_db(db_path: str = None):
    target = db_path or DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    conn = sqlite3.connect(target)
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


def compute_hash(row) -> str:
    if row is None:
        row = {}
    elif isinstance(row, sqlite3.Row):
        row = dict(row)
    elif not hasattr(row, "get"):
        row = {}
    prev_hash = str(row.get("prev_hash") or "")
    tx_type = str(row.get("tx_type") or "")
    from_user = str(row.get("from_user") or "")
    to_user = str(row.get("to_user") or "")
    amount = row.get("amount", 0)
    if amount is None:
        amount = 0
    reason = str(row.get("reason") or "")
    raw = f"{prev_hash}|{tx_type}|{from_user}|{to_user}|{amount}|{reason}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_last_hash(conn) -> str:
    cur = conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    return row["hash"] if row else "0" * 64


def get_balance(conn, username: str) -> int:
    if not username or not isinstance(username, str):
        return 0
    cur = conn.execute("SELECT balance FROM accounts WHERE username = ?", (username,))
    row = cur.fetchone()
    return row["balance"] if row else 0


def ensure_account(conn, username: str):
    if not username or not isinstance(username, str) or not username.strip():
        return
    cur = conn.execute("SELECT 1 FROM accounts WHERE username = ?", (username.strip(),))
    if not cur.fetchone():
        conn.execute("INSERT INTO accounts (username, balance) VALUES (?, 0)", (username.strip(),))


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
        from_user = str(getattr(args, "from_user", "") or "").strip()
        to_user = str(getattr(args, "to_user", "") or "").strip()
        amount = getattr(args, "amount", 0)

        if not from_user or not to_user:
            print("ERROR: 转账用户不能为空")
            return 1
        if from_user == to_user:
            print("ERROR: 不能给自己转账")
            return 1
        if not isinstance(amount, int) or amount <= 0:
            print("ERROR: 转账金额必须大于 0")
            return 1

        ensure_account(conn, from_user)
        ensure_account(conn, to_user)

        # 原子扣款：balance >= amount 时才扣，避免竞态双花
        cur = conn.execute(
            "UPDATE accounts SET balance = balance - ? WHERE username = ? AND balance >= ?",
            (amount, from_user, amount)
        )
        if cur.rowcount == 0:
            print(f"ERROR: {from_user} 余额不足或并发冲突")
            return 1

        prev_hash = get_last_hash(conn)
        tx_data = {
            "tx_type": "transfer", "from_user": from_user,
            "to_user": to_user, "amount": amount,
            "reason": args.reason, "prev_hash": prev_hash,
        }
        tx_data["hash"] = compute_hash(tx_data)

        conn.execute(
            "INSERT INTO transactions (tx_type, from_user, to_user, amount, reason, prev_hash, hash) VALUES (?,?,?,?,?,?,?)",
            (tx_data["tx_type"], tx_data["from_user"], tx_data["to_user"],
             tx_data["amount"], tx_data["reason"], tx_data["prev_hash"], tx_data["hash"])
        )
        conn.execute("UPDATE accounts SET balance = balance + ? WHERE username = ?", (amount, to_user))
        conn.commit()
        print(f"✅ 转账成功: {from_user} → {to_user} 共 {amount} 积分币")
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
        user = str(getattr(args, "user", "") or "").strip()
        address = str(getattr(args, "address", "") or "").strip()
        amount = getattr(args, "amount", 0)

        if not user or not address:
            print("ERROR: 用户名和收款地址不能为空")
            return 1
        if not isinstance(amount, int) or amount < 1:
            print("ERROR: 金额必须大于 0")
            return 1

        balance = get_balance(conn, user)
        if balance < amount:
            print(f"ERROR: {user} 余额不足（{balance} < {amount}）")
            return 1

        cash_value = amount * RATE
        ensure_account(conn, user)
        cur = conn.execute(
            "INSERT INTO redeem_requests (username, amount, coin_value, address, status) VALUES (?,?,?,?,'pending')",
            (user, amount, cash_value, address)
        )
        req_id = cur.lastrowid

        if getattr(args, "auto", False):
            prev_hash = get_last_hash(conn)
            tx_data = {"tx_type": "redeem", "from_user": user, "to_user": None,
                       "amount": amount, "reason": f"自助兑换 #{req_id}", "prev_hash": prev_hash}
            tx_data["hash"] = compute_hash(tx_data)
            conn.execute(
                "INSERT INTO transactions (tx_type, from_user, amount, reason, prev_hash, hash, status) VALUES (?,?,?,?,?,?,'approved')",
                ("redeem", user, amount, f"自助兑换 #{req_id}", tx_data["prev_hash"], tx_data["hash"])
            )
            cur_upd = conn.execute("UPDATE accounts SET balance = balance - ? WHERE username = ? AND balance >= ?", (amount, user, amount))
            if cur_upd.rowcount == 0:
                conn.rollback()
                print(f"ERROR: {user} 余额不足或并发冲突")
                return 1
            conn.execute("UPDATE redeem_requests SET status = 'approved', updated_at = datetime('now') WHERE id = ?", (req_id,))
            conn.commit()
            if getattr(args, "json", False):
                import json as _json
                print(_json.dumps({"ok": True, "id": req_id, "username": user, "amount": amount, "cash_value": round(cash_value, 2), "address": address, "status": "approved", "balance_remaining": balance - amount}))
            else:
                print(f"✅ 自助兑换成功: {user} 兑换 {amount} 积分币 = ${cash_value:.2f}")
                print(f"   收款地址: {address}")
                rid_label = f"兑换号: #{req_id}"; print(f"   {rid_label}，已自动批准，管理员请尽快打款")
        else:
            conn.commit()
            print(f"✅ 兑换申请已提交: {user} 兑换 {amount} 积分币 = ${cash_value:.2f}")
            print(f"   收款地址: {address}")
            print(f"   等待管理员审核（ID: {req_id}）")
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
        # 原子锁定：只有 pending 状态的才能被批准，防止重复扣款
        conn.execute(
            "UPDATE redeem_requests SET status = 'approved', updated_at = datetime('now') WHERE id = ? AND status = 'pending'",
            (args.id,)
        )
        if conn.execute("SELECT changes()").fetchone()[0] == 0:
            print(f"ERROR: 兑换请求 #{args.id} 不存在或已被处理")
            return 1

        cur = conn.execute("SELECT username, amount, coin_value FROM redeem_requests WHERE id = ?", (args.id,))
        req = cur.fetchone()
        username = req["username"]
        amount = req["amount"]

        # 原子扣款
        cur2 = conn.execute(
            "UPDATE accounts SET balance = balance - ? WHERE username = ? AND balance >= ?",
            (amount, username, amount)
        )
        if cur2.rowcount == 0:
            print(f"ERROR: {username} 余额不足（并发冲突）")
            conn.execute("UPDATE redeem_requests SET status = 'pending', updated_at = datetime('now') WHERE id = ?", (args.id,))
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
    try:
        cur = conn.execute("SELECT * FROM redeem_requests WHERE id = ? AND status = 'approved'", (args.id,))
        req = cur.fetchone()
        if not req:
            if getattr(args, 'json', False):
                import json as _json
                print(_json.dumps({"ok": False, "error": "not_found", "id": args.id}))
            else:
                print(f"ERROR: 兑换请求 #{args.id} 不存在或已处理")
            return 1

        conn.execute("UPDATE redeem_requests SET status = 'paid', updated_at = datetime('now') WHERE id = ?", (args.id,))
        cur2 = conn.execute("SELECT * FROM transactions WHERE from_user = ? AND amount = ? AND status = 'approved' ORDER BY id DESC LIMIT 1", (req["username"], req["amount"]))
        tx = cur2.fetchone()
        if tx:
            conn.execute("UPDATE transactions SET status = 'completed' WHERE id = ?", (tx["id"],))
        conn.commit()

        req_dict = dict(req)
        cash_val = req_dict.get("coin_value", req_dict["amount"] * RATE)
        if getattr(args, 'json', False):
            import json as _json
            print(_json.dumps({"ok": True, "id": args.id, "username": req_dict["username"], "amount": req_dict["amount"], "cash_value": round(cash_val, 2), "status": "paid"}))
        else:
            print(f"✅ 兑换 #{args.id} 已标记为已支付: {req_dict['username']} ${cash_val:.2f}")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        return 1
    finally:
        conn.close()
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


def get_bounty_tier_r(amount: float) -> tuple:
    """依据 REWARD_POLICY.md 与 BOUNTY_CONFIG.json 确定分成比例 R"""
    if amount <= 50:
        return 0.95, "< $50 (95%)"
    elif amount <= 200:
        return 0.92, "$50-$200 (92%)"
    elif amount <= 500:
        return 0.90, "$200-$500 (90%)"
    elif amount <= 1000:
        return 0.87, "$500-$1000 (87%)"
    else:
        return 0.85, "$1000+ (85%)"


def bounty(amount=None, user: str = None, **kwargs) -> dict:
    """
    计算赏金与积分兑换规则（依据 REWARD_POLICY.md & BOUNTY_CONFIG.json）。
    多层防御：严格防御空值、非数字、布尔值、负数、NaN/Inf 以及格式畸变。
    """
    if amount is None or isinstance(amount, bool):
        return {
            "ok": False,
            "error": "赏金金额不能为空且必须为有效数值",
            "bounty_usd": 0.0,
            "coins": 0,
            "r_ratio": 0.0,
            "contributor_coins": 0,
            "cash_value": 0.0,
            "rate": RATE,
        }

    # 处理字符串格式输入（例如 "$100", "1,000", "50.5"）
    if isinstance(amount, str):
        cleaned = amount.strip().replace("$", "").replace(",", "")
        try:
            parsed_amount = float(cleaned)
        except (ValueError, TypeError):
            return {
                "ok": False,
                "error": f"无法解析的赏金金额: {amount}",
                "bounty_usd": 0.0,
                "coins": 0,
                "r_ratio": 0.0,
                "contributor_coins": 0,
                "cash_value": 0.0,
                "rate": RATE,
            }
    elif isinstance(amount, (int, float)):
        parsed_amount = float(amount)
    else:
        return {
            "ok": False,
            "error": f"不受支持的金额类型: {type(amount).__name__}",
            "bounty_usd": 0.0,
            "coins": 0,
            "r_ratio": 0.0,
            "contributor_coins": 0,
            "cash_value": 0.0,
            "rate": RATE,
        }

    # 校验 NaN, Inf, 负数与 0
    if math.isnan(parsed_amount) or math.isinf(parsed_amount) or parsed_amount <= 0:
        return {
            "ok": False,
            "error": "赏金金额必须为有限正数",
            "bounty_usd": 0.0,
            "coins": 0,
            "r_ratio": 0.0,
            "contributor_coins": 0,
            "cash_value": 0.0,
            "rate": RATE,
        }

    # 校验低于最低限额 ($25)
    if parsed_amount < MIN_BOUNTY_USD:
        return {
            "ok": False,
            "error": f"赏金金额 ${parsed_amount:.2f} 低于平台最低标准 (${MIN_BOUNTY_USD})",
            "bounty_usd": round(parsed_amount, 2),
            "coins": 0,
            "r_ratio": 0.0,
            "contributor_coins": 0,
            "cash_value": 0.0,
            "rate": RATE,
        }

    r_ratio, tier_label = get_bounty_tier_r(parsed_amount)
    coins = int(parsed_amount * BOUNTY_TO_COIN_RATE)
    contributor_coins = round(parsed_amount * BOUNTY_TO_COIN_RATE * r_ratio, 2)
    contributor_coins_int = int(round(parsed_amount * BOUNTY_TO_COIN_RATE * r_ratio))
    cash_value = round(parsed_amount * BOUNTY_TO_COIN_RATE * r_ratio * RATE, 2)

    res = {
        "ok": True,
        "bounty_usd": round(parsed_amount, 2),
        "coins": coins,
        "r_ratio": r_ratio,
        "tier": tier_label,
        "contributor_coins": contributor_coins_int,
        "contributor_coins_float": contributor_coins,
        "cash_value": cash_value,
        "rate": RATE,
    }
    if user:
        res["user"] = str(user).strip()
    return res


def cmd_bounty(args):
    raw_amount = getattr(args, "amount", None) or getattr(args, "flag_amount", None)
    user = getattr(args, "user", None)
    result = bounty(raw_amount, user=user)

    if getattr(args, "json", False):
        import json as _json
        print(_json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 1

    if not result["ok"]:
        print(f"ERROR: {result.get('error', '赏金计算失败')}")
        return 1

    print(f"💰 赏金换算结果 (${result['bounty_usd']:.2f}):")
    print(f"   阶梯区间: {result['tier']}")
    print(f"   任务标价: {result['coins']} 积分币 (按 1 USD = {BOUNTY_TO_COIN_RATE} 积分)")
    print(f"   贡献者分成比例 (R): {int(result['r_ratio'] * 100)}%")
    print(f"   贡献者实得积分: {result['contributor_coins']} 积分币")
    print(f"   最终提现现金: ${result['cash_value']:.2f} (按 1 积分 = ${RATE} USD)")
    if result.get("user"):
        print(f"   指定贡献者: {result['user']}")
    return 0


def main():
    init_db()

    parser = argparse.ArgumentParser(description="积分币系统 — Coin System")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("balance", help="查询余额")
    p.add_argument("user")
    p.add_argument("--init", action="store_true", help="初始化 Admin 账户并注入初始积分")

    p = sub.add_parser("transfer", help="转账")
    p.add_argument("--from", dest="from_user", required=True)
    p.add_argument("--to", dest="to_user", required=True)
    p.add_argument("--amount", type=int, required=True)
    p.add_argument("--reason", default="")

    p = sub.add_parser("redeem", help="发起兑换")
    p.add_argument("--user", required=True)
    p.add_argument("--amount", type=int, required=True)
    p.add_argument("--address", required=True, help="PayPal 邮箱或 USDT 地址")
    p.add_argument("--auto", action="store_true", help="自助模式：自动批准兑换")
    p.add_argument("--json", action="store_true", help="JSON 格式输出")
    p.add_argument("--note", default="", help="备注")

    p = sub.add_parser("approve", help="批准兑换")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("pay", help="标记已打款")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--json", action="store_true", help="JSON 格式输出")
    p.add_argument("--note", default="", help="备注")

    p = sub.add_parser("reject", help="拒绝兑换")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("ledger", help="查看排行榜")
    p = sub.add_parser("audit", help="审计日志")
    p.add_argument("--verbose", action="store_true")
    p = sub.add_parser("history", help="兑换历史")

    p = sub.add_parser("bounty", help="计算或查看赏金与积分兑换规则")
    p.add_argument("amount", nargs="?", default=None, help="赏金金额 (USD)")
    p.add_argument("--amount", dest="flag_amount", default=None, help="赏金金额 (USD)")
    p.add_argument("--user", default=None, help="贡献者用户名")
    p.add_argument("--json", action="store_true", help="JSON 格式输出")

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
        "bounty": cmd_bounty,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
