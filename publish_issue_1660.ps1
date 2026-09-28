# Automated Pull Request Publisher for Bounty Plaza Issue #1660
# Target: zhangjiayang6835-cyber/bounty-plaza
# Branch: fix/issue-1660-network-fee-ledger
# Reward: $400 USD / £312 GBP (500 coins)

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  AEA-01 Automated Bounty PR Publisher: Bounty Plaza Issue #1660" -ForegroundColor Yellow
Write-Host "  Reward: $400 USD / £312 GBP | Claim: /claim #1660" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan

$upstreamRepo = "zhangjiayang6835-cyber/bounty-plaza"
$branch = "fix/issue-1660-network-fee-ledger"
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

# 2. Push branch to fork
Write-Host "[2/4] Pushing branch '$branch' to fork..." -ForegroundColor Cyan
git push -u fork $branch
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Branch '$branch' pushed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Push failed. Please verify GitHub authentication." -ForegroundColor Red
    exit 1
}

# 3. Create Pull Request via GitHub API
Write-Host "[3/4] Creating Pull Request on $upstreamRepo via GitHub API..." -ForegroundColor Cyan
$prDoc = Join-Path (Get-Location) "packages\fee-lamports-ledger\BOUNTY_1660_PR_SUBMISSION.md"
$bodyContent = Get-Content $prDoc -Raw

$inputCreds = "protocol=https`nhost=github.com`n"
$tokenOutput = $inputCreds | git credential fill
$token = ($tokenOutput | Select-String "password=").Line.Replace("password=", "").Trim()

$headers = @{
    "User-Agent" = "AEA-01-Bounty-Swarm"
    "Authorization" = "Bearer $token"
    "Accept" = "application/vnd.github.v3+json"
}

$payload = @{
    title = "feat(ledger): record factual network fee (fee_lamports) alongside capped fee_micro for issue #1660"
    head = "${forkUser}:${branch}"
    base = "main"
    body = $bodyContent
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "https://api.github.com/repos/$upstreamRepo/pulls" -Method Post -Headers $headers -Body $payload -ContentType "application/json"
Write-Host "🚀 Pull Request Created: $($response.html_url)" -ForegroundColor Green

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Done! PR URL: $($response.html_url)" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
