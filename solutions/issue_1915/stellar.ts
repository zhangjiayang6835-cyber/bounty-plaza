/**
 * Stellar Confirmation Polling with Transient Fault Tolerance.
 * Upstream Reference: Parabola-org/parabola (src/chains/stellar.ts)
 * Resolves Issue #1915 (and Parabola-org/parabola#1).
 */

export class SubmissionTimeoutError extends Error {
  public readonly hash: string;

  constructor(message: string, hash: string) {
    super(message);
    this.name = "SubmissionTimeoutError";
    this.hash = hash;
  }
}

/**
 * Consecutive transient `getTransaction` failures tolerated while polling for
 * confirmation, and the backoff between attempts. This mirrors the tolerance
 * policy `src/iris/poll.ts` applies to Iris: one blip is normal against a
 * public endpoint, sustained failure is surfaced — here as
 * SubmissionTimeoutError, which carries the hash — instead of being absorbed
 * into a bare error that loses the handle on an already-broadcast transaction.
 */
export const STELLAR_CONFIRMATION_MAX_CONSECUTIVE_RPC_FAILURES = 5;
export const STELLAR_CONFIRMATION_RETRY_DELAY_MS = 1000;
export const STELLAR_CONFIRMATION_TIMEOUT_MS = 60000;

export interface StellarRpcServer {
  getTransaction(hash: string): Promise<{ status: "SUCCESS" | "FAILED" | "PENDING"; [key: string]: any }>;
}

export async function pollTransactionStatus(
  server: StellarRpcServer,
  hash: string,
  timeoutMs: number = STELLAR_CONFIRMATION_TIMEOUT_MS,
  retryDelayMs: number = STELLAR_CONFIRMATION_RETRY_DELAY_MS,
  maxConsecutiveFailures: number = STELLAR_CONFIRMATION_MAX_CONSECUTIVE_RPC_FAILURES
): Promise<string> {
  const deadline = Date.now() + timeoutMs;
  let consecutiveRpcFailures = 0;

  while (Date.now() < deadline) {
    let result: { status: "SUCCESS" | "FAILED" | "PENDING"; [key: string]: any };
    try {
      result = await server.getTransaction(hash);
      consecutiveRpcFailures = 0;
    } catch (err) {
      consecutiveRpcFailures += 1;
      if (consecutiveRpcFailures >= maxConsecutiveFailures) {
        throw new SubmissionTimeoutError(
          `Stellar RPC failed ${consecutiveRpcFailures} consecutive times polling transaction ${hash}: ${
            err instanceof Error ? err.message : String(err)
          }`,
          hash
        );
      }
      await new Promise((resolve) => setTimeout(resolve, retryDelayMs));
      continue;
    }

    if (result.status === "SUCCESS") return hash;
    if (result.status === "FAILED") {
      throw new Error(`Stellar transaction ${hash} failed`);
    }

    await new Promise((resolve) => setTimeout(resolve, retryDelayMs));
  }

  throw new SubmissionTimeoutError(
    `Stellar transaction ${hash} confirmation timed out after ${timeoutMs}ms`,
    hash
  );
}
