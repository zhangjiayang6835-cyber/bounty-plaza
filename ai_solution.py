```markdown
/docs/failure-modes-and-recovery.md
```

```markdown
# Failure Modes and Recovery Guide

## Transfer Lifecycle Overview

The transfer process follows a lifecycle where funds are locked, transferred, and then unlocked. The key states are:

1. **Locked**: Funds are locked during transfer.
2. **Transferring**: The transfer is in progress.
3. **Complete**: The transfer is completed and funds are unlocked.

## Error Classes and Recovery Actions

### 1. TransferError
- **Meaning**: Indicates a transfer lock has expired, and the transfer wasn't completed.
- **Action**: Call `completeMint` to unlock the funds.

### 2. AttestationNotReadyError
- **Meaning**: The attestation is not ready, but funds are safe.
- **Action**: Retry the transfer.

### 3. SubmissionTimeoutError
- **Meaning**: The transfer submission timed out, but the hash exists.
- **Action**: Check the chain and then retry.

### 4. IrisRequestError
- **Meaning**: Indicates a Circle-side issue.
- **Action**: Retry the transfer.

### 5. resolveBurn
- **Meanity**: Used to inspect a burn not produced by your system.
- **Action**: Use to verify the burn status.

## Worked Example: completeMint Recovery

```typescript
try {
  await transfer(...);
} catch (error) {
  if (error instanceof TransferError) {
    await completeMint();
  }
}
```

## Choosing pollTimeout

Set `pollTimeout` to a value that balances responsiveness and stability. Adjust as needed for your environment.

## References

- [INTEGRATION.md](INTEGRATION.md)
```