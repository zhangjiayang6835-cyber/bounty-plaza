# Skill: generate-changelog

## Purpose
Build a structured `CHANGELOG.md` from git history: commits since the latest tag, grouped into Added / Fixed / Changed / Removed.

## Trigger
`/generate-changelog`

## Steps
1. Prefer `bash changelog.sh` at the repo root.
2. If missing: `git describe --tags --abbrev=0`, then `git log <tag>..HEAD --pretty=format:'%h %s' --no-merges`.
3. Sort into Added / Fixed / Changed / Removed.
4. Write `CHANGELOG.md`. Do not edit application source for this task.
