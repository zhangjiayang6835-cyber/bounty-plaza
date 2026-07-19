import os
import json
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = "zhangjiayang6835-cyber/bounty-plaza"

def create_issue(title, body, labels):
    url = f"https://api.github.com/repos/{REPO}/issues"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "title": title,
        "body": body,
        "labels": labels
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Failed to create issue: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    title = "[Bounty] Seed a distribution child bounty that attracts a new participant"
    body = """### 赏金平台 / Platform\nGitHub\n\n### 原始链接 / Source URL\nhttps://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/482\n\n### 漏洞描述 / Description\n[1 USDC autonomous bounty] Seed a distribution child bounty that attracts a new participant\n\n### 积分币奖励 / Coin Reward\n125 coins\n\n### 真实赏金（USD）/ Real Reward\n$1.00\n\n### 难度 / Difficulty\nEasy\n\n### 认领方式\n评论 `/claim` 锁定任务 24h\n\n### 兑换说明\n> 查看 [REWARD_POLICY.md](REWARD_POLICY.md) 了解兑换规则)\n"""
    labels = ["bounty", "real"]
    issue = create_issue(title, body, labels)
    if issue:
        print(f"Created issue: {issue['html_url']}")