# Fix for Issue #1904: Expose retry/backoff knobs for Stellar allowance wait and RPC-lag

## Problem
In `src/chains/stellar.ts`, `waitForAllowance` and `retryOnTransientRpcLag` relied on hard-coded compile-time attempt and delay constants (6 attempts x 1500ms, and 3 attempts x 2000ms), giving callers no control to tune recovery for slower RPC providers or latency-critical applications.

## Solution
1. Defined and exported `StellarRetryOptions { attempts?: number; delayMs?: number }`.
2. Added `stellarRetry?: StellarRetryOptions` to `StellarDestinationOptions` and `TransferOptionsBase`.
3. Validated that custom retry attempts and delays are positive integers.
4. Preserved default values when omitted (existing tests green).
5. Added unit tests with mocked timers verifying custom attempt counts and delays in both loops.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
