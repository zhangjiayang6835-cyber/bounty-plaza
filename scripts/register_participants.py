import os
import requests

# GitHub API endpoint
url = "https://api.github.com/repos/zhangjiayang6835-cyber/bounty-plaza/issues/1/comments"

# GitHub token
token = os.environ.get("GITHUB_TOKEN")

# Parent registration comment
parent_comment = {
    "body": "/agent-bounty register 0xParentBaseWallet"
}

# Child solver registration comment
child_comment = {
    "body": "/agent-bounty register 0xChildBaseWallet"
}

# Set up headers
headers = {
    "Authorization": f"token {token}",
    "Content-Type": "application/json"
}

# Post the parent registration comment
response = requests.post(url, json=parent_comment, headers=headers)
if response.status_code == 201:
    print("Parent registered successfully")
else:
    print("Failed to register parent:", response.status_code, response.text)

# Post the child solver registration comment
response = requests.post(url, json=child_comment, headers=headers)
if response.status_code == 201:
    print("Child solver registered successfully")
else:
    print("Failed to register child solver:", response.status_code, response.text)
