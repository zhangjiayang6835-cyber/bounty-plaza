/**
 * Signer Client & Payment Result interface with fee_lamports retention
 */

export interface PayResult {
  kind: 'paid';
  payer_wallet: string;
  signature: string;
  amount_micro: number;
  fee_micro: number;
  fee_lamports?: number;
}

export function lamportsToMicroCeil(lamports: number, solUsdCeilingPrice: number = 400.0): number {
  if (lamports <= 0) return 0;
  // 1 SOL = 1e9 lamports; micro-USD = lamports * price * 1e6 / 1e9 = (lamports * price) / 1000
  return Math.ceil((lamports * solUsdCeilingPrice) / 1_000);
}
