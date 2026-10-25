To address the task, we need to add optional retry and delay options for the Stellar functions. Here's the step-by-step solution:

1. **Add new optional properties to `TransferOptionsBase`:**

```typescript
// src/types/transfer-options.ts
export type TransferOptionsBase = {
    kind?: string;
    stellarRetryAttempts?: number;
    stellarRetryDelayMs?: number;
};
```

2. **Update `waitForAllowance` in `src/chains/stellar.ts`:**

```typescript
// src/chains/stellar.ts
function waitForAllowance(...args: any[]) {
    const opts = this.opts as TransferOptionsBase;
    const attempts = opts.stellarRetryAttempts ?? 6;
    const delay = opts.stellarRetryDelayMs ?? 1500;
    // Replace the hardcoded values with attempts and delay
    // ... rest of the function
}
```

3. **Update `retryOnTransientRpcLag` in `src/chains/stellar.ts`:**

```typescript
// src/chains/stellar.ts
function retryOnTransientRpcLag(...args: any[]) {
    const opts = this.opts as TransferOptionsBase;
    const attempts = opts.stellarRetryAttempts ?? 3;
    const delay = opts.stellarRetryDelayMs ?? 2000;
    // Replace the hardcoded values with attempts and delay
    // ... rest of the function
}
```

4. **Document the new options in the README:**

```markdown
# Options

- `stellarRetryAttempts`: Number of retry attempts for Stellar operations. Default: 6.
- `stellarRetryDelayMs`: Delay in milliseconds between retries for Stellar operations. Default: 1500.
```

5. **Ensure the options are passed through in `burnUsdcOnStellar` and `approveUsdcOnStellar` functions:**

```typescript
// Example function call
burnUsdcOnStellar({
    // ... other options
    stellarRetryAttempts: 6,
    stellarRetryDelayMs: 1500,
});
```

These changes make the retry and delay options configurable, preserving the current behavior by default while allowing customization.