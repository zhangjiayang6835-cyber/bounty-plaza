#!/usr/bin/env node
// End-to-end smoke test against live Arc and Stellar testnets. Unlike the
// mocked unit tests in tests/, this exercises the real depositForBurn /
// receiveMessage / mint_and_forward calls and waits on real Iris attestations.
//
// Requires funded testnet keys (see .env.example, fund via
// https://faucet.circle.com) and a built package (`pnpm build` first), since
// this imports from dist/, not src/, so it also catches bundling regressions
// that unit tests against src/ can't see.
//
// Structured with named steps (fund/check, approve+burn, attestation wait, mint),
// per-step retry + exponential backoff for transient infrastructure-shaped failures,
// deterministic error fast-fail, tabular step summary, and recovery command formatting.

import { createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { Keypair } from "@stellar/stellar-sdk";
import {
  transfer,
  completeMint,
  resolveBurn,
  checkStellarRecipientReady,
  arcMainnetChain,
  arcTestnetChain,
  TransferError,
  AttestationNotReadyError,
  IrisRequestError,
  SubmissionTimeoutError,
  AmountPrecisionError,
} from "../dist/index.js";

const ARC_PRIVATE_KEY = process.env.ARC_PRIVATE_KEY;
const STELLAR_SECRET_KEY = process.env.STELLAR_SECRET_KEY;

// Defaults to testnet. Set NETWORK=mainnet to smoke against mainnet, which
// moves real USDC and spends real Arc gas on every case below.
const NETWORK = process.env.NETWORK === "mainnet" ? "mainnet" : "testnet";
const STELLAR_RPC_URL = process.env.STELLAR_RPC_URL;

// Amount burned per case, in USDC. Override with SMOKE_AMOUNT to test with less
// on mainnet (for example SMOKE_AMOUNT=0.10).
const SMOKE_AMOUNT = process.env.SMOKE_AMOUNT ?? "1.00";

// Which leg(s) to run, named by source chain. Set FROM=arc to run only arc -> stellar
// or FROM=stellar to run only stellar -> arc (useful for a first mainnet run that
// validates the full burn, attest, and mint path with one transfer before committing
// the second). Anything else runs both.
const FROM = process.env.FROM ?? "both";

// Retry configuration for transient infrastructure failures
const STEP_MAX_ATTEMPTS = Number(process.env.SMOKE_MAX_ATTEMPTS ?? "3");
const STEP_BASE_DELAY_MS = Number(process.env.SMOKE_BASE_DELAY_MS ?? "2000");

if (!ARC_PRIVATE_KEY || !STELLAR_SECRET_KEY) {
  console.error(
    "Missing ARC_PRIVATE_KEY and/or STELLAR_SECRET_KEY.\n" +
      "Fund testnet accounts at https://faucet.circle.com, copy .env.example to .env, " +
      "fill in both keys, then export them in your shell (or, on Node 20.6+, run with " +
      "`node --env-file=.env scripts/testnet-smoke.mjs`) before re-running `pnpm smoke`.",
  );
  process.exit(1);
}

const arcChain = NETWORK === "mainnet" ? arcMainnetChain : arcTestnetChain;
const arcAccount = privateKeyToAccount(ARC_PRIVATE_KEY);
const arcSigner = {
  walletClient: createWalletClient({ account: arcAccount, chain: arcChain, transport: http() }),
};

const stellarKeypair = Keypair.fromSecret(STELLAR_SECRET_KEY);
const stellarSigner = { publicKey: stellarKeypair.publicKey(), keypair: stellarKeypair };

/** @type {Array<{ caseName: string; step: string; status: "PASS" | "FAIL"; durationMs: number; attempts: number; detail?: string }>} */
const stepSummary = [];
let failures = 0;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Distinguishes transient infrastructure / finality-window errors from deterministic
 * validation or balance failures that should fail immediately without retry.
 */
function isDeterministicError(error) {
  if (!error) return false;
  if (error instanceof AmountPrecisionError) return true;
  const message = error instanceof Error ? error.message : String(error);
  const deterministicPatterns = [
    /invalid.*address/i,
    /bad.*address/i,
    /more precision/i,
    /destination cannot preserve/i,
    /does not exist yet/i,
    /no USDC trustline/i,
    /insufficient funds/i,
    /exceeds balance/i,
    /underfunded/i,
    /Invalid USDC amount/i,
  ];
  return deterministicPatterns.some((re) => re.test(message));
}

function isTransientError(error) {
  if (!error || isDeterministicError(error)) return false;

  if (
    error instanceof AttestationNotReadyError ||
    error instanceof SubmissionTimeoutError ||
    (error instanceof TransferError && error.code === "ATTESTATION_NOT_READY")
  ) {
    return true;
  }

  const status = Number(
    error?.status ?? error?.statusCode ?? error?.cause?.status ?? error?.cause?.statusCode,
  );
  if ([429, 500, 502, 503, 504].includes(status)) {
    return true;
  }

  const code = String(error?.code ?? error?.cause?.code ?? "");
  const transientCodes = new Set([
    "ETIMEDOUT",
    "ECONNRESET",
    "ECONNREFUSED",
    "EAI_AGAIN",
    "ENETUNREACH",
    "UND_ERR_CONNECT_TIMEOUT",
    "UND_ERR_SOCKET",
  ]);
  if (transientCodes.has(code)) {
    return true;
  }

  const message = error instanceof Error ? error.message : String(error);
  const transientPatterns = [
    /\b(?:429|500|502|503|504)\b/,
    /rate limit/i,
    /too many requests/i,
    /temporarily unavailable/i,
    /gateway timeout/i,
    /server error/i,
    /timeout/i,
    /timed out/i,
    /connection reset/i,
    /fetch failed/i,
    /network/i,
    /txBadSeq/i,
    /RPC.*error/i,
  ];
  return transientPatterns.some((re) => re.test(message));
}

/**
 * Runs a named step with per-step retry and exponential backoff for transient errors.
 */
async function runStep(caseName, stepName, fn, options = {}) {
  const maxAttempts = options.maxAttempts ?? STEP_MAX_ATTEMPTS;
  const baseDelayMs = options.baseDelayMs ?? STEP_BASE_DELAY_MS;
  const allowRetry = options.allowRetry ?? ((err) => isTransientError(err));

  const start = Date.now();
  let attempts = 0;

  while (attempts < maxAttempts) {
    attempts += 1;
    try {
      const result = await fn();
      const durationMs = Date.now() - start;
      stepSummary.push({ caseName, step: stepName, status: "PASS", durationMs, attempts });
      console.log(`  [PASS] ${stepName} (${durationMs}ms, attempt ${attempts}/${maxAttempts})`);
      return result;
    } catch (error) {
      const canRetry = attempts < maxAttempts && allowRetry(error);
      const msg = error instanceof Error ? error.message : String(error);

      if (!canRetry) {
        const durationMs = Date.now() - start;
        stepSummary.push({
          caseName,
          step: stepName,
          status: "FAIL",
          durationMs,
          attempts,
          detail: msg,
        });
        console.error(`  [FAIL] ${stepName} (${durationMs}ms, attempt ${attempts}/${maxAttempts}): ${msg}`);
        throw error;
      }

      const delayMs = baseDelayMs * 2 ** (attempts - 1);
      console.warn(
        `  [retry] ${stepName} transient error on attempt ${attempts}/${maxAttempts}: ${msg} — retrying in ${delayMs}ms...`,
      );
      await sleep(delayMs);
    }
  }
}

function printRecoveryInstructions(params, destinationSignerName, burnTxHash, attestationHash) {
  console.error("\n  ==================== RECOVERY INSTRUCTIONS ====================");
  console.error("  A burn succeeded on-chain, but a subsequent step encountered an error.");
  console.error(`  burnTxHash: ${burnTxHash}`);
  if (attestationHash) {
    console.error(`  attestationHash: ${attestationHash}`);
  }
  console.error("  Funds are safe and can be claimed with completeMint():\n");
  console.error(
    "  await completeMint(" +
      JSON.stringify(
        {
          from: params.from,
          to: params.to,
          burnTxHash,
          signer: `<${destinationSignerName}>`,
          network: params.network,
          options: {
            stellarRpcUrl: STELLAR_RPC_URL,
          },
        },
        null,
        2,
      ) +
      ")\n",
  );
  console.error("  ===============================================================");
}

async function runCase(name, params, destinationSigner, destinationSignerName) {
  console.log(`\n--- ${name} ---`);
  const caseStart = Date.now();
  let burnTxHash;
  let attestationHash;

  try {
    // Step 1: fund/check
    await runStep(name, "fund/check", async () => {
      if (params.from === "stellar") {
        const senderStatus = await checkStellarRecipientReady(
          stellarKeypair.publicKey(),
          params.network,
          STELLAR_RPC_URL,
        );
        if (!senderStatus.exists) {
          throw new Error(
            `Stellar sender account ${stellarKeypair.publicKey()} does not exist yet. Fund it with XLM first.`,
          );
        }
        if (!senderStatus.hasTrustline) {
          throw new Error(
            `Stellar sender account ${stellarKeypair.publicKey()} has no USDC trustline.`,
          );
        }
      }

      if (params.to === "stellar") {
        const status = await checkStellarRecipientReady(
          params.recipient,
          params.network,
          STELLAR_RPC_URL,
        );
        if (!status.exists) {
          throw new Error(
            `Stellar recipient ${params.recipient} does not exist yet. Fund it with XLM first.`,
          );
        }
        if (!status.hasTrustline) {
          throw new Error(
            `Stellar recipient ${params.recipient} has no USDC trustline.`,
          );
        }
      } else if (params.to === "arc") {
        if (!/^0x[a-fA-F0-9]{40}$/.test(params.recipient)) {
          throw new Error(`Invalid Arc/EVM recipient address: ${params.recipient}`);
        }
      }
    });

    // Step 2: approve+burn
    // Note: Once burnTxHash exists, allowRetry returns false so transfer() is never
    // retried (which would double-burn).
    const burnOutcome = await runStep(
      name,
      "approve+burn",
      async () => {
        try {
          const res = await transfer({
            ...params,
            options: {
              ...params.options,
              destinationSigner: undefined,
              pollInterval: 1000,
              pollTimeout: 3000,
            },
          });
          burnTxHash = res.burnTxHash;
          if (res.attestationHash) {
            attestationHash = res.attestationHash;
          }
          return res;
        } catch (error) {
          if (error instanceof TransferError && error.burnTxHash) {
            burnTxHash = error.burnTxHash;
            if (error.attestationHash) {
              attestationHash = error.attestationHash;
            }
            return {
              status: "pending",
              burnTxHash: error.burnTxHash,
              attestationHash: error.attestationHash,
            };
          }
          throw error;
        }
      },
      {
        allowRetry: (err) => !burnTxHash && isTransientError(err),
      },
    );

    burnTxHash = burnOutcome.burnTxHash;
    if (burnOutcome.attestationHash) {
      attestationHash = burnOutcome.attestationHash;
    }

    // Step 3: attestation wait
    await runStep(
      name,
      "attestation wait",
      async () => {
        if (attestationHash) {
          return { attestation: attestationHash };
        }
        const resolved = await resolveBurn({
          from: params.from,
          burnTxHash,
          network: params.network,
        });
        if (!resolved.attestation) {
          throw new AttestationNotReadyError(
            `Iris has indexed burn ${burnTxHash} but attestation signature is still pending`,
            burnTxHash,
          );
        }
        attestationHash = resolved.attestation;
        return resolved;
      },
      {
        maxAttempts: 15,
        baseDelayMs: 3000,
      },
    );

    // Step 4: mint
    const mintResult = await runStep(
      name,
      "mint",
      async () => {
        const completed = await completeMint({
          from: params.from,
          to: params.to,
          burnTxHash,
          signer: destinationSigner,
          network: params.network,
          options: {
            stellarRpcUrl: STELLAR_RPC_URL,
          },
        });
        if (!completed.mintTxHash) {
          throw new Error("expected a non-empty mintTxHash from completeMint");
        }
        return completed;
      },
      {
        maxAttempts: 3,
        baseDelayMs: 2500,
      },
    );

    attestationHash = mintResult.attestationHash ?? attestationHash;
    console.log(
      JSON.stringify(
        {
          status: "success",
          from: params.from,
          to: params.to,
          burnTxHash,
          attestationHash,
          mintTxHash: mintResult.mintTxHash,
          durationMs: Date.now() - caseStart,
        },
        null,
        2,
      ),
    );
    console.log(`PASS ${name} (${Date.now() - caseStart}ms)`);
  } catch (error) {
    failures += 1;
    console.error(`FAIL ${name}:`, error instanceof Error ? error.message : error);
    if (burnTxHash) {
      printRecoveryInstructions(params, destinationSignerName, burnTxHash, attestationHash);
    }
  }
}

function printStepSummary() {
  console.log("\n==================== Smoke Test Step Summary ====================");
  let passed = 0;
  let failed = 0;

  for (const row of stepSummary) {
    const attemptStr = `${row.attempts} attempt${row.attempts === 1 ? "" : "s"}`;
    const detail = row.detail ? ` — ${row.detail}` : "";
    console.log(
      `[${row.status}] ${row.caseName} :: ${row.step} (${row.durationMs}ms, ${attemptStr})${detail}`,
    );
    if (row.status === "PASS") passed++;
    else failed++;
  }

  console.log("=================================================================");
  console.log(`Total: ${passed} passed, ${failed} failed (${stepSummary.length} steps total)`);
}

console.log(`Running smoke cases against ${NETWORK}.`);
if (NETWORK === "mainnet") {
  console.log("WARNING: mainnet moves real USDC and spends real Arc gas.");
}

if (FROM === "arc" || FROM === "both") {
  await runCase(
    "arc -> stellar (standard)",
    {
      from: "arc",
      to: "stellar",
      amount: SMOKE_AMOUNT,
      recipient: stellarKeypair.publicKey(),
      speed: "standard",
      signer: arcSigner,
      network: NETWORK,
      options: { stellarRpcUrl: STELLAR_RPC_URL },
    },
    stellarSigner,
    "stellarSigner",
  );
}

if (FROM === "stellar" || FROM === "both") {
  await runCase(
    "stellar -> arc (standard)",
    {
      from: "stellar",
      to: "arc",
      amount: SMOKE_AMOUNT,
      recipient: arcAccount.address,
      speed: "standard",
      signer: stellarSigner,
      network: NETWORK,
      options: { stellarRpcUrl: STELLAR_RPC_URL },
    },
    arcSigner,
    "arcSigner",
  );
}

printStepSummary();

if (failures > 0) {
  console.error(`\n${failures} smoke test case(s) failed.`);
  process.exit(1);
}
console.log("\nAll smoke test cases passed.");
