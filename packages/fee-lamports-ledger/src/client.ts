/**
 * X402 Settlement Client preserving fee_lamports to ledger
 */

import { InMemorySpendLedger } from './ledger.js';
import { InMemoryReceiptStore, InferenceCallRecord } from './receipts.js';
import { PayResult } from './signer.js';

export interface X402ClientOptions {
  ledger: InMemorySpendLedger;
  receipts: InMemoryReceiptStore;
  solUsdCeilingPrice?: number;
}

export class X402Client {
  constructor(private opts: X402ClientOptions) {}

  async settlePayment(
    entryId: string,
    callId: string,
    pay: PayResult
  ): Promise<InferenceCallRecord> {
    // Settle in ledger preserving both capped fee_micro and factual fee_lamports
    await this.opts.ledger.settle(entryId, {
      amountMicro: pay.amount_micro,
      feeMicro: pay.fee_micro,
      feeLamports: pay.fee_lamports,
      txSignature: pay.signature,
    });

    const record: InferenceCallRecord = {
      id: callId,
      scheme: 'onchain',
      payerWallet: pay.payer_wallet,
      payTxSignature: pay.signature,
      paidMicro: pay.amount_micro,
      feeMicro: pay.fee_micro,
      feeLamports: pay.fee_lamports,
      createdAt: Date.now(),
    };

    await this.opts.receipts.record(record);
    return record;
  }
}
