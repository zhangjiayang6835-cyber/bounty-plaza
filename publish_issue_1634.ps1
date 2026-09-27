# Automated Pull Request Publisher for Bounty Plaza Issue #1634
# Target: zhangjiayang6835-cyber/bounty-plaza
# Branch: fix/issue-1634-agent-card-discovery
# Reward: $99 USD / £77.22 GBP

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  AEA-01 Automated Bounty PR Publisher: Bounty Plaza Issue #1634" -ForegroundColor Yellow
Write-Host "  Reward: $99 USD / £77.22 GBP | Claim: /claim #1634" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan

$upstreamRepo = "zhangjiayang6835-cyber/bounty-plaza"
$branch = "fix/issue-1634-agent-card-discovery"
$forkUser = "AlexanderFWatling"
$forkUrl = "https://github.com/$forkUser/bounty-plaza.git"

# 1. Check if git remote 'fork' exists
$remotes = git remote
if ($remotes -notcontains "fork") {
    Write-Host "[1/4] Adding personal fork remote: $forkUrl" -ForegroundColor Cyan
    git remote add fork $forkUrl
} else {
    Write-Host "[1/4] Fork remote already configured." -ForegroundColor Green
}

# 2. Check if fork exists on GitHub
Write-Host "[2/4] Testing connection to personal fork..." -ForegroundColor Cyan
$testFork = git ls-remote fork 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Personal fork not found yet on GitHub!" -ForegroundColor Yellow
    Write-Host "👉 Opening browser to create fork on GitHub..." -ForegroundColor Cyan
    Start-Process "https://github.com/zhangjiayang6835-cyber/bounty-plaza/fork"
    Write-Host "Please click 'Create fork' on GitHub, then press any key to continue..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# 3. Push branch to fork
Write-Host "[3/4] Pushing branch '$branch' to fork..." -ForegroundColor Cyan
git push -u fork $branch
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Branch '$branch' pushed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Push failed. Please verify GitHub authentication." -ForegroundColor Red
    exit 1
}

# 4. Copy PR markdown to clipboard and launch PR creation page
$prDoc = Join-Path (Get-Location) "packages\agent-card-discovery\BOUNTY_1634_PR_SUBMISSION.md"
if (Test-Path $prDoc) {
    Get-Content $prDoc -Raw | Set-Clipboard
    Write-Host "[4/4] Copied full Pull Request description & /claim #1634 to clipboard!" -ForegroundColor Green
}

$prUrl = "https://github.com/zhangjiayang6835-cyber/bounty-plaza/compare/main...${forkUser}:bounty-plaza:${branch}?expand=1"
Write-Host "🚀 Opening Pull Request creation page in browser..." -ForegroundColor Cyan
Start-Process $prUrl

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Done! Simply paste into the GitHub PR body and click 'Create pull request'!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
