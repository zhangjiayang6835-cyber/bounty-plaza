# Fix for Issue #1908: Skip the Arc approve transaction when the existing allowance already covers the burn

## Problem
In `src/transfer.ts:burn()`, an exact-amount ERC-20 `approveUsdcOnArc` transaction was submitted unconditionally before every Arc burn, even when TokenMessengerV2 already had an allowance ≥ `amountRaw` from a previous transfer. This resulted in redundant transactions, unnecessary gas costs, and confirmation delays.

## Solution
1. Introduced `getUsdcAllowanceOnArc` using `publicClient.readContract` to inspect the current allowance.
2. In `burn()`, checked `allowance(owner, tokenMessengerV2)` prior to approving.
3. If `allowance >= amountRaw`, skipped the approve transaction entirely.
4. If `allowance < amountRaw`, submitted an exact-amount approve as before to maintain the strict security model.
5. Fails closed if reading the allowance encounters transport or RPC failures.
6. Comprehensive test coverage in `tests/transfer.test.ts` and `tests/arc.test.ts`.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
