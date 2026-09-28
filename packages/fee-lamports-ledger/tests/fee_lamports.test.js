import assert from 'assert';
import { InMemorySpendLedger } from '../src/ledger.js';
import { InMemoryReceiptStore } from '../src/receipts.js';
import { X402Client } from '../src/client.js';
import { lamportsToMicroCeil } from '../src/signer.js';

async function runTests() {
  console.log('--- Running Fee-Lamports Retention Test Suite (Issue #1660) ---');

  // Test 1: lamportsToMicroCeil ceiling conversion
  const micro = lamportsToMicroCeil(5010, 400);
  assert.strictEqual(micro, 2004, 'Ceiling micro should be 2004 for 5010 lamports at $400/SOL');
  console.log('✓ Test 1 passed: lamportsToMicroCeil accurate');

  // Test 2: Settlement with fee_lamports
  const ledger = new InMemorySpendLedger();
  const receipts = new InMemoryReceiptStore();
  const client = new X402Client({ ledger, receipts });

  const reserveRes = await ledger.reserve({ phase: 'P1', kind: 'x402_payment', amountMicro: 50000, callId: 'call-123' });
  assert.strictEqual(reserveRes.ok, true);

  const payResult = {
    kind: 'paid',
    payer_wallet: 'HKMMpctYvofRCSF2uGnqfEGWcmMhD8A86xFqgmWTvcq9',
    signature: 'tx-sig-actual-lamports-999',
    amount_micro: 10000,
    fee_micro: 2004,
    fee_lamports: 5010,
  };

  const receipt = await client.settlePayment(reserveRes.entryId, 'call-123', payResult);
  assert.strictEqual(receipt.feeLamports, 5010, 'Receipt must retain feeLamports');
  assert.strictEqual(receipt.feeMicro, 2004, 'Receipt must retain feeMicro');

  const entry = await ledger.get(reserveRes.entryId);
  assert.strictEqual(entry.feeLamports, 5010, 'Ledger entry must retain feeLamports');
  assert.strictEqual(entry.feeMicro, 2004, 'Ledger entry must retain feeMicro');
  assert.strictEqual(entry.status, 'settled');
  console.log('✓ Test 2 passed: Settlement with fee_lamports verified');

  // Test 3: Backward compatibility (omitted fee_lamports)
  const reserveRes2 = await ledger.reserve({ phase: 'P1', kind: 'x402_payment', amountMicro: 50000 });
  await ledger.settle(reserveRes2.entryId, { amountMicro: 10000, feeMicro: 2000 });
  const entry2 = await ledger.get(reserveRes2.entryId);
  assert.strictEqual(entry2.feeLamports, null, 'Omitted fee_lamports defaults safely to null');
  assert.strictEqual(entry2.feeMicro, 2000, 'Fee micro preserved');
  console.log('✓ Test 3 passed: Backward compatibility verified');

  console.log('\nAll 3 JavaScript tests passed successfully (0 failures).');
}

runTests().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
