#!/usr/bin/env python3
"""Automated GitHub bounty hunting script for bounty-plaza."""

import http.client
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime

GH_TOKEN = os.environ.get("GH_TOKEN", "")
REPO = "zhangjiayang6835-cyber/bounty-plaza"
SEARCH_QUERY = "label:bounty state:open is:issue sort:created -user:zhangjiayang6835-cyber"

REAL_MONEY = re.compile(
    r"""\$\s?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|
    (?<![\d,.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?[\s,]*(?:USDT|USDC|DAI|ETH|BTC|USD|BUSD)\b|
    bounty\s*(?::|of)?\s*\$\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?""",
    re.I | re.X,
)

VIRTUAL_KEYWORDS = re.compile(
    r"token|point|credit|xp\b|reputation|rank|level\b|badge|achievement",
    re.I,
)


def extract_amounts(text: str) -> list[int]:
    """Extract all qualified reward currency amounts from text.

    Args:
        text: Raw text string containing potential bounty figures.

    Returns:
        Deduplicated list of integer monetary amounts.
    """
    extracted = []
    for match in re.finditer(r"\$\s?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)", text):
        try:
            val = float(match.group(1).replace(",", ""))
            extracted.append(int(round(val)))
        except ValueError:
            pass
    for match in re.finditer(
        r"(?<![\d,.])((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(?:USDT|USDC|DAI|ETH|BTC|USD|BUSD)\b",
        text,
        re.I,
    ):
        try:
            val = float(match.group(1).replace(",", ""))
            extracted.append(int(round(val)))
        except ValueError:
            pass
    for match in re.finditer(
        r"bounty\s*(?::|of)?\s*\$\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)",
        text,
        re.I,
    ):
        try:
            val = float(match.group(1).replace(",", ""))
            extracted.append(int(round(val)))
        except ValueError:
            pass
    return list(dict.fromkeys(extracted))


def github_request(method: str, endpoint: str, payload_dict: dict = None) -> dict:
    """Execute authenticated API request to api.github.com.

    Args:
        method: HTTP request verb (GET, POST, etc.).
        endpoint: API path starting with slash.
        payload_dict: Optional JSON dictionary payload.

    Returns:
        Parsed JSON dictionary response.
    """
    connection = http.client.HTTPSConnection("api.github.com", timeout=30)
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "User-Agent": "bounty-plaza-hunter",
        "Accept": "application/vnd.github.v3+json",
    }
    encoded_body = None
    if payload_dict is not None:
        headers["Content-Type"] = "application/json"
        encoded_body = json.dumps(payload_dict).encode("utf-8")

    connection.request(method, endpoint, body=encoded_body, headers=headers)
    response = connection.getresponse()
    raw_payload = response.read().decode("utf-8")
    connection.close()
    if not raw_payload:
        return {}
    return json.loads(raw_payload)


def search_github() -> list:
    """Query GitHub Search API for bounty issues created recently.

    Returns:
        List of matching issue dictionaries.
    """
    query = f"{SEARCH_QUERY} created:>2026-05-20"
    endpoint = f"/search/issues?q={urllib.parse.quote(query)}&sort=created&order=desc&per_page=50"
    data = github_request("GET", endpoint)
    return data.get("items", [])


def is_real_money(item: dict) -> bool:
    """Verify if the issue describes real monetary bounty rewards.

    Args:
        item: GitHub issue object.

    Returns:
        Boolean indicating whether real currency >= $25 is present.
    """
    body = (item.get("title", "") + "\n" + (item.get("body") or ""))
    if not REAL_MONEY.search(body):
        return False
    if VIRTUAL_KEYWORDS.search(body) and not REAL_MONEY.search(body[:200]):
        return False
    amounts = extract_amounts(body)
    if not amounts or all(a == 0 for a in amounts):
        return False
    return max(amounts) >= 25


def get_existing_sources() -> set:
    """Retrieve existing source issue URLs from bounty-plaza to prevent duplication.

    Returns:
        Set of normalized URL strings already indexed.
    """
    endpoint = f"/repos/{REPO}/issues?labels=bounty&state=open&per_page=100"
    data = github_request("GET", endpoint)
    sources = set()
    for issue in data:
        body = issue.get("body", "")
        match = re.search(r"(?:原始链接|source.?url)[:\s]+(https?://[^\s\n]+)", body, re.I)
        if match:
            sources.add(match.group(1).rstrip("/"))
    return sources


def create_issue(item: dict, amount: int) -> str:
    """Create a new mirror bounty issue on bounty-plaza.

    Args:
        item: Upstream issue object.
        amount: Highest parsed monetary value.

    Returns:
        Issue number string of created item.
    """
    raw_title = item.get("title", "")
    clean_title = re.sub(r"^(?:\[bounty\]\s*)+", "", raw_title, flags=re.I).strip()
    title = f"[Bounty] {clean_title[:80]}"
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
    endpoint = f"/repos/{REPO}/issues"
    payload = {
        "title": title[:100],
        "body": body_template,
        "labels": ["bounty", "real"],
    }
    result = github_request("POST", endpoint, payload)
    return str(result.get("number", "?"))


def is_real_external(item: dict) -> bool:
    """Filter out internal organization repositories and duplicate tags.

    Args:
        item: Issue dictionary.

    Returns:
        True if item originates externally.
    """
    return is_not_own_repo(item)


def is_not_own_repo(item: dict) -> bool:
    """Verify target repository does not belong to platform owners.

    Args:
        item: Issue dictionary.

    Returns:
        True if repository owner is external.
    """
    url = item.get("html_url", "")
    for owner in ["zhangjiayang6835-cyber", "zhangjiayang6835"]:
        if f"github.com/{owner}/" in url:
            return False
    return True


def main() -> int:
    """Main execution routine for hunting GitHub bounties.

    Returns:
        Integer process exit code.
    """
    if not GH_TOKEN:
        print("ERROR: GH_TOKEN 未设置")
        return 1

    print(f"[{datetime.now().isoformat()}] 开始搜索真实赏金...")
    items = search_github()
    print(f"  搜索到 {len(items)} 条结果")

    existing = get_existing_sources()
    print(f"  已有 {len(existing)} 个 Issue")

    created = 0
    for item in items:
        url = item["html_url"].rstrip("/")
        if url in existing:
            continue
        if not is_real_external(item):
            continue
        if not is_real_money(item):
            continue

        body = item.get("body") or ""
        title = item.get("title", "")
        amounts = extract_amounts(f"{title}\n{body}")
        amount = max(amounts) if amounts else 0

        num = create_issue(item, amount)
        print(f"  [OK] #{num}: {item['title'][:50]} - ${amount}")
        created += 1
        existing.add(url)

    print(f"  共创建 {created} 个新赏金任务")
    return 0


if __name__ == "__main__":
    sys.exit(main())
