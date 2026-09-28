export class InMemoryReceiptStore {
  constructor() {
    this.records = new Map();
  }

  async record(record) {
    this.records.set(record.id, { ...record });
  }

  async get(id) {
    const r = this.records.get(id);
    return r ? { ...r } : undefined;
  }
}
