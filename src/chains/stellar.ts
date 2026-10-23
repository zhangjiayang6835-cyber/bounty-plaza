import {
  Contract,
  TransactionBuilder,
  BASE_FEE,
  Address,
  nativeToScVal,
  scValToNative,
  rpc,
} from "@stellar/stellar-sdk";
import { stellarConfig, STELLAR_TX_TIMEOUT_SECONDS, STELLAR_CONFIRMATION_TIMEOUT_MS, STELLAR_INCLUSION_FEE } from "../constants.js";
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
 * Simulates, prepares, signs, and submits a Soroban contract invocation, then
 * polls the RPC server until the transaction is confirmed. Returns the tx hash.
 */
async function invokeContract(
  contractId: string,
  method: string,
  args: ReturnType<typeof nativeToScVal>[],
  signer: StellarSigner,
  network: Network,
  rpcUrl?: string,
): Promise<string> {
  const server = getServer(network, rpcUrl);
  const account = await server.getAccount(signer.publicKey);
  const contract = new Contract(contractId);

  const builtTx = new TransactionBuilder(account, {
    fee: STELLAR_INCLUSION_FEE,
    networkPassphrase: stellarConfig(network).networkPassphrase,
  })
    .addOperation(contract.call(method, ...args))
    .setTimeout(STELLAR_TX_TIMEOUT_SECONDS)
    .build();

  const prepared = await server.prepareTransaction(builtTx);
  const signedXdr = await signTransaction(prepared.toXDR(), signer, network);
  const signedTx = TransactionBuilder.fromXDR(signedXdr, stellarConfig(network).networkPassphrase);

  const sendResult = await server.sendTransaction(signedTx);
  if (sendResult.status === "ERROR") {
    throw new Error(`Stellar transaction submission failed: ${JSON.stringify(sendResult.errorResult)}`);
  }

  return pollTransactionStatus(server, sendResult.hash);
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
    try {
      await sleep(Math.min(pollIntervalMs, Math.max(0, remaining)), signal);
    } catch {
      throw new SubmissionTimeoutError(
        `Operation aborted waiting for Stellar transaction ${hash} to confirm`,
        hash,
      );
    }
  }

  // The transaction was broadcast (this hash came from a successful sendTransaction);
  // confirmation did not arrive within the timeout. This differs from never having been
  // submitted, so the hash is surfaced for callers to act on instead of being discarded
  // in a bare error.
  throw new SubmissionTimeoutError(`Timed out waiting for Stellar transaction ${hash} to confirm`, hash);
}

export interface StellarRetryOptions {
  /** Maximum number of attempts before failing. Must be a positive integer when provided. */
  attempts?: number;
  /** Delay in milliseconds between attempts. Must be a non-negative number when provided. */
  delayMs?: number;
}

function resolveRetryConfig(
  retry: StellarRetryOptions | undefined,
  defaultAttempts: number,
  defaultDelayMs: number,
): { attempts: number; delayMs: number } {
  const attempts = retry?.attempts ?? defaultAttempts;
  const delayMs = retry?.delayMs ?? defaultDelayMs;

  if (!Number.isInteger(attempts) || attempts < 1) {
    throw new Error(`Invalid Stellar retry attempts: ${attempts}. Expected a positive integer.`);
  }
  if (!Number.isFinite(delayMs) || delayMs < 0) {
    throw new Error(`Invalid Stellar retry delayMs: ${delayMs}. Expected a non-negative number.`);
  }

  return { attempts, delayMs };
}

/**
 * Approves Stellar's TokenMessengerMinter to pull USDC from the signer via the
 * SEP-41 token's transfer_from, mirroring the ERC20 approve step CCTP needs on
 * EVM chains. Required before deposit_for_burn, which otherwise fails with
 * "not enough allowance to spend".
 */
export async function approveUsdcOnStellar(
  amountRaw: bigint,
  signer: StellarSigner,
  network: Network,
  rpcUrl?: string,
  retry?: StellarRetryOptions,
  signal?: AbortSignal,
): Promise<string> {
  if (signal?.aborted) {
    throw signal.reason ?? new DOMException("The operation was aborted", "AbortError");
  }
  const retryConfig = resolveRetryConfig(retry, 6, 1500);
  const stellar = stellarConfig(network);
  const { attempts, delayMs } = resolveRetry(retry, ALLOWANCE_WAIT_DEFAULTS);
  const server = getServer(network, rpcUrl);
  const latestLedger = await server.getLatestLedger();
  const expirationLedger = latestLedger.sequence + 100_000;

  const args = [
    Address.fromString(signer.publicKey).toScVal(),
    Address.fromString(stellar.tokenMessengerMinter).toScVal(),
    nativeToScVal(amountRaw, { type: "i128" }),
    nativeToScVal(expirationLedger, { type: "u32" }),
  ];

  const approveTxHash = await invokeContract(stellar.usdc, "approve", args, signer, network, rpcUrl);

  // The approve tx above is confirmed (SUCCESS) by this point, but a subsequent
  // deposit_for_burn simulation can still read a stale allowance of 0 immediately
  // afterward. This is RPC read-after-write lag between the ledger closing and it
  // becoming queryable for simulation. Poll the on-chain allowance until it reflects
  // the approval (or fail with a clear error) before returning, so the two calls do not
  // proceed on disagreeing views of state.
  await waitForAllowance(signer.publicKey, stellar.tokenMessengerMinter, amountRaw, network, rpcUrl, retryConfig, signal);

  return approveTxHash;
}

export interface StellarRecipientStatus {
  /** Whether the account exists on-ledger (has been funded with at least the minimum XLM reserve). */
  exists: boolean;
  /** Whether the account holds a trustline for the USDC asset. Only meaningful when `exists` is true. */
  hasTrustline: boolean;
  /** True only when both `exists` and `hasTrustline` are true; a mint sent here would actually land. */
  ready: boolean;
}

const MISSING_TRUSTLINE_MESSAGE = "trustline entry is missing for account";

/**
 * Checks whether a Stellar account can receive USDC: it must exist on-ledger (accounts do
 * not exist until minimally funded with XLM) and hold a trustline for the USDC asset. An
 * unfunded account causes server.getAccount() to throw "Account not found"; a funded
 * account without a USDC trustline causes the balance() simulation to fail with
 * Error(Contract, #13) / "trustline entry is missing for account" rather than returning a
 * zero balance.
 */
function isAccountNotFoundError(err: unknown): boolean {
  if (err instanceof Error) {
    return /account not found/i.test(err.message) || /not found/i.test(err.message);
  }
  return false;
}

export async function checkStellarRecipientReady(
  recipient: string,
  network: Network = "mainnet",
  rpcUrl?: string,
  signal?: AbortSignal,
): Promise<StellarRecipientStatus> {
  if (signal?.aborted) {
    throw signal.reason ?? new DOMException("The operation was aborted", "AbortError");
  }
  const stellar = stellarConfig(network);
  const server = getServer(network, rpcUrl);

  let account;
  try {
    account = await server.getAccount(recipient);
  } catch (err) {
    if (signal?.aborted) {
      throw signal.reason ?? new DOMException("The operation was aborted", "AbortError");
    }
    if (isAccountNotFoundError(err)) {
      return { exists: false, hasTrustline: false, ready: false };
    }
    // Propagate transport, 5xx, or RPC outages rather than misreporting as a non-existent account
    throw err;
  }

  const contract = new Contract(stellar.usdc);
  const tx = new TransactionBuilder(account, {
    fee: BASE_FEE,
    networkPassphrase: stellar.networkPassphrase,
  })
    .addOperation(contract.call("balance", Address.fromString(recipient).toScVal()))
    .setTimeout(30)
    .build();

  const sim = await server.simulateTransaction(tx);
  if (signal?.aborted) {
    throw signal.reason ?? new DOMException("The operation was aborted", "AbortError");
  }
  if (rpc.Api.isSimulationError(sim)) {
    if (sim.error.includes(MISSING_TRUSTLINE_MESSAGE)) {
      return { exists: true, hasTrustline: false, ready: false };
    }
    throw new Error(`Failed to check Stellar recipient's USDC trustline: ${sim.error}`);
  }

  return { exists: true, hasTrustline: true, ready: true };
}

async function getUsdcAllowance(
  owner: string,
  spender: string,
  network: Network,
  rpcUrl?: string,
): Promise<bigint> {
  const stellar = stellarConfig(network);
  const server = getServer(network, rpcUrl);
  const account = await server.getAccount(owner);
  const contract = new Contract(stellar.usdc);

  const tx = new TransactionBuilder(account, {
    fee: BASE_FEE,
    networkPassphrase: stellar.networkPassphrase,
  })
    .addOperation(
      contract.call("allowance", Address.fromString(owner).toScVal(), Address.fromString(spender).toScVal()),
    )
    .setTimeout(30)
    .build();

  const sim = await server.simulateTransaction(tx);
  if (rpc.Api.isSimulationError(sim)) {
    throw new Error(`Failed to read Stellar USDC allowance: ${sim.error}`);
  }
  if (!rpc.Api.isSimulationSuccess(sim) || !sim.result) {
    return 0n;
  }
  return BigInt(scValToNative(sim.result.retval));
}

async function waitForAllowance(
  owner: string,
  spender: string,
  minimum: bigint,
  network: Network,
  attempts: number,
  delayMs: number,
  rpcUrl?: string,
  retryConfig?: { attempts: number; delayMs: number },
  signal?: AbortSignal,
): Promise<void> {
  const attempts = retryConfig?.attempts ?? 6;
  const delayMs = retryConfig?.delayMs ?? 1500;
  for (let i = 0; i < attempts; i++) {
    if (signal?.aborted) {
      throw signal.reason ?? new DOMException("The operation was aborted", "AbortError");
    }
    const allowance = await getUsdcAllowance(owner, spender, network, rpcUrl);
    if (allowance >= minimum) return;
    await sleep(delayMs, signal);
  }
  throw new Error(
    `Approved USDC allowance for ${spender} did not reach ${minimum} after ${(attempts * delayMs) / 1000}s of polling; the approval transaction confirmed but the network hasn't reflected it yet`,
  );
}

/**
 * Calls deposit_for_burn on Stellar's TokenMessengerMinter, burning USDC to be
 * minted on the destination CCTP domain.
 */
export async function burnUsdcOnStellar(params: {
  amountRaw: bigint;
  destinationDomain: number;
  mintRecipientBytes32: `0x${string}`;
  maxFeeRaw: bigint;
  minFinalityThreshold: number;
  signer: StellarSigner;
  network: Network;
  rpcUrl?: string;
  retry?: StellarRetryOptions;
  signal?: AbortSignal;
}): Promise<string> {
  if (params.signal?.aborted) {
    throw params.signal.reason ?? new DOMException("The operation was aborted", "AbortError");
  }
  const retryConfig = resolveRetryConfig(params.retry, 3, 2000);
  const stellar = stellarConfig(params.network);
  const { attempts, delayMs } = resolveRetry(params.retry, RPC_LAG_RETRY_DEFAULTS);
  const recipientBytes = Buffer.from(params.mintRecipientBytes32.slice(2), "hex");

  // Argument order per the deployed contract's interface (stellar contract info
  // interface): caller comes first, not last, as in deposit_for_burn(caller,
  // amount, destination_domain, mint_recipient, burn_token, destination_caller,
  // max_fee, min_finality_threshold). Do not reorder from memory; re-verify
  // against the contract if this signature ever needs to change.
  const args = [
    Address.fromString(params.signer.publicKey).toScVal(),
    nativeToScVal(params.amountRaw, { type: "i128" }),
    nativeToScVal(params.destinationDomain, { type: "u32" }),
    nativeToScVal(recipientBytes, { type: "bytes" }),
    Address.fromString(stellar.usdc).toScVal(),
    nativeToScVal(Buffer.alloc(32), { type: "bytes" }), // destinationCaller: unrestricted
    nativeToScVal(params.maxFeeRaw, { type: "i128" }),
    nativeToScVal(params.minFinalityThreshold, { type: "u32" }),
  ];

  // waitForAllowance() in approveUsdcOnStellar confirms on-chain state is caught up before
  // this runs, but that confirmation and this call's own getAccount()/simulation can land
  // on different RPC nodes that have not converged yet. Two symptoms share this cause: a
  // stale allowance read ("not enough allowance"), and a stale account sequence number
  // (txBadSeq) when the node serving this call's getAccount() has not seen the approve's
  // sequence bump. Both are handled by retrying: invokeContract() re-fetches the account on
  // every call, so a retry can reach a caught-up node.
  return retryOnTransientRpcLag(
    () => invokeContract(stellar.tokenMessengerMinter, "deposit_for_burn", args, params.signer, params.network, params.rpcUrl),
    retryConfig,
    params.signal,
  );
}

function isTransientRpcLagError(message: string): boolean {
  return message.includes("not enough allowance") || message.includes("txBadSeq");
}

async function retryOnTransientRpcLag(
  call: () => Promise<string>,
  retryConfig?: { attempts: number; delayMs: number },
  signal?: AbortSignal,
): Promise<string> {
  const attempts = retryConfig?.attempts ?? 3;
  const delayMs = retryConfig?.delayMs ?? 2000;
  for (let i = 0; i < attempts; i++) {
    if (signal?.aborted) {
      throw signal.reason ?? new DOMException("The operation was aborted", "AbortError");
    }
    try {
      return await call();
    } catch (err) {
      if (signal?.aborted) {
        throw signal.reason ?? new DOMException("The operation was aborted", "AbortError");
      }
      const message = err instanceof Error ? err.message : String(err);
      const isLastAttempt = i === attempts - 1;
      if (!isTransientRpcLagError(message) || isLastAttempt) {
        throw err;
      }
      await sleep(delayMs, signal);
    }
  }
  throw new Error("unreachable");
}

/**
 * Calls mint_and_forward on Stellar's CctpForwarder contract. This is the only
 * supported way to land an inbound CCTP transfer on Stellar: it verifies the
 * message and attestation, mints USDC to the forwarder, then forwards it to
 * the recipient strkey encoded in the burn message's hook data.
 */
export async function mintAndForwardOnStellar(params: {
  message: `0x${string}`;
  attestation: `0x${string}`;
  signer: StellarSigner;
  network: Network;
  rpcUrl?: string;
  signal?: AbortSignal;
}): Promise<string> {
  if (params.signal?.aborted) {
    throw params.signal.reason ?? new DOMException("The operation was aborted", "AbortError");
  }
  const stellar = stellarConfig(params.network);
  const args = [
    nativeToScVal(Buffer.from(params.message.slice(2), "hex"), { type: "bytes" }),
    nativeToScVal(Buffer.from(params.attestation.slice(2), "hex"), { type: "bytes" }),
  ];

  return invokeContract(stellar.cctpForwarder, "mint_and_forward", args, params.signer, params.network, params.rpcUrl);
}
