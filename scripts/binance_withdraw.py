#!/usr/bin/env python3
"""binance_withdraw.py — 调币安 API 提现 USDT（BSC BEP-20）"""

import hmac
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from decimal import Decimal, InvalidOperation, ROUND_DOWN

API_KEY = os.environ.get("BINANCE_API_KEY", "")
SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")


def _format_amount(amount) -> str:
    try:
        d = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("invalid amount")

    if not d.is_finite() or d <= 0:
        raise ValueError("invalid amount")

    try:
        d = d.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
    except InvalidOperation:
        raise ValueError("invalid amount")

    if d <= 0:
        raise ValueError("invalid amount")

    return format(d, "f")


def withdraw(address: str, amount: float, coin: str = "USDT", network: str = "BSC") -> dict:
    if not API_KEY or not SECRET_KEY:
        return {"ok": False, "error": "BINANCE_API_KEY 或 BINANCE_SECRET_KEY 未设置"}
    
    if not isinstance(address, str) or not address.strip():
        return {"ok": False, "error": "invalid address"}

    try:
        formatted_amount = _format_amount(amount)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    timestamp = int(time.time() * 1000)
    params = {
        "coin": coin,
        "network": network,
        "address": address,
        "amount": formatted_amount,
        "timestamp": timestamp,
        "recvWindow": 5000,
    }

    query = urllib.parse.urlencode(params)
    signature = hmac.new(SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
    body = f"{query}&signature={signature}"

    url = "https://api.binance.com/sapi/v1/capital/withdraw/apply"
    headers = {"X-MBX-APIKEY": API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    
    req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            if "id" not in result:
                return {"ok": False, "error": f"unexpected response: {result}"}
            return {"ok": True, "withdraw_id": result["id"]}
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:200]
        try:
            error_response = json.loads(err)
            return {"ok": False, "error": error_response.get("msg", err)}
        except json.JSONDecodeError:
            return {"ok": False, "error": err}
    except (urllib.error.URLError, TimeoutError) as e:
        return {"ok": False, "error": f"network error: {e}"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid response"}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python binance_withdraw.py <address> <amount>")
        sys.exit(1)
    result = withdraw(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)