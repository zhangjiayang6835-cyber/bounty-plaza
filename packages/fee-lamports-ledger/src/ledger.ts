/**
 * Spend Ledger for x402 inference calls with fee_lamports retention
 */

export interface SpendEntry {
  id: string;
  phase: string;
  kind: string;
  amountMicro: number;
  feeMicro: number;
  feeLamports: number | null;
  status: 'reserved' | 'settled' | 'released';
  txSignature?: string | null;
  callId?: string | null;
  createdAt: number;
}

export interface SettleParams {
  amountMicro: number;
  feeMicro: number;
  feeLamports?: number | null;
  txSignature?: string | null;
}

export class InMemorySpendLedger {
  private entriesMap = new Map<string, SpendEntry>();

  constructor(private ceilingMicro: number = 1_000_000) {}

  async reserve(params: { phase: string; kind: string; amountMicro: number; callId?: string }): Promise<{ ok: boolean; entryId: string }> {
    const entryId = `entry-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entry: SpendEntry = {
      id: entryId,
      phase: params.phase,
      kind: params.kind,
      amountMicro: params.amountMicro,
      feeMicro: 0,
      feeLamports: null,
      status: 'reserved',
      callId: params.callId,
      createdAt: Date.now(),
    };
    this.entriesMap.set(entryId, entry);
    return { ok: true, entryId };
  }

  async settle(entryId: string, params: SettleParams): Promise<SpendEntry> {
    const entry = this.entriesMap.get(entryId);
    if (!entry) throw new Error(`Entry ${entryId} not found`);

    entry.amountMicro = params.amountMicro;
    entry.feeMicro = params.feeMicro;
    entry.feeLamports = params.feeLamports !== undefined ? params.feeLamports : null;
    entry.txSignature = params.txSignature;
    entry.status = 'settled';

    return { ...entry };
  }

  async get(entryId: string): Promise<SpendEntry | undefined> {
    const entry = this.entriesMap.get(entryId);
    return entry ? { ...entry } : undefined;
  }

  async entries(): Promise<SpendEntry[]> {
    return Array.from(this.entriesMap.values()).map(e => ({ ...e }));
  }
}
