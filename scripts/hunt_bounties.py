#!/usr/bin/env python3
"""Automated crawler for open GitHub bounties.

Searches GitHub for external bounty issues, verifies monetary rewards,
and mirrors validated opportunities to the bounty-plaza issue tracker.
"""

import http.client
import json
import os
import re
import sys
from datetime import datetime
from urllib.parse import quote, urlparse


GH_TOKEN = os.environ.get("GH_TOKEN", "")
REPO = "zhangjiayang6835-cyber/bounty-plaza"
SEARCH_QUERY = "label:bounty state:open is:issue sort:created -user:zhangjiayang6835-cyber"

REAL_MONEY = re.compile(
    r"\$\s?[\d,]+(?:\.\d{1,2})?|"
    r"\d+(?:\.\d+)?[\s,]*(?:USDT|USDC|DAI|ETH|BTC|USD|BUSD)|"
    r"bounty\s*(?::|of)?\s*\$\s*\d+",
    re.I,
)

VIRTUAL_KEYWORDS = re.compile(
    r"token|point|credit|xp\b|reputation|rank|level\b|badge|achievement",
    re.I,
)


def extract_amounts(text: str) -> list[float]:
    """Parse numeric currency rewards from issue descriptions.

    Args:
        text: Raw text content from issue title and body.

    Returns:
        List of identified reward values as floats.
    """
    amounts: list[float] = []
    for match in re.finditer(r"\$\s?(\d[\d,]*(?:\.\d+)?)", text):
        try:
            amounts.append(float(match.group(1).replace(",", "")))
        except ValueError:
            pass
    for match in re.finditer(
        r"(\d+(?:\.\d+)?)\s*(?:USDT|USDC|DAI|ETH|BTC|USD|BUSD)", text, re.I
    ):
        try:
            amounts.append(float(match.group(1)))
        except ValueError:
            pass
    for match in re.finditer(
        r"bounty\s*(?::|of)?\s*\$\s*(\d[\d,]*(?:\.\d+)?)", text, re.I
    ):
        try:
            amounts.append(float(match.group(1).replace(",", "")))
        except ValueError:
            pass
    return amounts


def github_request(
    method: str, path: str, payload: dict | None = None
) -> dict:
    """Execute authenticated HTTPS request against GitHub REST API.

    Args:
        method: HTTP verb such as GET or POST.
        path: API path suffix.
        payload: Optional dictionary payload to serialize as JSON.

    Returns:
        Parsed JSON dictionary from API response.
    """
    conn = http.client.HTTPSConnection("api.github.com", timeout=30)
    headers = {
        "User-Agent": "bounty-plaza-crawler/1.0",
        "Accept": "application/vnd.github+json",
    }
    if GH_TOKEN:
        headers["Authorization"] = f"token {GH_TOKEN}"

    body_bytes = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body_bytes = json.dumps(payload).encode("utf-8")

    try:
        conn.request(method, path, body=body_bytes, headers=headers)
        response = conn.getresponse()
        raw_body = response.read().decode("utf-8")
        if not raw_body:
            return {}
        return json.loads(raw_body)
    finally:
        conn.close()


def search_github() -> list[dict]:
    """Query GitHub Search API for open bounty issues.

    Returns:
        List of issue dictionaries matching criteria.
    """
    encoded_query = quote(f"{SEARCH_QUERY} created:>2026-05-20")
    path = f"/search/issues?q={encoded_query}&sort=created&order=desc&per_page=50"
    data = github_request("GET", path)
    return data.get("items", [])


def is_real_money(item: dict) -> bool:
    """Determine whether issue offers genuine monetary rewards.

    Args:
        item: Issue dictionary from GitHub Search API.

    Returns:
        True if item contains eligible monetary reward.
    """
    body = f"{item.get('title', '')}\n{item.get('body') or ''}"
    if not REAL_MONEY.search(body):
        return False
    if VIRTUAL_KEYWORDS.search(body) and not REAL_MONEY.search(body[:200]):
        return False
    amounts = extract_amounts(body)
    if not amounts or all(amount == 0 for amount in amounts):
        return False
    return max(amounts) >= 0.5


def get_existing_sources() -> set[str]:
    """Retrieve existing source URLs already tracked in repository issues.

    Returns:
        Set of tracked upstream repository issue URLs.
    """
    path = f"/repos/{REPO}/issues?labels=bounty&state=open&per_page=100"
    data = github_request("GET", path)
    sources: set[str] = set()
    if isinstance(data, list):
        for issue in data:
            body = issue.get("body", "")
            match = re.search(
                r"(?:原始链接|source.?url)[:\s]+(https?://[^\s\n]+)",
                body,
                re.I,
            )
            if match:
                sources.add(match.group(1).rstrip("/"))
    return sources


def clean_bounty_title(title: str) -> str:
    """Normalize issue title by removing redundant bounty prefixes.

    Args:
        title: Raw issue title string.

    Returns:
        Normalized title prefixed with single [Bounty] tag.
    """
    cleaned = re.sub(r"^(\[Bounty\]\s*)+", "", title, flags=re.I).strip()
    return f"[Bounty] {cleaned}"[:80]


def create_issue(item: dict, amount: float) -> str:
    """Publish validated bounty task as a new issue in repository.

    Args:
        item: Upstream issue payload dictionary.
        amount: Verified monetary amount in USD.

    Returns:
        Issue number string of created issue.
    """
    title = clean_bounty_title(item.get("title", ""))
    body_content = (
        "### 赏金平台 / Platform\nGitHub\n\n"
        f"### 原始链接 / Source URL\n{item['html_url']}\n\n"
        f"### 漏洞描述 / Description\n{item.get('title')}\n\n"
        f"{item.get('body', '')[:2000]}\n\n"
        f"### 积分币奖励 / Coin Reward\n{int(amount * 1.25)} coins\n\n"
        f"### 真实赏金（USD）/ Real Reward\n${amount:,.2f}\n\n"
        "### 难度 / Difficulty\nMedium\n\n"
        "### 认领方式\n评论 `/claim` 锁定任务 24h\n\n"
        "### 兑换说明\n> 查看 [REWARD_POLICY.md](REWARD_POLICY.md) 了解兑换规则\n"
    )
    endpoint = f"/repos/{REPO}/issues"
    payload = {
        "title": title[:100],
        "body": body_content,
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
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) >= 2:
        owner = path_parts[0]
        if owner in ("zhangjiayang6835-cyber", "zhangjiayang6835"):
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
        amount = max(amounts) if amounts else 0.0

        num = create_issue(item, amount)
        print(f"  [OK] #{num}: {item['title'][:50]} - ${amount}")
        created += 1
        existing.add(url)

    print(f"  共创建 {created} 个新赏金任务")
    return 0


if __name__ == "__main__":
    sys.exit(main())
