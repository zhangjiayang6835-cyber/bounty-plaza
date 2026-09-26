Add a live status meter badge block to the repository README.

## What this adds

A self-updating "Status Meter" section inserted near the top of README.md that
renders project health as visual shields.io badges, so the README immediately
communicates build/test/coverage/version state to any visitor.

## README.md — insert directly under the H1 title

```markdown
<!-- STATUS METER:START -->
<p align="center">
  <a href="../../actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/zhangjiayang6835-cyber/bounty-plaza/ci.yml?branch=main&label=build&style=for-the-badge"></a>
  <img alt="Issues" src="https://img.shields.io/github/issues/zhangjiayang6835-cyber/bounty-plaza?style=for-the-badge&color=blue">
  <img alt="PRs" src="https://img.shields.io/github/issues-pr/zhangjiayang6835-cyber/bounty-plaza?style=for-the-badge&color=green">
  <img alt="Last commit" src="https://img.shields.io/github/last-commit/zhangjiayang6835-cyber/bounty-plaza?style=for-the-badge&color=orange">
  <img alt="License" src="https://img.shields.io/github/license/zhangjiayang6835-cyber/bounty-plaza?style=for-the-badge">
</p>

### 📊 Status Meter

| Metric | Status |
| --- | --- |
| Build | ![build](https://img.shields.io/github/actions/workflow/status/zhangjiayang6835-cyber/bounty-plaza/ci.yml?branch=main) |
| Open issues | ![issues](https://img.shields.io/github/issues/zhangjiayang6835-cyber/bounty-plaza) |
| Open PRs | ![prs](https://img.shields.io/github/issues-pr/zhangjiayang6835-cyber/bounty-plaza) |
| Last commit | ![last-commit](https://img.shields.io/github/last-commit/zhangjiayang6835-cyber/bounty-plaza) |
| Contributors | ![contributors](https://img.shields.io/github/contributors/zhangjiayang6835-cyber/bounty-plaza) |
| License | ![license](https://img.shields.io/github/license/zhangjiayang6835-cyber/bounty-plaza) |
<!-- STATUS METER:END -->
```

## Optional: keep it fresh automatically

`.github/workflows/status-meter.yml`:

```yaml
name: Status Meter Refresh
on:
  schedule: [{ cron: "0 6 * * *" }]
  workflow_dispatch:
permissions:
  contents: write
jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Touch README to re-render badges
        run: |
          date -u +"<!-- status-meter refreshed: %Y-%m-%dT%H:%M:%SZ -->" > .status-meter-stamp
          if grep -q "status-meter refreshed" README.md; then
            sed -i "s|<!-- status-meter refreshed:.*-->|$(cat .status-meter-stamp)|" README.md
          else
            printf '\n%s\n' "$(cat .status-meter-stamp)" >> README.md
          fi
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: refresh status meter badges"
```

## Why this satisfies the bounty

- Adds a **status meter** to the README as requested.
- Uses shields.io dynamic endpoints — no tokens, no secrets, no maintenance burden.
- Delimited by `STATUS METER:START/END` markers so future automation can update it safely.
- Degrades gracefully: if a workflow file is absent, the build badge simply shows "no status".
