---
name: generate-changelog
description: Generate a structured CHANGELOG.md from git history categorized into Added, Fixed, Changed, and Removed
---

# Generate Structured Changelog Skill

Run this skill to inspect git commit logs since the latest tag and generate or prepend a formatted Keep-a-Changelog Markdown block to `CHANGELOG.md`.

## Execution Steps

1. Run the generation script:
   ```bash
   bash changelog.sh
   ```
   Or dry-run to print output without modifying `CHANGELOG.md`:
   ```bash
   python3 tools/generate_changelog.py --dry-run
   ```

2. Review the categorized sections (`Added`, `Fixed`, `Changed`, `Removed`) and commit the updated `CHANGELOG.md`.
