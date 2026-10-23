import { describe, it, expect, vi, beforeEach } from "vitest";
import type { TransferProgressEvent } from "../src/index.js";

const getUsdcAllowanceOnArc = vi.fn();
const approveUsdcOnArc = vi.fn();
const burnUsdcOnArc = vi.fn();
const burnUsdcOnArcWithStellarForward = vi.fn();
const receiveMessageOnArc = vi.fn();
const approveUsdcOnStellar = vi.fn();
const burnUsdcOnStellar = vi.fn();
const mintAndForwardOnStellar = vi.fn();
const checkStellarRecipientReady = vi.fn();
const fetchFastTransferFeeBps = vi.fn();
const pollForAttestation = vi.fn();
const getAttestation = vi.fn();

vi.mock("../src/chains/arc.js", () => ({
  getUsdcAllowanceOnArc: (...args: unknown[]) => getUsdcAllowanceOnArc(...args),
  approveUsdcOnArc: (...args: unknown[]) => approveUsdcOnArc(...args),
  burnUsdcOnArc: (...args: unknown[]) => burnUsdcOnArc(...args),
  burnUsdcOnArcWithStellarForward: (...args: unknown[]) => burnUsdcOnArcWithStellarForward(...args),
  receiveMessageOnArc: (...args: unknown[]) => receiveMessageOnArc(...args),
}));

vi.mock("../src/chains/stellar.js", () => ({
  approveUsdcOnStellar: (...args: unknown[]) => approveUsdcOnStellar(...args),
  burnUsdcOnStellar: (...args: unknown[]) => burnUsdcOnStellar(...args),
  mintAndForwardOnStellar: (...args: unknown[]) => mintAndForwardOnStellar(...args),
  checkStellarRecipientReady: (...args: unknown[]) => checkStellarRecipientReady(...args),
}));

vi.mock("../src/iris/poll.js", () => ({
  fetchFastTransferFeeBps: (...args: unknown[]) => fetchFastTransferFeeBps(...args),
  pollForAttestation: (...args: unknown[]) => pollForAttestation(...args),
  getAttestation: (...args: unknown[]) => getAttestation(...args),
}));

const { transfer, completeMint } = await import("../src/transfer.js");
const { TransferError, SubmissionTimeoutError } = await import("../src/errors.js");
const { encodeStellarForwardHook } = await import("../src/utils/encoding.js");

const FORWARD_RECIPIENT = "GCY3PLGZQZWVKQELW7GCHQVLVZGRMGI5R4HODX6QZM7ETJSPHBFVJPY2";

function buildBurnMessage(options: { forwardRecipient?: string } = {}): `0x${string}` {
  const header = Buffer.alloc(148);
  header.writeUInt32BE(1, 0);
  header.writeUInt32BE(26, 4);
  header.writeUInt32BE(27, 8);

  const body = Buffer.alloc(228);
  body.writeUInt32BE(1, 0);

  const hook =
    options.forwardRecipient === undefined
      ? Buffer.alloc(0)
      : Buffer.from(encodeStellarForwardHook(options.forwardRecipient).slice(2), "hex");

  return `0x${Buffer.concat([header, body, hook]).toString("hex")}`;
}

const arcSigner = { walletClient: { account: { address: "0x1234567890123456789012345678901234567890" } } } as any;
const stellarSigner = { publicKey: "GABCD" } as any;

beforeEach(() => {
  vi.clearAllMocks();
  getUsdcAllowanceOnArc.mockResolvedValue(0n);
  approveUsdcOnArc.mockResolvedValue("0xapprovehash");
  burnUsdcOnArcWithStellarForward.mockResolvedValue("0xburnhookhash");
  approveUsdcOnStellar.mockResolvedValue("stellarapprovehash");
  burnUsdcOnStellar.mockResolvedValue("stellarburnhash");
  checkStellarRecipientReady.mockResolvedValue({ exists: true, hasTrustline: true, ready: true });
  pollForAttestation.mockResolvedValue({
    message: buildBurnMessage({ forwardRecipient: FORWARD_RECIPIENT }),
    attestation: "0xattestation",
  });
  getAttestation.mockResolvedValue({
    message: buildBurnMessage({ forwardRecipient: FORWARD_RECIPIENT }),
    attestation: "0xattestation",
  });
  receiveMessageOnArc.mockResolvedValue("0xminthash");
  mintAndForwardOnStellar.mockResolvedValue("stellarminthash");
});

describe("transfer() structured progress callbacks (Issue #6)", () => {
  it("emits expected 7 stages in order with burnTxHash present from burn-submitted onward (Arc -> Stellar)", async () => {
    const events: TransferProgressEvent[] = [];
    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "100",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: {
        destinationSigner: stellarSigner,
        onProgress: (e) => events.push(e),
      },
    });

    expect(result.status).toBe("success");
    expect(result.burnTxHash).toBe("0xburnhookhash");

    const stages = events.map((e) => e.stage);
    expect(stages).toEqual([
      "recipient-check",
      "approve",
      "burn-submitted",
      "burn-confirmed",
      "attestation",
      "mint-submitted",
      "mint-confirmed",
    ]);

    // All events carry timestamps
    for (const e of events) {
      expect(e.timestamp).toBeGreaterThan(0);
    }

    // burnTxHash present from burn-submitted onward
    const burnSubmitted = events.find((e) => e.stage === "burn-submitted");
    expect(burnSubmitted && "burnTxHash" in burnSubmitted && burnSubmitted.burnTxHash).toBe("0xburnhookhash");

    const burnConfirmed = events.find((e) => e.stage === "burn-confirmed");
    expect(burnConfirmed && "burnTxHash" in burnConfirmed && burnConfirmed.burnTxHash).toBe("0xburnhookhash");

    const attestation = events.find((e) => e.stage === "attestation");
    expect(attestation && "burnTxHash" in attestation && attestation.burnTxHash).toBe("0xburnhookhash");

    const mintSubmitted = events.find((e) => e.stage === "mint-submitted");
    expect(mintSubmitted && "burnTxHash" in mintSubmitted && mintSubmitted.burnTxHash).toBe("0xburnhookhash");
    expect(mintSubmitted && "attestationHash" in mintSubmitted && mintSubmitted.attestationHash).toBe("0xattestation");

    const mintConfirmed = events.find((e) => e.stage === "mint-confirmed");
    expect(mintConfirmed && "burnTxHash" in mintConfirmed && mintConfirmed.burnTxHash).toBe("0xburnhookhash");
    expect(mintConfirmed && "attestationHash" in mintConfirmed && mintConfirmed.attestationHash).toBe("0xattestation");
    expect(mintConfirmed && "mintTxHash" in mintConfirmed && mintConfirmed.mintTxHash).toBe("stellarminthash");
  });

  it("emits expected stages for Stellar -> Arc transfer with burnTxHash present from burn-submitted onward", async () => {
    const events: TransferProgressEvent[] = [];
    const result = await transfer({
      from: "stellar",
      to: "arc",
      amount: "50",
      recipient: "0x1111111111111111111111111111111111111111",
      speed: "standard",
      signer: stellarSigner,
      options: {
        destinationSigner: arcSigner,
        onProgress: (e) => events.push(e),
      },
    });

    expect(result.status).toBe("success");
    expect(result.burnTxHash).toBe("stellarburnhash");

    const stages = events.map((e) => e.stage);
    expect(stages).toEqual([
      "approve",
      "burn-submitted",
      "burn-confirmed",
      "attestation",
      "mint-submitted",
      "mint-confirmed",
    ]);

    expect((events[1] as any).burnTxHash).toBe("stellarburnhash");
    expect((events[2] as any).burnTxHash).toBe("stellarburnhash");
    expect((events[3] as any).burnTxHash).toBe("stellarburnhash");
    expect((events[4] as any).burnTxHash).toBe("stellarburnhash");
    expect((events[5] as any).mintTxHash).toBe("0xminthash");
  });

  it("emits up to attestation when destinationSigner is omitted (pending transfer)", async () => {
    const events: TransferProgressEvent[] = [];
    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "25",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: {
        onProgress: (e) => events.push(e),
      },
    });

    expect(result.status).toBe("pending");
    const stages = events.map((e) => e.stage);
    expect(stages).toEqual([
      "recipient-check",
      "approve",
      "burn-submitted",
      "burn-confirmed",
      "attestation",
    ]);
  });

  it("swallows exceptions thrown by onProgress without breaking or altering the transfer", async () => {
    const consoleErrorSpy = vi.spyOn(console, "error");
    const throwsCallback = vi.fn().mockImplementation(() => {
      throw new Error("Observer crashed!");
    });

    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "100",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: {
        destinationSigner: stellarSigner,
        onProgress: throwsCallback,
      },
    });

    expect(result.status).toBe("success");
    expect(result.burnTxHash).toBe("0xburnhookhash");
    expect(throwsCallback).toHaveBeenCalledTimes(7);
    // Console error was not called
    expect(consoleErrorSpy).not.toHaveBeenCalled();
    consoleErrorSpy.mockRestore();
  });

  it("swallows errors even when onProgress throws non-Error primitives", async () => {
    const throwsString = vi.fn().mockImplementation(() => {
      throw "fatal string rejection";
    });

    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: {
        onProgress: throwsString,
      },
    });

    expect(result.status).toBe("pending");
    expect(throwsString).toHaveBeenCalledTimes(5);
  });

  it("preserves underlying transfer error when burn confirmation times out and emits burn-submitted with hash", async () => {
    burnUsdcOnArcWithStellarForward.mockRejectedValue(
      new SubmissionTimeoutError("Confirmation timed out", "0xtimeouthash"),
    );

    const events: TransferProgressEvent[] = [];
    const promise = transfer({
      from: "arc",
      to: "stellar",
      amount: "100",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: {
        onProgress: (e) => events.push(e),
      },
    });

    await expect(promise).rejects.toThrow(TransferError);
    await expect(promise).rejects.toMatchObject({
      burnTxHash: "0xtimeouthash",
    });

    const stages = events.map((e) => e.stage);
    expect(stages).toEqual(["recipient-check", "approve", "burn-submitted"]);
    expect((events[2] as any).burnTxHash).toBe("0xtimeouthash");
  });

  it("does not change any behavior or emit anything when onProgress is omitted", async () => {
    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "100",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: {
        destinationSigner: stellarSigner,
      },
    });

    expect(result.status).toBe("success");
    expect(result.burnTxHash).toBe("0xburnhookhash");
  });

  it("completeMint() emits progress events safely and supports observer throws", async () => {
    const events: TransferProgressEvent[] = [];
    const result = await completeMint({
      from: "arc",
      to: "stellar",
      burnTxHash: "0xburnhookhash",
      signer: stellarSigner,
      options: {
        onProgress: (e) => events.push(e),
      },
    });

    expect(result.mintTxHash).toBe("stellarminthash");
    expect(result.attestationHash).toBe("0xattestation");

    const stages = events.map((e) => e.stage);
    expect(stages).toEqual([
      "attestation",
      "recipient-check",
      "mint-submitted",
      "mint-confirmed",
    ]);

    // Test observer throwing in completeMint
    const throwsCallback = vi.fn().mockImplementation(() => {
      throw new Error("completeMint observer error");
    });
    const result2 = await completeMint({
      from: "arc",
      to: "stellar",
      burnTxHash: "0xburnhookhash",
      signer: stellarSigner,
      options: {
        onProgress: throwsCallback,
      },
    });
    expect(result2.mintTxHash).toBe("stellarminthash");
  });
});
