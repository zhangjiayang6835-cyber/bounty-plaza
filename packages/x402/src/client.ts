import { settlePayment } from '../../services/signer'

// ... existing imports

export async function payForInference(
  // ... existing params
): Promise<{ fee_micro: number, fee_lamports: number }> {
  const res = await signer.payForInference(/* ... */)
  await settlePayment(
    res.txSignature,
    res.feeLamports,  // Pass actual fee
    // ... other params
  )
  return { fee_micro: res.fee_micro, fee_lamports: res.feeLamports }
}