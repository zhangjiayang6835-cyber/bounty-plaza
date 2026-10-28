import os
import dotenv

# 修复文件路径
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DB_PATH = os.path.join(REPO_ROOT, "data", "coins.db")

# 修复 Binance API Key
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")

# 修复 GitHub 配置
GH_REPO = "zhangjiayang6835-cyber/bounty-plaza"

# ⚠️ 警告：Binance API Key 权限隔离
# 在币安创建 API Key 时：
# - 只启用「提现」权限（WITHDRAW）
# - 不要启用「交易」权限
# - IP 白名单锁你的本机 IP
# - 设置每日提现限额
# - 永远不要把这个 Key 提交到 GitHub

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_pending_redemptions():
    """查询所有已批准但未打款的兑换请求"""
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM redeem_requests WHERE status = 'approved
