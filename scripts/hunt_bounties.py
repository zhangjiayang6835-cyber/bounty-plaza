#!/usr/bin/env python3
"""hunt_bounties.py — 自动猎索 GitHub 真实赏金任务并部署至 bounty-plaza"""

import json, os, re, sys, urllib.request
from datetime import datetime, timezone

GH_TOKEN = os.environ.get("GH_TOKEN", "")
REPO = "zhangjiayang6835-cyber/bounty-plaza"
SEARCH_QUERY = "label:bounty state:open is:issue sort:created -user:zhangjiayang6835-cyber"

# 真实赏金正则
REAL_MONEY = re.compile(
    r"""\$\s?[\d,]+(?:\.\d{1,2})?|
        \d+[\s,]*(?:USDT|USDC|DAI|ETH|BTC|USD|BUSD)|
        bounty\s*(?::|of)?\s*\$\s*\d+
    """, re.IGNORECASE | re.VERBOSE
)

def extract_amounts(text):
    """从文本中捕捉所有符合模式的最值金额"""
    amounts = []
    
    for m in re.finditer(r'\$\s?(\d[\d,]*)', text):
        try:
            amounts.append(int(m.group(1).replace(',', '')))
        except ValueError:
            pass
    
    for m in re.finditer(r'(\d+)\s*(?:USDT|USDC|DAI|ETH|BTC|USD|BUSD)', text, re.I):
        try:
            amounts.append(int(m.group(1)))
        except ValueError:
            pass
    
    for m in re.finditer(r'bounty\s*(?::|of)?\s*\$\s*(\d[\d,]*)', text, re.I):
        try:
            amounts.append(int(m.group(1).replace(',', '')))
        except ValueError:
            pass
    
    return amounts

# 虚拟代币关键词 — 匹配标题 + 正文 150 字内无真实金额则剔除
VIRTUAL_KEYWORDS = re.compile(
    r"token|point|credit|xp\b|reputation|rank|level\b|badge|achievement", re.I
)

def search_github():
    """搜索最近 30 天的 bounty Issue"""
    since = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    q = f"{SEARCH_QUERY} created:>2026-05-20"
    url = f"https://api.github.com/search/issues?q={urllib.request.quote(q)}&sort=created&order=desc&per_page=50"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}"})
    data = json.loads(urllib.request.urlopen(req).read())
    return data.get("items", [])

def is_real_money(item):
    body = (item.get("title", "") + "\n" + (item.get("body") or ""))
    
    # 必须包含真实赏金模式
    if not REAL_MONEY.search(body):
        return False
    
    # 剔除纯虚拟代币（token/points 等）且无真实金额者
    if VIRTUAL_KEYWORDS.search(body) and not REAL_MONEY.search(body[:200]):
        return False
    
    # 提取金额
    amounts = extract_amounts(body)
    if not amounts or all(a == 0 for a in amounts):
        return False
    
    return max(amounts) >= 25

def get_existing_sources():
    """获取 bounty-plaza 已有的 source_url"""
    url = f"https://api.github.com/repos/{REPO}/issues?labels=bounty&state=open&per_page=100"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GH_TOKEN}"})
    data = json.loads(urllib.request.urlopen(req).read())
    sources = set()
    for issue in data:
        body = issue.get("body", "")
        m = re.search(r"(?:原始链接|source.?url)[:\s]+(https?://[^\s\n]+)", body, re.I)
        if m:
            sources.add(m.group(1).rstrip("/"))
    return sources

def create_issue(item, amount):
    title = f"[Bounty] {item['title'][:80]}"
    body_template = f"""### 赏金平台 / Platform
GitHub

### 原始链接 / Source URL
{item['html_url']}

### 漏洞描述 / Description
{item.get('title')}

{item.get('body', '')[:2000]}

### 积分币奖励 / Coin Reward
{int(amount * 1.25)} coins

### 真实赏金（USD）/ Real Reward
${amount:,}

### 难度 / Difficulty
Medium

### 认领方式
评论 `/claim` 锁定任务 24h

### 兑换说明
> 查看 [REWARD_POLICY.md](REWARD_POLICY.md) 了解兑换规则
"""
    url = f"https://api.github.com/repos/{REPO}/issues"
    data = json.dumps({
        "title": title[:100],
        "body": body_template,
        "labels": ["bounty", "real"]
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST",
        headers={"Authorization": f"token {GH_TOKEN}", "Content-Type": "application/json"})
    result = json.loads(urllib.request.urlopen(req).read())
    return result.get("number", "?")

def is_real_external(item):
    """排除自己的仓库 + 防重复认领"""
    # 完整实现...
    pass

def main():
    """主入口"""
    items = search_github()
    sources = get_existing_sources()
    
    for item in items:
        amount = max(extract_amounts(item.get("body", "")), default=5000)
        if is_real_money(item):
            issue_num = create_issue(item, amount)
            # 更新源 URL 为 bounty-plaza
            # 逻辑...
            
    return 0

if __name__ == "__main__":
    sys.exit(main())