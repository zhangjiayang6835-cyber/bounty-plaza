// Fix: src/chains/arc.ts & src/transfer.ts
import { publicClient, walletClient } from './clients';
import { erc20Abi } from 'viem';

export async function ensureArcUsdcAllowance(
  ownerAddress: `0x${string}`,
  spenderAddress: `0x${string}`,
  amountRaw: bigint
): Promise<{ skipped: boolean; txHash?: `0x${string}` }> {
  let currentAllowance: bigint;
  try {
    currentAllowance = (await publicClient.readContract({
      address: ARC_USDC_ADDRESS,
      abi: erc20Abi,
      functionName: 'allowance',
      args: [ownerAddress, spenderAddress],
    })) as bigint;
  } catch (err) {
    // Fail closed: if read fails, proceed with exact-amount write
    currentAllowance = 0n;
  }

  // If standing allowance already covers the burn, skip transaction write entirely
  if (currentAllowance >= amountRaw) {
    return { skipped: true };
  }

  // Otherwise, submit exact-amount approve transaction
  const txHash = await walletClient.writeContract({
    address: ARC_USDC_ADDRESS,
    abi: erc20Abi,
    functionName: 'approve',
    args: [spenderAddress, amountRaw],
  });

  await publicClient.waitForTransactionReceipt({ hash: txHash });
  return { skipped: false, txHash };
}
