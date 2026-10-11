#!/bin/bash
cd /tmp/repo 2>/dev/null || { mkdir -p /tmp/repo && cd /tmp/repo && git clone https://github.com/zhangjiayang6835-cyber/bounty-plaza . 2>/dev/null; }
echo "=== FILES ==="
find . -type f 2>/dev/null | head -100
echo "=== README ==="
cat README.md 2>/dev/null | head -80
echo "=== PACKAGE.JSON ==="
cat package.json 2>/dev/null
echo "=== DOCS ==="
find . -name "*.md" -type f 2>/dev/null | head -20
