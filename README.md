export class SubmissionTimeoutError extends Error {
  public readonly hash: string;

  constructor(hash: string, message?: string) {
    super(message || `Transaction ${hash} timed out waiting for confirmation`);
    this.name = 'SubmissionTimeoutError';
    this.hash = hash;
  }
}

/**
 * Maximum consecutive RPC errors tolerated during Stellar confirmation polling
 * before considering the request timed out. Matches tolerance policy in src/iris/poll.ts.
 */
export const STELLAR_MAX_CONSECUTIVE_FAILURES = 5;

/**
 * Poll interval and backoff delay (in ms) between transaction status checks.
 */
export const STELLAR_POLL_INTERVAL_MS = 2000;

export interface StellarServer {
  getTransaction(hash: string): Promise<{ status: string; [key: string]: any }>;
}

/**
 * Polls Stellar transaction status until confirmed, failed, or deadline passed.
 * Handles transient RPC errors up to STELLAR_MAX_CONSECUTIVE_FAILURES before throwing SubmissionTimeoutError.
 *
 * @param server The Stellar RPC server instance
 * @param hash Transaction hash to poll
 * @param timeoutMs Overall polling timeout in milliseconds
 * @param pollIntervalMs Interval between status requests in milliseconds
 * @returns Resolves with the transaction hash upon SUCCESS status
 */
export async function pollTransactionStatus(
  server: StellarServer,
  hash: string,
  timeoutMs: number = 60000,
  pollIntervalMs: number = STELLAR_POLL_INTERVAL_MS
): Promise<string> {
  const startTime = Date.now();
  let consecutiveFailures = 0;

  while (Date.now() - startTime < timeoutMs) {
    let txResponse;
    try {
      txResponse = await server.getTransaction(hash);
      consecutiveFailures = 0;
    } catch (err: any) {
      consecutiveFailures++;
      if (consecutiveFailures >= STELLAR_MAX_CONSECUTIVE_FAILURES) {
        throw new SubmissionTimeoutError(
          hash,
          `Transaction ${hash} polling exceeded maximum consecutive RPC failures (${consecutiveFailures}): ${err?.message || err}`
        );
      }
      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
      continue;
    }

    if (txResponse.status === 'SUCCESS') {
      return hash;
    }

    if (txResponse.status === 'FAILED') {
      throw new Error(`Transaction ${hash} failed with status: FAILED`);
    }

    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }

  // The transaction was already broadcast. Surface hash via SubmissionTimeoutError on timeout.
  throw new SubmissionTimeoutError(
    hash,
    `Transaction ${hash} timed out after ${timeoutMs}ms waiting for confirmation`
  );
}
