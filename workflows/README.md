# Automated Weekly GitHub Activity Narrative Summary (n8n + Claude API)

Automated end-to-end workflow integrating **n8n** and **Anthropic's Claude API** (`claude-sonnet-4-20250514`) to compile, analyze, and dispatch an executive narrative summary of weekly repository momentum to Discord, Slack, or email.

Resolves **Issue #497** / **claude-builders-bounty/claude-builders-bounty#5** ($200 USD).

---

## ⚡ 5-Step Setup Guide

1. **Import Workflow into n8n**:
   - Open your n8n workspace $\rightarrow$ Click **Add Workflow** $\rightarrow$ Select **Import from File...** $\rightarrow$ Choose `workflows/github_weekly_summary_n8n.json`.
2. **Configure Environment Variables / Credentials**:
   - Set `ANTHROPIC_API_KEY` in your n8n environment credentials.
   - (Optional) Set `GITHUB_TOKEN` if monitoring private repositories or high-frequency orgs.
3. **Set Repository & Webhook Parameters**:
   - In the `Configure Workflow Parameters` node, set:
     - `REPO_OWNER`: Target GitHub account / organization (e.g. `anthropic`).
     - `REPO_NAME`: Target repository name (e.g. `claude-code`).
     - `DESTINATION_WEBHOOK_URL`: Your Discord or Slack incoming webhook URL.
     - `SUMMARY_LANGUAGE`: Set to `EN` (English) or `FR` (French).
4. **Test Run**:
   - Click **Test step** on the `Weekly Friday 5PM Cron Trigger` or trigger a manual execution to verify GitHub data fetching, Claude generation, and webhook delivery.
5. **Activate**:
   - Toggle the workflow switch to **Active**. The cron schedule (`0 17 * * 5`) will automatically execute every Friday at 5:00 PM.

---

## 🏗️ Architecture & Data Pipeline

```text
[Cron: Friday 5:00 PM]
       │
       ▼
[Configure Parameters (Repo, Language, Webhook)]
       ├───► [GitHub API: Commits (Last 7 Days)]
       ├───► [GitHub API: Closed Issues (Last 7 Days)]
       └───► [GitHub API: Merged Pull Requests (Last 7 Days)]
       │
       ▼
[Aggregate Activity & Build Prompt (n8n Code Node)]
       │
       ▼
[Claude API: claude-sonnet-4-20250514 (Messages Endpoint)]
       │
       ▼
[Dispatch Summary to Discord/Slack Webhook]
```

---

## 📊 Summary Output Format

Claude structures the weekly digest into 5 executive sections:
1. 🌟 **Executive Highlights & Theme of the Week**
2. 🚀 **Key Merged Features & Refactors**
3. 🐛 **Critical Bugs Resolved**
4. 📊 **Momentum Statistics** (`N` commits, `M` merged PRs, `K` closed issues)
5. 🎯 **Focus Areas for Next Week**
