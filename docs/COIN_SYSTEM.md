# bounty-plaza 积分币系统

## 账本文件说明

积分币系统使用 SQLite 数据库存储，位置在 `data/coins.db`。

## 命令行工具

```bash
# 查看用户余额
python scripts/coin.py balance <username>

# 转账（管理员用）
python scripts/coin.py transfer --from admin --to <user> --amount 1000 --reason "Bounty #42 最优提交"

# 发起兑换申请
python scripts/coin.py redeem --user <username> --amount 5000 --address "PayPal: user@example.com"

# 审核兑换（管理员用）
python scripts/coin.py approve --id <redeem_id>

# 查看账本
python scripts/coin.py ledger

# 查看所有兑换记录
python scripts/coin.py history

# 查看审计日志
python scripts/coin.py audit
```

## 兑换规则

- 汇率：**100 积分币 = $0.01**
- 最低兑换：100 积分（=$1.00）
- 兑换后 7 个工作日内打款
- 每笔交易永久记录，可审计
