#!/usr/bin/env python3
"""redeem_issue.py — Parse Issue body and process redemption."""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    body = os.environ.get('ISSUE_BODY', '')
    issue_num = os.environ.get('ISSUE_NUM', '0')

    # Parse Issue body
    lines = body.split('\n')
    username = ''
    amount = ''
    address = ''

    for i, line in enumerate(lines):
        stripped = line.strip()
        if '用户名' in stripped and i + 1 < len(lines):
            username = lines[i + 1].strip()
        if '兑换数量' in stripped and i + 1 < len(lines):
            raw_amt = lines[i + 1].strip()
            amount = ''.join(c for c in raw_amt if c.isdigit())
        if '收款地址' in stripped and i + 1 < len(lines):
            address = lines[i + 1].strip()

    if not username or not amount or not address:
        result = {"ok": False, "error": f"字段解析失败: user={username} amt={amount} addr={address}"}
        write_result(result)
        return 1

    # Run coin.py redeem --auto --json
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, 'coin.py'), 'redeem',
         '--auto', '--json',
         '--user', username,
         '--amount', amount,
         '--address', address,
         '--note', f'GitHub Issue #{issue_num}'],
        capture_output=True, text=True, cwd=os.path.dirname(HERE)
    )

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        result = {"ok": False, "error": stdout[:200] or stderr[:200]}

    write_result(result)
    return 0 if result.get('ok') else 1


def write_result(data: dict):
    path = os.path.join(os.path.dirname(HERE), 'redeem_result.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    sys.exit(main())
