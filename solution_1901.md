# Fix for Issue #1901: Package hygiene: sideEffects flag, export-map validation, and publint in CI

## Problem
In `package.json`, the package published dual CJS/ESM artifacts without declaring `sideEffects: false`, forcing downstream bundlers to assume the package has side effects and retain unused code. Additionally, there was no automated validation verifying that the published artifact export map and types correctly resolve for Node16 consumers.

## Solution
1. Added `"sideEffects": false` to `package.json`, backed by verification that module top levels are pure declarations.
2. Added `publint` as a devDependency with `pnpm publint` (`publint --strict`) script.
3. Integrated `pnpm publint` into `.github/workflows/ci.yml` under `typecheck-test-build` following the build step.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
