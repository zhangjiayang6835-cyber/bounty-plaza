import { solUsdCeilingPrice } from './constants'

// ... existing imports

export interface PayResult {
  success: boolean
  fee_lamports: number  // Actual fee paid (lamports)
  fee_micro: number     // Conservative micro-USD estimate
  // ... other fields
}

export async function settlePayment(
  txSignature: string,
  feeLamports: number,
  // ... other params
): Promise<void> {
  const feeMicro = lamportsToMicroCeil(feeLamports, solUsdCeilingPrice)

  await db.insertInto('inference_calls').values({
    // ... existing fields
    fee_micro: feeMicro,
    fee_lamports: feeLamports,  // Add actual fee
  }).execute()
}

function lamportsToMicroCeil(lamports: number, usdPerSol: number): number {
  return Math.ceil((lamports / 1e9) * usdPerSol * 1e6)  // 1 SOL = 1e9 lamports
}