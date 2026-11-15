# Usage Examples

This guide provides practical examples for interacting with the Bounty Plaza ecosystem.

## 1. For Developers (Hunters)

### Running Tests Locally
Before submitting a PR, run the scoring script locally to check your grade:
```bash
python scripts/score.py --pr_path ./path_to_your_code --test_path ./tests
```

### Checking the Leaderboard
You can view your current rank and accumulated coins via the web interface:
1. Start the web server: `python web/app.py`
2. Navigate to `http://localhost:5000`

---

## 2. For Maintainers (Administrators)

### Hunting for New Bounties
To manually trigger the bounty hunter script to find new tasks from GitHub:
```bash
python scripts/hunt_bounties.py --keyword "bounty" --min_reward 50
```

### Processing Payouts
The system usually automates this via GitHub Actions, but it can be run manually:
```bash
# Process all pending approved redemptions
python scripts/auto_payout.py --mode production
```

### Managing User Coins
To manually adjust or check a user's balance in the database:
```bash
python scripts/coin.py --user "github_username" --action "add" --amount 125
```

---

## 3. Automation Flow Example

1. **Detection**: `hunt_bounties.py` finds a $100 issue.
2. **Creation**: A new issue is created in Bounty Plaza with 125 Coins as the reward.
3. **Claim**: User A comments `/claim`.
4. **Submission**: User A submits a PR.
5. **Evaluation**: `scripts/score.py` runs. If score is 95, the PR is marked as "Qualified".
6. **Merge**: Maintainer merges the PR.
7. **Reward**: `scripts/award.py` updates the user's balance in `coins.db`.
8. **Redeem**: User A opens a "Redeem Request" issue.
9. **Payout**: `scripts/binance_withdraw.py` sends the USD equivalent to the user.
