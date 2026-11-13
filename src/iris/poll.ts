import { sleep, checkSignal } from '../utils/abort';

export async function pollForAttestation(
  messageHash: string,
  options: { signal?: AbortSignal; pollInterval?: number; pollTimeout?: number } = {}
): Promise<string> {
  const { signal, pollInterval = 5000, pollTimeout = 600000 } = options;
  const startTime = Date.now();

  while (Date.now() - startTime < pollTimeout) {
    checkSignal(signal);

    try {
      const response = await fetch(`https://iris-api.circle.com/attestations/${messageHash}`, {
        signal // Pass signal to native fetch
      });
      
      if (response.ok) {
        const { attestation, status } = await response.json();
        if (status === 'complete') return attestation;
      }
    } catch (e) {
      if (e.name === 'AbortError') throw e;
      // Ignore transient network errors during polling
    }

    await sleep(pollInterval, signal);
  }

  throw new Error('Attestation polling timed out');
}
