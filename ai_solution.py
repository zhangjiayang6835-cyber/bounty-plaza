```bash
#!/usr/bin/env bash

# 安装所需的Python包
pip install python-semver

# 获取所有提交
commits=$(git log --since=$(git tag --sort=taggerdate --list --merged-branches= --format='%(tag)'))
while read commit; do
  IFS=',' read -r type desc
  case "$type" in
    feat) category="Added" ;;
    fix) category="Fixed" ;;
    chore) category="Changed" ;;
    style) category="Changed" ;;
    refactor) category="Changed" ;;
    other) category="Removed" ;;
    *) category="Other" ;;
  esac
  changelog_content+="$version - $type: $desc\n"
done < <(git log --since=$(git tag --sort=taggerdate --list --merged-branches= --format='%(tag)') --format='|%H|%s' | grep -v '^\|' | awk '{print $1 "," $2}' | sort -u)

# 生成CHANGELOG.md内容
echo "## Changelog" > CHANGELOG.md
echo "" >> CHANGELOG.md
echo "### Version $(git describe --tags --abbrev=0)" >> CHANGELOG.md
echo "" >> CHANGELOG.md
echo "$changelog_content" >> CHANGELOG.md
```

```bash
# README.md
# 1. 安装依赖：pip install python-semver
# 2. 运行：./changelog.sh
# 3. 输出会生成CHANGELOG.md
```