# 兑换系统 Web 服务

## 启动

```bash
cd web
pip install -r requirements.txt
python app.py
```

浏览器打开 http://localhost:8080/docs 查看 Swagger UI。

## 接口

| 接口 | 说明 |
|------|------|
| `GET /balance/{username}` | 查询余额和折合现金 |
| `GET /solver/margin/{bounty_id}` | 查询 solver 现金利润及保证金（直接支持 / 费率分析） |
| `POST /redeem` | 自助兑换（自动审批） |
| `GET /redeem/{id}` | 查询兑换状态 |
| `GET /history/{username}` | 兑换历史 |
| `GET /ledger` | 排行榜 |
