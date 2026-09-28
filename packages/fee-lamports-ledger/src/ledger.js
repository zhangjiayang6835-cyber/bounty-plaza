export class InMemorySpendLedger {
  constructor(ceilingMicro = 1000000) {
    this.ceilingMicro = ceilingMicro;
    this.entriesMap = new Map();
  }

  async reserve(params) {
    const entryId = `entry-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const entry = {
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

  async settle(entryId, params) {
    const entry = this.entriesMap.get(entryId);
    if (!entry) throw new Error(`Entry ${entryId} not found`);

    entry.amountMicro = params.amountMicro;
    entry.feeMicro = params.feeMicro;
    entry.feeLamports = params.feeLamports !== undefined ? params.feeLamports : null;
    entry.txSignature = params.txSignature;
    entry.status = 'settled';

    return { ...entry };
  }

  async get(entryId) {
    const entry = this.entriesMap.get(entryId);
    return entry ? { ...entry } : undefined;
  }

  async entries() {
    return Array.from(this.entriesMap.values()).map(e => ({ ...e }));
  }
}
