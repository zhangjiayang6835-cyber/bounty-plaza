import * as anchor from '@coral-xyz/anchor';
import { expect } from 'chai';

describe('dispatcher', () => {
  it('prevents unauthorized account ownership', async () => {
    // Test logic to ensure CPI fails when account owner is invalid
    try {
      await program.methods.dispatchCpi().accounts({ ... }).rpc();
      expect.fail('Should have failed due to invalid owner');
    } catch (err) {
      expect(err.toString()).to.include('AccountOwnedByWrongProgram');
    }
  });
});