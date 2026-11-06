# Issue #1896 — convertPrecision export + 6↔7 decimal round-trip tests

`convertPrecision` is already exported from `src/index.ts` on main, so the remaining part of
the issue is the missing round-trip coverage. That coverage is in `tests/amount.test.ts` here,
exercised through the public helpers (`toRawAmount` / `fromRawAmount`) rather than by calling
the internal function directly.

While adding it, main turned out not to compile, so the patch also repairs that.

## The tests (the actual ask)

`describe("cross-chain decimal round trips")`:

- up-scale then down-scale must return the original raw value byte-for-byte, and the formatted
  amount must come back unchanged for values without trailing zeros
- 7→6 must truncate the seventh decimal, not round it
- sub-unit remainders truncate toward zero
- zero round-trips in both directions
- the maximum value at each chain's precision round-trips exactly
- matching decimals is a no-op

## The repairs main needed

`vitest` could not even transform the repo at these commit; 11 of 13 test files failed to
collect. Each fix below is a duplicate declaration or a refactor leftover, not a behaviour change:

- `src/errors.ts` — `AmountPrecisionError` declared twice; kept the first (its message is the
  one the tests assert) and removed the second.
- `src/chains/arc.ts` — `getUsdcAllowanceOnArc` declared twice. Kept the `ArcSigner | Hex`
  variant the caller uses, with the fail-closed `try/catch → 0n` from the other copy, since
  `arc.test.ts` asserts that behaviour. Also annotated the two chain constants as `Chain` to
  clear a TS2742.
- `src/chains/stellar.ts` — `StellarRetryOptions` declared twice (kept the documented one);
  `waitForAllowance` shadowed its own `attempts`/`delayMs` parameters; the call passed the old
  positional signature (`rpcUrl` landing in `attempts`); `retryOnTransientRpcLag` used an
  undefined `waitMs`; `resolveRetry` and its two default tables were referenced but missing.
- `src/transfer.ts` — three call sites used `emitProgress`, which does not exist (the helper is
  `safeEmit`); `AmountPrecisionError` was thrown but never imported; `TOTAL`/stage emissions were
  duplicated (`burn-confirmed`, `attestation`, `mint-confirmed` each fired twice per transfer,
  which the progress tests count); a duplicate local `assertDestinationPrecision` shadowed the
  imported utility.
- `src/types.ts` — `stellarRetryAttempts` / `stellarRetryDelayMs` declared twice.
- `src/index.ts`, `tests/progress.test.ts` — duplicate re-export and duplicate mock key.
- `tests/transfer.test.ts` — one assertion still matched the old 4-argument
  `approveUsdcOnStellar` signature; updated to the current 6-argument form.

## Verification

```
pnpm test       # 13 files, 210 tests passed
pnpm typecheck  # clean
pnpm lint       # clean, 0 warnings
```

Before: 11 of 13 files failed to collect, 32 tests ran.

`pnpm-lock.yaml` is left untouched so the diff stays reviewable.
