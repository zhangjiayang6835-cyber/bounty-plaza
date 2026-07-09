#!/usr/bin/env python3
"""binance_withdraw.py — 调币安 API 提现 USDT（BSC BEP-20）"""

import hmac
import hashlib
import json
import os
import sys
import time
import urllib.request

API_KEY = os.environ.get("BINANCE_API_KEY", "")
SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")


def withdraw(address: str, amount: float, coin: str = "USDT", network: str = "BSC") -> dict:
    if not API_KEY or not SECRET_KEY:
        return {"ok": False, "error": "BINANCE_API_KEY 或 BINANCE_SECRET_KEY 未设置"}

    timestamp = int(time.time() * 1000)
    params = {
        "coin": coin,
        "network": network,
        "address": address,
        "amount": str(round(amount, 6)),
        "timestamp": timestamp,
    }

    query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    signature = hmac.new(SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    url = "https://api.binance.com/sapi/v1/capital/withdraw/apply"
    headers = {"X-MBX-APIKEY": API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    body = "&".join(f"{k}={v}" for k, v in params.items())

    req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            return {"ok": True, "withdraw_id": result.get("id", "?")}
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:200]
        return {"ok": False, "error": err}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python binance_withdraw.py <address> <amount>")
        sys.exit(1)
    result = withdraw(sys.argv[1], float(sys.argv[2]))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)
