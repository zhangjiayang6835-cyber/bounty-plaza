/**
 * Inference Call Receipts with fee_lamports retention
 */

export interface InferenceCallRecord {
  id: string;
  scheme: 'onchain' | 'balance';
  payerWallet: string;
  payTxSignature?: string | null;
  paidMicro?: number | null;
  feeMicro?: number | null;
  feeLamports?: number | null;
  chargedMicro?: number | null;
  createdAt: number;
}

export class InMemoryReceiptStore {
  private records = new Map<string, InferenceCallRecord>();

  async record(record: InferenceCallRecord): Promise<void> {
    this.records.set(record.id, { ...record });
  }

  async get(id: string): Promise<InferenceCallRecord | undefined> {
    const r = this.records.get(id);
    return r ? { ...r } : undefined;
  }
}
