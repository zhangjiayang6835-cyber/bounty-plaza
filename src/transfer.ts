import { TransferError } from './errors';
import { checkSignal } from './utils/abort';

export async function transfer(options: TransferOptions) {
  const { signal } = options;

  // 1. Pre-burn check
  checkSignal(signal);

  let burnTxHash: string | undefined;

  try {
    // 2. Perform Burn
    // Assume submitBurn is the internal method
    burnTxHash = await submitBurn(options);

    // 3. Post-burn check: If aborted right after submission
    if (signal?.aborted) {
      throw new TransferError(
        'Transfer aborted after burn submission. Use burnTxHash to recover.',
        { burnTxHash, code: 'ABORTED_POST_BURN' }
      );
    }

    // 4. Polling for attestation
    const attestation = await pollForAttestation(burnTxHash, { signal });

    // 5. Complete Mint
    return await completeMint({ ...options, attestation, signal });

  } catch (err) {
    if (err.name === 'AbortError' && burnTxHash) {
      // Wrap native AbortError into TransferError if we have a hash
      throw new TransferError(
        'Transfer aborted. Burn transaction was already submitted.',
        { burnTxHash, code: 'ABORTED_POST_BURN' }
      );
    }
    throw err;
  }
}
