# ERC-4626 YieldVault security fix (Bounty #1304)

Fix for the critical **Reentrancy and Share Inflation in ERC-4626 Deposit
Mechanism** vulnerability reported against `contracts/YieldVault.sol`.

## Vulnerabilities

1. **Share inflation (first-depositor donation attack)**
   An attacker deposits 1 wei and mints a single share, then donates
   `10**18` assets directly to the vault contract. Every subsequent deposit is
   computed as `assets * totalSupply / totalAssets` and rounds down to **zero
   shares**, so later users suffer a total loss.

2. **Reentrancy**
   The external deposit/withdraw routines had no reentrancy protection, so an
   ERC777-style underlying asset could re-enter the vault during
   `transfer`/`transferFrom` callbacks and double-spend shares/assets.

## Fix (`contracts/YieldVault.sol`)

- **Internal virtual shares / offset decimals (OpenZeppelin ERC-4626 standard).**
  `_decimalsOffset()` adds a permanent `10**6` virtual-share buffer to
  `totalSupply` in the conversion math
  (`_convertToShares` / `_convertToAssets`), so donations can no longer force
  deposits to round down to zero shares. The offset makes the attack
  economically unprofitable instead of a guaranteed steal.
- **Reentrancy guards.** `ReentrancyGuard` (`nonReentrant`) is applied to all
  external deposit/withdraw routines: `deposit`, `mint`, `withdraw`, `redeem`.

`contracts/YieldVaultVulnerable.sol` keeps the original audited contract
(naive rounding, no guard) for regression / differential testing.

## Test suite (`test/YieldVault.t.sol`)

| Test | Result (fixed) |
|------|----------------|
| `testVulnerableVaultTotalLossOnInflationAttack` | demonstrates the bug (victim gets 0 shares) |
| `testFixedVaultResistsInflationAttack` | victim gets non-zero shares and can redeem |
| `testFixedVaultDepositRedeemRoundTrip` | 1e18 deposit -> 1e18 redeemed |
| `testFixedVaultWithdrawRoundTrip` | withdraw burns exactly `previewWithdraw` shares |
| `testFixedVaultReentrancyGuardBlocksReentrantDeposit` | reverts `ReentrancyGuard: reentrant call` |
| `testFixedVaultReentrancyGuardBlocksReentrantWithdraw` | reverts `ReentrancyGuard: reentrant call` |
| `testVulnerableVaultAllowsReentrancy` | demonstrates the bug (reentrancy succeeds) |

## Run

```bash
forge install foundry-rs/forge-std   # pull forge-std into lib/
forge build
forge test
```

> The repository also ships a dependency-free Python reference implementation
> and pytest suite (`../yieldvault_fix.py`, `../tests/`) that exercises the same
> attack scenarios and passes with `python -m pytest tests/`.