import urllib.request, json, os, shutil

# Clone repo
shutil.rmtree('/tmp/repo', ignore_errors=True)
os.makedirs('/tmp/repo', exist_ok=True)
os.system('cd /tmp/repo && git init && git remote add origin https://github.com/zhangjiayang6835-cyber/bounty-plaza.git && git fetch origin && git checkout FETCH_HEAD 2>/dev/null || true')

# List files
result = os.popen('find /tmp/repo -type f | head -100').read()
print("=== REPO FILES ===")
print(result)

# Try to fetch issue
try:
    req = urllib.request.urlopen('https://api.github.com/repos/zhangjiayang6835-cyber/bounty-plaza/issues')
    issues = json.loads(req.read())
    print("\n=== ISSUES ===")
    for iss in issues[:10]:
        print(f"#{iss['number']}: {iss['title']}")
except Exception as e:
    print(f"Error fetching issues: {e}")
