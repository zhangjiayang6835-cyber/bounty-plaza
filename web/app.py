#!/usr/bin/env python3
"""
bounty-plaza 自助兑换系统 Web 服务

贡献者可通过 HTTP 接口自助查询余额、发起兑换、查看历史。

启动:
    cd web && pip install -r requirements.txt && python app.py

浏览器打开 http://localhost:8080/docs 查看 API 文档
"""

import sys
import os

# 确保能找到 coin.py（上一级 scripts/ 目录）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import coin  # 直接导入 coin.py 的模块

app = FastAPI(
    title="Bounty Plaza - 自助兑换系统",
    description="查询余额、发起兑换、查看排行榜",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 数据模型 ──

class RedeemRequest(BaseModel):
    username: str
    amount: int
    address: str


# ── 接口 ──

@app.get("/balance/{username}")
def get_balance(username: str):
    """查询余额和折合现金"""
    conn = coin.get_db()
    balance = coin.get_balance(conn, username)
    conn.close()
    cash = balance * coin.RATE
    return {
        "username": username,
        "balance_coins": balance,
        "cash_usd": round(cash, 2),
        "rate": coin.RATE,
    }


@app.post("/redeem")
def create_redeem(req: RedeemRequest):
    """自助兑换：自动校验并批准"""
    if req.amount < coin.MIN_REDEEM:
        raise HTTPException(status_code=400, detail=f"最低兑换 {coin.MIN_REDEEM} 积分币")

    conn = coin.get_db()
    balance = coin.get_balance(conn, req.username)
    if balance < req.amount:
        conn.close()
        raise HTTPException(status_code=400, detail=f"余额不足（{balance} < {req.amount}）")

    # 直接走自助模式（自动批准）
    cash_value = req.amount * coin.RATE
    coin.ensure_account(conn, req.username)
    cur = conn.execute(
        "INSERT INTO redeem_requests (username, amount, coin_value, address, status) VALUES (?,?,?,?,'pending')",
        (req.username, req.amount, cash_value, req.address)
    )
    req_id = cur.lastrowid

    # 自动批准 & 扣余额
    prev_hash = coin.get_last_hash(conn)
    tx_data = {
        "tx_type": "redeem", "from_user": req.username, "to_user": None,
        "amount": req.amount, "reason": f"自助兑换 #{req_id}", "prev_hash": prev_hash,
    }
    tx_data["hash"] = coin.compute_hash(tx_data)
    conn.execute(
        "INSERT INTO transactions (tx_type, from_user, amount, reason, prev_hash, hash, status) VALUES (?,?,?,?,?,?,'approved')",
        ("redeem", req.username, req.amount, f"自助兑换 #{req_id}", tx_data["prev_hash"], tx_data["hash"])
    )
    conn.execute("UPDATE accounts SET balance = balance - ? WHERE username = ?", (req.amount, req.username))
    conn.execute("UPDATE redeem_requests SET status = 'approved', updated_at = datetime('now') WHERE id = ?", (req_id,))
    conn.commit()
    conn.close()

    return {
        "redeem_id": req_id,
        "username": req.username,
        "amount_coins": req.amount,
        "cash_usd": round(cash_value, 2),
        "address": req.address,
        "status": "approved",
        "message": f"兑换 #{req_id} 已自动批准，等待管理员打款",
    }


@app.get("/redeem/{redeem_id}")
def get_redeem_status(redeem_id: int):
    """查询兑换状态"""
    conn = coin.get_db()
    cur = conn.execute("SELECT * FROM redeem_requests WHERE id = ?", (redeem_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="兑换请求不存在")

    return {
        "id": row["id"],
        "username": row["username"],
        "amount_coins": row["amount"],
        "cash_usd": round(row["coin_value"], 2),
        "address": row["address"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


@app.get("/history/{username}")
def get_history(username: str):
    """查询兑换历史"""
    conn = coin.get_db()
    cur = conn.execute(
        "SELECT * FROM redeem_requests WHERE username = ? ORDER BY id DESC LIMIT 20",
        (username,)
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "amount_coins": r["amount"],
            "cash_usd": round(r["coin_value"], 2),
            "address": r["address"],
            "status": r["status"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@app.get("/ledger")
def get_ledger():
    """排行榜"""
    conn = coin.get_db()
    cur = conn.execute("SELECT username, balance FROM accounts WHERE balance > 0 ORDER BY balance DESC")
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "rank": i + 1,
            "username": r["username"],
            "balance_coins": r["balance"],
            "cash_usd": round(r["balance"] * coin.RATE, 2),
        }
        for i, r in enumerate(rows)
    ]


@app.get("/config")
def get_config():
    """系统配置和汇率"""
    return {
        "rate": coin.RATE,
        "rate_label": f"1 积分 = ${coin.RATE:.2f} USD",
        "min_redeem": coin.MIN_REDEEM,
        "min_redeem_label": f"最低兑换 {coin.MIN_REDEEM} 积分币",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
