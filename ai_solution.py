To solve the problem, we need to make the `getAttestation` function more reliable by allowing it to retry up to 5 times when it encounters `IrisRequestError`. We'll extract the retry logic into a helper function to keep the code organized and consistent.

Here's the step-by-step solution:

1. **Extract the maximum consecutive failure limit into a constant.**
2. **Create a helper function to manage retries.**
3. **Modify `getAttestation` to use the helper function and handle errors appropriately.**

The complete code solution is as follows:

```typescript
const MAX_CONSECUTIVE_FAILURES = 5;

async function withRetry(fn: () => Promise<string>): Promise<string> {
  let consecutiveFailures = 0;
  while (consecutiveFailures < MAX_CONSECUTIVE_FAILURES) {
    try {
      return await fn();
    } catch (err) {
      if (err.code === 'IrisRequestError') {
        consecutiveFailures++;
        if (consecutiveFailures < MAX_CONSECUTIVE_FAILURES) {
          await wait(1000);
        }
      } else {
        throw err;
      }
    }
  }
  throw new AttestationNotReadyError();
}

async function getAttestation(): Promise<string> {
  const fn = async () => {
    const response = await iris.getAttestation().catch((err) => {
      if (err.code === 'IrisRequestError') {
        return Promise.resolve();
      }
      throw err;
    });
    if (!response) {
      throw new AttestationNotReadyError();
    }
    return response;
  };

  return await withRetry(fn);
}
```