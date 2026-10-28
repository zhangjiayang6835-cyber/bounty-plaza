import os
import dotenv

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if os.path.isfile(_env_path):
    dotenv.load_dotenv(_env_path)

import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from hashlib import sha256

# ── 路径 ──
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DB_PATH = os.path.join(REPO_ROOT, "data", "coins.db")

# ── Binance API ──
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "") or ""
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "") or ""
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")

# ── GitHub 配置 ──
GH_REPO = "zhangjiayang6835-cyber/bounty-plaza"

# ⚠️ 警告：Binance API Key 权限隔离
# 在币安创建 API Key 时： 
# - 只启用「提现」权限（WITHDRAW）
# - 不要启用「交易」权限
# - IP 白名单锁你的本机 IP
# - 设置每日提现限额
# -
