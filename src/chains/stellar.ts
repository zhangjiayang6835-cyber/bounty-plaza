import {
  Contract,
  TransactionBuilder,
  rpc,
} from "@stellar/stellar-sdk";
import {
  stellarConfig,
  STELLAR_TX_TIMEOUT_SECONDS,
  STELLAR_CONFIRMATION_TIMEOUT_MS,
  STELLAR_INCLUSION_FEE,
} from "../constants.js";
import type { StellarSigner, Network } from "../types.js";
import { SubmissionTimeoutError } from "../errors.js";

export interface StellarRetryOptions {
  attempts?: number;
  delayMs?: number;
}

function getServer(network: Network, rpcUrl?: string): rpc.Server {
  return new rpc.Server(rpcUrl ?? stellarConfig(network).sorobanRpcUrl);
}

async function signTransaction(
  xdr: string,
  signer: StellarSigner,
  network: Network,
): Promise<string> {
  const passphrase = stellarConfig(network).networkPassphrase;
  if (signer.signTransaction) {
    return signer.signTransaction(xdr, passphrase);
  }
  if (signer.keypair) {
    const tx = TransactionBuilder.fromXDR(xdr, passphrase);
    tx.sign(signer.keypair);
    return tx.toXDR();
  }
  throw new Error("StellarSigner must provide either a keypair or a signTransaction function");
}

/**
 * Consecutive transient RPC errors tolerated before polling considers the RPC outage sustained.
 * A single connection reset, HTTP 5xx, or network blip from the Soroban RPC is common;
 * failing the broadcast transaction immediately with an untyped error would drop the hash
 * and prevent recovery of an already-broadcast transaction.
 */
export const STELLAR_RPC_MAX_CONSECUTIVE_FAILURES = 5;
export const STELLAR_RPC_RETRY_INTERVAL_MS = 2000;

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      return reject(signal.reason ?? new DOMException("The operation was aborted", "AbortError"));
    }
    let onAbort: (() => void) | undefined;
    const timer = setTimeout(() => {
      if (signal && onAbort) {
        signal.removeEventListener("abort", onAbort);
      }
      resolve();
    }, ms);
    if (signal) {
      onAbort = () => {
        clearTimeout(timer);
        reject(signal.reason ?? new DOMException("The operation was aborted", "AbortError"));
      };
      signal.addEventListener("abort", onAbort, { once: true });
    }
  });
}

/**
 * Polls the Soroban RPC server for confirmation of a transaction.
 * Tolerates transient RPC failures up to maxConsecutiveFailures, preserving the broadcast
 * tx hash in SubmissionTimeoutError on sustained outage or overall timeout.
 */
export async function pollTransactionStatus(
  server: rpc.Server,
  hash: string,
  options?: {
    timeoutMs?: number;
    pollIntervalMs?: number;
    maxConsecutiveFailures?: number;
    signal?: AbortSignal;
  },
): Promise<string> {
  const timeoutMs = options?.timeoutMs ?? STELLAR_CONFIRMATION_TIMEOUT_MS;
  const pollIntervalMs = options?.pollIntervalMs ?? STELLAR_RPC_RETRY_INTERVAL_MS;
  const maxConsecutiveFailures = options?.maxConsecutiveFailures ?? STELLAR_RPC_MAX_CONSECUTIVE_FAILURES;
  const signal = options?.signal;

  const deadline = Date.now() + timeoutMs;
  let consecutiveFailures = 0;

  while (Date.now() < deadline) {
    if (signal?.aborted) {
      throw new SubmissionTimeoutError(
        `Operation aborted waiting for Stellar transaction ${hash} to confirm`,
        hash,
      );
    }
    try {
      const result = await server.getTransaction(hash);
      consecutiveFailures = 0;
      if (result.status === "SUCCESS") return hash;
      if (result.status === "FAILED") {
        throw new Error(`Stellar transaction ${hash} failed`);
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes(`Stellar transaction ${hash} failed`)) {
        throw err;
      }

      consecutiveFailures += 1;
      if (consecutiveFailures >= maxConsecutiveFailures) {
        throw new SubmissionTimeoutError(
          `Timed out waiting for Stellar transaction ${hash} to confirm after ${consecutiveFailures} consecutive RPC failures: ${err instanceof Error ? err.message : String(err)}`,
          hash,
        );
      }
    }

    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    await sleep(Math.min(pollIntervalMs, remaining), signal);
  }

  throw new SubmissionTimeoutError(
    `Timed out waiting for Stellar transaction ${hash} to confirm after ${timeoutMs}ms`,
    hash,
  );
}
