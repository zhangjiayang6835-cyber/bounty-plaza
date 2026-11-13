import { sleep, checkSignal } from '../utils/abort';

export async function pollTransactionStatus(
  hash: string,
  options: { signal?: AbortSignal } = {}
) {
  const { signal } = options;
  while (true) {
    checkSignal(signal);
    const status = await getStellarStatus(hash); // Assume existing helper
    if (status.ready) return status;
    await sleep(2000, signal);
  }
}

export async function waitForAllowance(
  owner: string,
  options: { signal?: AbortSignal } = {}
) {
  const { signal } = options;
  while (true) {
    checkSignal(signal);
    const allowance = await getAllowance(owner);
    if (allowance > 0) return allowance;
    await sleep(3000, signal);
  }
}
