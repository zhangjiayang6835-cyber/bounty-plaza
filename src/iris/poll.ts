import { IRIS_MAINNET_BASE_URL, IRIS_SANDBOX_BASE_URL, DEFAULT_POLL_INTERVAL_MS, DEFAULT_POLL_TIMEOUT_MS } from "../constants.js";
import { AttestationNotReadyError, IrisRequestError } from "../errors.js";
import type { IrisMessage, IrisMessagesResponse, IrisFeesResponse } from "./types.js";

export function irisBaseUrl(useSandbox: boolean): string {
  return useSandbox ? IRIS_SANDBOX_BASE_URL : IRIS_MAINNET_BASE_URL;
}

/** Fetches the current Fast Transfer fee (in basis points) for a source/destination domain pair. */
export async function fetchFastTransferFeeBps(
  sourceDomain: number,
  destDomain: number,
  useSandbox: boolean,
  signal?: AbortSignal,
): Promise<number> {
  if (signal?.aborted) {
    throw signal.reason ?? new DOMException("The operation was aborted", "AbortError");
  }
  const url = `${irisBaseUrl(useSandbox)}burn/USDC/fees/${sourceDomain}/${destDomain}`;
  let res: Response;
  try {
    res = await fetch(url, { signal });
  } catch (err) {
    if (signal?.aborted || (err instanceof Error && err.name === "AbortError")) {
      throw signal?.reason ?? err;
    }
    throw err;
  }
  if (!res.ok) {
    throw new IrisRequestError(
      `Iris fees request failed: ${res.status} ${res.statusText}`,
      res.status,
    );
  }
  const body = (await res.json()) as IrisFeesResponse;
  const fastEntry = body.find((entry) => entry.finalityThreshold <= 1000);
  if (!fastEntry) {
    throw new Error(
      `No fast transfer tier available from Iris for domain pair ${sourceDomain} -> ${destDomain}`,
    );
  }
  return fastEntry.minimumFee;
}

/**
 * Consecutive unusable responses tolerated before polling gives up. A single 5xx or dropped
 * connection is normal against a public API, and failing the whole transfer on one blip
 * would be worse than the outage it reports. Sustained failure is different: it means
 * something polling cannot fix, so it is surfaced rather than hidden behind the deadline.
 */
export const IRIS_MAX_CONSECUTIVE_FAILURES = 5;

type PollOutcome =
  | { kind: "message"; message: IrisMessage; complete: boolean }
  | { kind: "not-indexed" }
  | { kind: "failure"; error: IrisRequestError };

/**
 * Reads the current attestation state for one burn. Iris answers 404 until it has indexed a
 * burn, which is the expected state for the first polls of any new transfer, so a 404 is
 * reported as "not indexed yet" rather than as an error. Everything else that is not a
 * success means the service is unreachable or unhealthy.
 *
 * A message that Iris has indexed but not yet attested is reported as a message with
 * complete: false. Its bytes are already final, so a caller that only needs to know what
 * the burn will do can read it before Circle has signed.
 */
async function pollOnce(
  url: string,
  transactionHash: string,
  signal?: AbortSignal,
): Promise<PollOutcome> {
  if (signal?.aborted) {
    throw signal.reason ?? new DOMException("The operation was aborted", "AbortError");
  }
  let res: Response;
  try {
    res = await fetch(url, { signal });
  } catch (err) {
    if (signal?.aborted || (err instanceof Error && err.name === "AbortError")) {
      throw signal?.reason ?? err;
    }
    const reason = err instanceof Error ? err.message : String(err);
    return {
      kind: "failure",
      error: new IrisRequestError(
        `Iris attestation request for burn ${transactionHash} failed: ${reason}`,
      ),
    };
  }

  if (res.status === 404) {
    return { kind: "not-indexed" };
  }

  if (!res.ok) {
    return {
      kind: "failure",
      error: new IrisRequestError(
        `Iris attestation request for burn ${transactionHash} failed with ${res.status} ${res.statusText}`,
        res.status,
      ),
    };
  }

  const body = (await res.json()) as IrisMessagesResponse;
  const message = body.messages[0];
  if (!message) {
    return { kind: "not-indexed" };
  }
  return {
    kind: "message",
    message,
    complete: message.status === "complete" && Boolean(message.attestation),
  };
}

function attestationUrl(sourceDomain: number, transactionHash: string, useSandbox: boolean): string {
  return `${irisBaseUrl(useSandbox)}messages/${sourceDomain}?transactionHash=${transactionHash}`;
}

/**
 * Runs `attempt` until it yields a non-failure outcome, or until Iris has failed
 * consecutively IRIS_MAX_CONSECUTIVE_FAILURES times, spacing retries by delayMs.
 * Only `failure` outcomes — Iris unreachable or unhealthy — consume the shared
 * tolerance; a not-indexed read and a successful read return to the caller
 * immediately, which decides what each of those means. Sharing this with the
 * poll loop is what keeps a single dropped connection from making the one-shot
 * read path strictly less reliable than the polling one.
 */
async function retryTransientFailures(
  attempt: () => Promise<PollOutcome>,
  delayMs: number = DEFAULT_POLL_INTERVAL_MS,
  maxFailures: number = IRIS_MAX_CONSECUTIVE_FAILURES,
  signal?: AbortSignal,
): Promise<PollOutcome> {
  let consecutiveFailures = 0;
  for (;;) {
    if (signal?.aborted) {
      throw signal.reason ?? new DOMException("The operation was aborted", "AbortError");
    }
    const outcome = await attempt();
    if (outcome.kind !== "failure") {
      return outcome;
    }
    consecutiveFailures += 1;
    if (consecutiveFailures >= maxFailures) {
      throw outcome.error;
    }
    await sleep(delayMs, signal);
  }
}

/**
 * Reads a burn's attestation state once, without waiting. Returns as soon as Iris has
 * indexed the burn, which happens well before Circle signs it, so a caller that wants to
 * inspect the burn or hand the wait off to a background job does not have to hold a request
 * open for the whole attestation window.
 *
 * The returned message's `status` says whether the attestation itself is ready. Throws
 * AttestationNotReadyError when Iris has not indexed the burn at all yet, which is a
 * retryable state, and IrisRequestError when Iris stays unreachable or unhealthy across
 * the same consecutive-failure tolerance the poll loop uses. A 404 or empty response is
 * an expected "not indexed yet" state, not a failure, so it is never retried: this read
 * answers immediately either way and never waits for indexing.
 */
export async function getAttestation(params: {
  sourceDomain: number;
  transactionHash: string;
  useSandbox: boolean;
  pollInterval?: number;
  signal?: AbortSignal;
}): Promise<IrisMessage> {
  if (params.signal?.aborted) {
    throw params.signal.reason ?? new DOMException("The operation was aborted", "AbortError");
  }
  const outcome = await retryTransientFailures(
    () =>
      pollOnce(
        attestationUrl(params.sourceDomain, params.transactionHash, params.useSandbox),
        params.transactionHash,
        params.signal,
      ),
    params.pollInterval ?? DEFAULT_POLL_INTERVAL_MS,
    IRIS_MAX_CONSECUTIVE_FAILURES,
    params.signal,
  );

  if (outcome.kind === "message") {
    return outcome.message;
  }
  if (outcome.kind === "failure") {
    throw outcome.error;
  }
  throw new AttestationNotReadyError(
    `Iris has not indexed burn ${params.transactionHash} yet`,
    params.transactionHash,
  );
}

/**
 * Polls Iris for the attestation of a burn transaction until it is complete or
 * pollTimeout elapses. Resolves with the completed IrisMessage.
 *
 * Throws AttestationNotReadyError when the deadline passes without an attestation, which
 * means the burn is real but unattested and the caller should retry. Throws
 * IrisRequestError, without waiting out the deadline, when Iris is persistently returning
 * responses that polling cannot resolve.
 */
export async function pollForAttestation(params: {
  sourceDomain: number;
  transactionHash: string;
  useSandbox: boolean;
  pollInterval?: number;
  pollTimeout?: number;
  signal?: AbortSignal;
}): Promise<IrisMessage> {
  if (params.signal?.aborted) {
    throw params.signal.reason ?? new DOMException("The operation was aborted", "AbortError");
  }
  const pollInterval = params.pollInterval ?? DEFAULT_POLL_INTERVAL_MS;
  const pollTimeout = params.pollTimeout ?? DEFAULT_POLL_TIMEOUT_MS;
  const url = attestationUrl(params.sourceDomain, params.transactionHash, params.useSandbox);

  const deadline = Date.now() + pollTimeout;
  let consecutiveFailures = 0;

  while (Date.now() < deadline) {
    if (params.signal?.aborted) {
      throw params.signal.reason ?? new DOMException("The operation was aborted", "AbortError");
    }
    const outcome = await pollOnce(url, params.transactionHash, params.signal);

    if (outcome.kind === "message" && outcome.complete) {
      return outcome.message;
    }

    if (outcome.kind === "failure") {
      consecutiveFailures += 1;
      if (consecutiveFailures >= IRIS_MAX_CONSECUTIVE_FAILURES) {
        throw outcome.error;
      }
    } else {
      consecutiveFailures = 0;
    }

    const waitMs = Math.min(pollInterval, Math.max(0, deadline - Date.now()));
    await sleep(waitMs, params.signal);
  }

  throw new AttestationNotReadyError(
    `Timed out after ${pollTimeout}ms waiting for Iris attestation of ${params.transactionHash}`,
    params.transactionHash,
  );
}

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
