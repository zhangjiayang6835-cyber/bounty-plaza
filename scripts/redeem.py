#!/usr/bin/env python3
"""
redeem.py — HONEY 兑换处理脚本

检查兑换请求，验证积分余额，更新账本。

用法:
    python scripts/redeem.py --user <username> --amount <HONEY> --payment <paypal|usdt>
    python scripts/redeem.py --ledger                    # 查看账本
    python scripts/redeem.py --balance <username>         # 查余额
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
LEDGER_PATH = os.path.join(REPO_ROOT, "HONEY_LEDGER.json")
CONFIG_PATH = os.path.join(REPO_ROOT, "BOUNTY_CONFIG.json")


def load_ledger() -> dict:
    if not os.path.isfile(LEDGER_PATH):
        return {}
    with open(LEDGER_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_ledger(ledger: dict):
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)


def load_config() -> dict:
    if not os.path.isfile(CONFIG_PATH):
        return {"rate": 0.0001, "min_redeem": 10000}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="HONEY redemption tool")
    parser.add_argument("--user", type=str, help="Username")
    parser.add_argument("--amount", type=int, help="HONEY amount to redeem")
    parser.add_argument("--payment", type=str, help="Payment method (paypal/usdt)")
    parser.add_argument("--address", type=str, help="Payment address")
    parser.add_argument("--balance", type=str, help="Check balance for user")
    parser.add_argument("--ledger", action="store_true", help="Show full ledger")
    parser.add_argument("--config", action="store_true", help="Show config")
    args = parser.parse_args()

    config = load_config()
    rate = config["rate"]
    min_redeem = config["min_redeem"]

    if args.config:
        print(json.dumps(config, indent=2))
        return 0

    if args.ledger:
        ledger = load_ledger()
        if not ledger:
            print("Empty ledger")
            return 0
        for user, data in sorted(ledger.items(), key=lambda x: -x[1].get("balance", 0)):
            print(f"{user}: {data.get('balance', 0)} HONEY (${data.get('balance', 0) * rate:.2f})")
        return 0

    if args.balance:
        ledger = load_ledger()
        user_data = ledger.get(args.balance, {})
        balance = user_data.get("balance", 0)
        print(f"{args.balance}: {balance} HONEY = ${balance * rate:.2f}")
        return 0

    if args.user and args.amount:
        ledger = load_ledger()
        user_data = ledger.get(args.user, {"balance": 0, "redeemed": 0, "history": []})
        balance = user_data.get("balance", 0)

        if args.amount < min_redeem:
            print(f"ERROR: Minimum redeem is {min_redeem} HONEY")
            return 1
        if args.amount > balance:
            print(f"ERROR: Insufficient balance. {args.user} has {balance} HONEY")
            return 1

        cash_value = args.amount * rate
        user_data["balance"] -= args.amount
        user_data["redeemed"] = user_data.get("redeemed", 0) + args.amount
        user_data["history"].append({
            "type": "redeem",
            "amount": args.amount,
            "cash": round(cash_value, 2),
            "payment": args.payment or "unknown",
            "address": args.address or "",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        ledger[args.user] = user_data
        save_ledger(ledger)

        print(f"✅ Redeemed {args.amount} HONEY for {args.user}")
        print(f"   Cash: ${cash_value:.2f}")
        print(f"   Remaining balance: {user_data['balance']} HONEY")
        print(f"   Total redeemed: {user_data['redeemed']} HONEY")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
