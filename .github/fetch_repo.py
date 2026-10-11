import json, subprocess, sys

# Fetch repo structure
result = subprocess.run(['git', 'clone', 'https://api.github.com/repos/zhangjiayang6835-cyber/bounty-plaza', '/tmp/repo'], capture_output=True, text=True)
if result.returncode != 0:
    result = subprocess.run(['git', 'clone', 'https://github.com/zhangjiayang6835-cyber/bounty-plaza', '/tmp/repo'], capture_output=True, text=True)
print("Clone result:", result.returncode)
print(result.stdout, result.stderr)
