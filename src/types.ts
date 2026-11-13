export interface TransferOptionsBase {
  // ... existing fields
  signal?: AbortSignal;
}

export interface CompleteMintOptions {
  // ... existing fields
  signal?: AbortSignal;
}

export enum TransferErrorCode {
  ABORTED_POST_BURN = 'ABORTED_POST_BURN',
  // ... other codes
}
