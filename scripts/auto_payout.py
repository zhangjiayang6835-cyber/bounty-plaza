#!/usr/bin/env python3
"""
auto_payout.py — 本地自动打款守护脚本

每 N 分钟检查一次 SQLite 账本，发现有已批准（approved）的兑换请求，自动调币安 API 打款 USDT（BEP-20），并提交 /paid 到 GitHub Issue。

用法:
    # 一次性运行
    python scripts/auto_payout.py --once

    # 持续运行（每5分钟检查一次）
    python scripts/auto_payout.py --daemon --interval 300

    # 查看待处理列表
    python scripts/auto_payout.py --list-pending
"""

import argparse
import json
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
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "") or
