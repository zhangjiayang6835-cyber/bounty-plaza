import { TransferOptionsBase } from '../types';

// ... existing imports and code ...

export async function waitForAllowance(options: TransferOptionsBase) {
  const attempts = options.stellarRetryAttempts ?? 6;
  const delay = options.stellarRetryDelayMs ?? 1500;
  
  for (let i = 0; i < attempts; i++) {
    // ... existing logic ...
    await new Promise(resolve => setTimeout(resolve, delay));
  }
}

export async function retryOnTransientRpcLag(options: TransferOptionsBase) {
  const attempts = options.stellarRetryAttempts ?? 3;
  const delay = options.stellarRetryDelayMs ?? 2000;

  for (let i = 0; i < attempts; i++) {
    // ... existing logic ...
    await new Promise(resolve => setTimeout(resolve, delay));
  }
}

// ... rest of the file ...