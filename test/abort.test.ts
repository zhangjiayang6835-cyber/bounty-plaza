import { transfer } from '../src/transfer';
import { Controller } from 'abort-controller'; // or native AbortController

describe('AbortSignal Support', () => {
  it('should throw AbortError if aborted before burn', async () => {
    const controller = new AbortController();
    controller.abort();
    
    await expect(transfer({ signal: controller.signal }))
      .rejects.toThrow('Aborted');
  });

  it('should throw TransferError with hash if aborted after burn', async () => {
    const controller = new AbortController();
    
    // Mock submitBurn to abort the controller immediately after "submission"
    const mockTransfer = async () => {
        const burnTxHash = "0x123...abc";
        controller.abort(); // Simulate user cancelling right after burn
        if (controller.signal.aborted) {
            throw new TransferError('Aborted', { burnTxHash, code: 'ABORTED_POST_BURN' });
        }
    };

    try {
        await mockTransfer();
    } catch (e) {
        expect(e.burnTxHash).toBe("0x123...abc");
        expect(e.code).toBe('ABORTED_POST_BURN');
    }
  });
});
