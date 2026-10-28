```typescript
import { TransferProgressEvent } from './index';

type TransferProgressEvent =
  | { stage: 'recipient-check'; }
  | { stage: 'approve'; }
  | { stage: 'burn-submitted'; burnTxHash?: string; }
  | { stage: 'burn-confirmed'; burnTxHash?: string; }
  | { stage: 'attestation'; }
  | { stage: 'mint-submitted'; mintTxHash?: string; }
  | { stage: 'mint-confirmed'; mintTxHash?: string; };

export function transfer(
  options: {
    onProgress?: (event: TransferProgressEvent) => void;
  } & Parameters<typeof transfer.noParam)
): Promise<TransferResult> {
  const { onProgress } = options;

  // Existing code from transfer.ts:43-139
  // (Assume the existing transfer logic is here)

  // Add onProgress calls at each stage boundary
  try {
    // 1. Recipient check
    if (recipientOk) {
      onProgress?.({ stage: 'recipient-check' });
    }

    // 2. Approve
    const approved = await批准();
    if (approved) {
      onProgress?.({ stage: 'approve' });
    }

    // 3. Burn submitted
    const burnTxHash = await burn();
    onProgress?.({ stage: 'burn-submitted', burnTxHash });

    // 4. Burn confirmed
    await确认();
    onProgress?.({ stage: 'burn-confirmed', burnTxHash });

    // 5. Attestation
    onProgress?.({ stage: 'attestation' });

    // 6. Mint submitted
    const mintTxHash = await mint();
    onProgress?.({ stage: 'mint-submitted', mintTxHash });

    // 7. Mint confirmed
    onProgress?.({ stage: 'mint-confirmed', mintTxHash });

    return { success: true };
  } catch (error) {
    // Handle any exceptions from onProgress without breaking transfer
    return { success: false, error: error.message };
  }
}
```