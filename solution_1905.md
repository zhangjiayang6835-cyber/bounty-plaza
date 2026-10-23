# Fix for Issue #1905: Add ESLint with typescript-eslint and wire it into CI

## Problem
CI (`.github/workflows/ci.yml`) previously ran typecheck, tests, and build, but lacked static analysis and code hygiene enforcement. High-risk bug classes in an asynchronous bridge SDK (such as unhandled/floating promises in polling loops, misused promises in callbacks, and unsafe unchecked types) had no automated linting. In addition, contributors had no local `pnpm lint` script.

## Solution
1. **ESLint 9 Flat Config (`eslint.config.mjs`)**:
   - Configured `@typescript-eslint/parser` and `@typescript-eslint/eslint-plugin`.
   - Enabled recommended TypeScript rules along with high-priority async rules:
     - `@typescript-eslint/no-floating-promises: 'error'`
     - `@typescript-eslint/no-misused-promises: 'error'`
     - Scoped parser project to `./tsconfig.json`.
   - Excluded `dist/**`, `node_modules/**`, `demos/**`, `examples/**`, `scripts/**`, and build outputs.
   - For `tests/**/*.ts`, relaxed `@typescript-eslint/no-explicit-any` to allow testing mock objects.

2. **Package Scripts & Dependencies (`package.json`)**:
   - Added `"lint": "eslint ."` and `"lint:fix": "eslint . --fix"`.
   - Added devDependencies: `eslint`, `@typescript-eslint/eslint-plugin`, and `@typescript-eslint/parser`.

3. **CI Pipeline Integration (`.github/workflows/ci.yml`)**:
   - Integrated `- run: pnpm lint` into the `typecheck-test-build` workflow between typecheck and test steps to ensure any lint violations immediately fail CI.

4. **Hermetic Test Suite (`tests/lint-config.test.ts`)**:
   - Validated that `eslint.config.mjs` contains the required floating-promise and misused-promise rules set to `'error'`.
   - Validated script definitions in `package.json` and CI step in `.github/workflows/ci.yml`.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
