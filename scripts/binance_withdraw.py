#!/usr/bin/env python3
"""binance_withdraw.py — 调币安 API 提现 USDT（BSC BEP-20）"""

import hmac
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from safe_erc20 import SafeERC20Error, verify_transfer_success

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

    query = urllib.parse.urlencode(sorted(params.items()))
    signature = hmac.new(SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    url = "https://api.binance.com/sapi/v1/capital/withdraw/apply"
    headers = {"X-MBX-APIKEY": API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    body = "&".join(f"{k}={v}" for k, v in params.items())

    req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:200]
        return {"ok": False, "error": err}

    # 检查 transfer 返回值：成功的提现必须携带 id（SafeERC20 式校验）。
    transfer_id = result.get("id")
    try:
        verify_transfer_success(bool(transfer_id), context="USDT withdraw")
    except SafeERC20Error as exc:
        return {"ok": False, "error": str(exc), "payload": str(result)[:200]}

    return {"ok": True, "withdraw_id": transfer_id}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python binance_withdraw.py <address> <amount>")
        sys.exit(1)
    result = withdraw(sys.argv[1], float(sys.argv[2]))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)
