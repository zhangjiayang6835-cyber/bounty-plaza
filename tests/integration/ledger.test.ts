import { expect, test } from 'vitest'
import { payForInference } from '../../packages/x402'
import { db } from '../../db'

// Mock constants for test
const mockFeeLamports = 2004000  // ~$0.002004 at $400/SOL
const mockSolUsdPrice = 400

const expectedFeeMicro = Math.ceil((mockFeeLamports / 1e9) * mockSolUsdPrice * 1e6)

// ... existing test setup

test('records actual fee lamports alongside micro estimate', async () => {
  const { fee_micro, fee_lamports } = await payForInference(/* ... */)

  const call = await db.selectFrom('inference_calls').selectAll().where('tx_hash', '=', 'mock-tx').executeTakeFirstOrThrow()

  expect(call.fee_micro).toBe(expectedFeeMicro)  // Ceiling logic unchanged
  expect(call.fee_lamports).toBe(mockFeeLamports)  // Actual fee recorded
  expect(call.fee_lamports).not.toBeNull()
})
