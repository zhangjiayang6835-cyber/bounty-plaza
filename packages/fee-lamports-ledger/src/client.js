export class X402Client {
  constructor(opts) {
    this.opts = opts;
  }

  async settlePayment(entryId, callId, pay) {
    await this.opts.ledger.settle(entryId, {
      amountMicro: pay.amount_micro,
      feeMicro: pay.fee_micro,
      feeLamports: pay.fee_lamports,
      txSignature: pay.signature,
    });

    const record = {
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
