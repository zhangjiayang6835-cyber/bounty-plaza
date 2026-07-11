#!/usr/bin/env python3
"""seed.py — Initialize coin database with admin and seed users."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coin

conn = coin.get_db()
coin.init_db(conn)

# Ensure admin exists
coin.ensure_account(conn, "admin")
admin_bal = coin.get_balance(conn, "admin")
print(f"admin balance: {admin_bal}")

# Create seed users from HONEY_LEDGER if available
honey_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "HONEY_LEDGER.json")
if os.path.isfile(honey_path):
    import json
    with open(honey_path) as f:
        ledger = json.load(f)
    for name, data in ledger.items():
        coin.ensure_account(conn, name)
        honey = data.get("HONEY", 0)
        if honey > 0 and coin.get_balance(conn, name) < honey:
            # Transfer from admin
            transfer_id = coin.transfer(conn, "admin", name, honey, "种子导入")
            print(f"  Seeded {name}: {honey} coins (tx #{transfer_id})")

conn.close()
print("Seed complete")
