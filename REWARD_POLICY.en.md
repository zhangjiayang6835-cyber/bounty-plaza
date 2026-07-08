🌐 [English](REWARD_POLICY.en.md) | [中文](REWARD_POLICY.zh.md)

# 💰 Token Redemption Rules

> Complete bounty tasks to earn token coins. Coins can be redeemed for cash.
> Here's exactly how much cash you'll get.

---

## Quick Reference

| Bounty Amount | Cash You Get |
|--------------|:------------:|
| $30 | **≈ $25.65** |
| $50 | **≈ $44.40** |
| $100 | **≈ $82.80** |
| $200 | **≈ $165.60** |
| $500 | **≈ $405.00** |
| $1000 | **≈ $783.00** |
| $2000 | **≈ $1,530.00** |

---

## Formula

```
Your Cash = Bounty(USD) × 1.25 × R × 0.72
```

### R Value by Bounty Tier

| Bounty Range | R (Your Share) |
|-------------|:--------------:|
| $25 - $50 | **95%** |
| $50 - $200 | **92%** |
| $200 - $500 | **90%** |
| $500 - $1000 | **87%** |
| $1000+ | **85%** |

### Quick Examples

```
$30 bounty → 30 × 1.25 × 95% × 0.72 ≈ $25.65
$100 bounty → 100 × 1.25 × 92% × 0.72 ≈ $82.80
$350 bounty → 350 × 1.25 × 90% × 0.72 ≈ $283.50
$750 bounty → 750 × 1.25 × 87% × 0.72 ≈ $587.25
$2000 bounty → 2000 × 1.25 × 85% × 0.72 ≈ $1,530.00
```

### At a Glance

| Bounty Range | You Keep **of Bounty** |
|-------------|:----------------------:|
| $25-$50 | **≈ 85.5%** |
| $50-$200 | **≈ 82.8%** |
| $200-$500 | **≈ 81.0%** |
| $500-$1000 | **≈ 78.3%** |
| $1000+ | **≈ 76.5%** |

---

## Parameters

| Parameter | Value | Description |
|-----------|:-----:|-------------|
| Listing Rate | **1 USD = 1.25 coins** | Bounty → coin conversion |
| Platform Fee | **10%** | Service fee deducted from your share |
| Redemption Rate | **1 coin = 0.72 USD** | Fixed rate for cashing out |

> The 0.72 rate is derived from (1 - 10%) ÷ 1.25 and is constant.

---

## Full Example

$100 bounty walkthrough:

```
① Task listed as 100 × 1.25 = 125 coins
② You complete the fix, score ≥ 90 → you win
③ You receive 125 × 92% = 115 coins
④ Cash out: 115 × 0.72 = $82.80 to your account
```

From claim to cash, fully transparent.

---

> Questions? Comment on the issue or contact the admin.
