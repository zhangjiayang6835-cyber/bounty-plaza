```json
// package.json
{
  "name": "parabola",
  "version": "1.0.0",
  "scripts": {
    "lint": "pnpm lint",
    "lint:fix": "pnpm lint:fix"
  },
  "devDependencies": {
    "eslint": "^8.0.0",
    "typescript-eslint": "^5.0.0"
  }
}

// eslint.config.mjs
import { ESLint } from 'https://esm.sh/eslint/linter.mjs';

export default ESLint({
  extends: ['eslint:recommended', 'plugin:@typescript-eslint/eslint-recommended'],
  plugins: ['@typescript-eslint'],
  rules: {
    '@typescript-eslint/no-floating-promises': 'error',
    '@typescript-eslint/no-misused-promises': 'error'
  }
});

// .github/workflows/ci.yml
jobs:
  typecheck-test-build:
    runs-on: ubuntu
    steps:
      - uses: actions/checkout@v2
      - uses: actions/runner@v1
      - name: Lint
        run: pnpm lint
      - name: Type check
        run: pnpm typecheck
      - name: Tests
        run: pnpm test
      - name: Build
        run: pnpm build
      - name: Commit lint
        run: pnpm commitlint
      - name: PR title lint
        run: pnpm pr-title
```