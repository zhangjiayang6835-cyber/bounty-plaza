import os
import requests

# GitHub API endpoint
url = "https://api.github.com/repos/zhangjiayang6835-cyber/bounty-plaza/issues"

# GitHub token
token = os.environ.get("GITHUB_TOKEN")

# Issue details
issue_data = {
    "title": "[Bounty] Concrete API Coding Task",
    "body": """### 赏金平台 / Platform\nGitHub\n\n### 原始链接 / Source URL\nhttps://github.com/NSPG13/agent-bounties/issues/334\n\n### 漏洞描述 / Description\nThis is a concrete API coding task. The goal is to implement a specific API endpoint.\n\n### 积分币奖励 / Coin Reward\n90 coins\n\n### 真实赏金（USD）/ Real Reward\n$0.90\n\n### 难度 / Difficulty\nMedium\n\n### 认领方式\n评论 `/claim` 锁定任务 24h\n\n### 兑换说明\n> 查看 [REWARD_POLICY.md](REWARD_POLICY.md) 了解兑换规则""",
    "labels": ["bounty", "real"]
}

# Set up headers
headers = {
    "Authorization": f"token {token}",
    "Content-Type": "application/json"
}

# Create the issue
response = requests.post(url, json=issue_data, headers=headers)

if response.status_code == 201:
    print("Issue created successfully:", response.json()["html_url"])
else:
    print("Failed to create issue:", response.status_code, response.text)
