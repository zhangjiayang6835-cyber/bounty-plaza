import { describe, it, expect, vi, beforeEach } from "vitest";

const approveUsdcOnArc = vi.fn();
const burnUsdcOnArc = vi.fn();
const burnUsdcOnArcWithStellarForward = vi.fn();
const receiveMessageOnArc = vi.fn();
const getUsdcAllowanceOnArc = vi.fn();
const approveUsdcOnStellar = vi.fn();
const burnUsdcOnStellar = vi.fn();
const mintAndForwardOnStellar = vi.fn();
const checkStellarRecipientReady = vi.fn();
const fetchFastTransferFeeBps = vi.fn();
const pollForAttestation = vi.fn();
const getAttestation = vi.fn();

vi.mock("../src/chains/arc.js", () => ({
  approveUsdcOnArc: (...args: unknown[]) => approveUsdcOnArc(...args),
  burnUsdcOnArc: (...args: unknown[]) => burnUsdcOnArc(...args),
  burnUsdcOnArcWithStellarForward: (...args: unknown[]) => burnUsdcOnArcWithStellarForward(...args),
  receiveMessageOnArc: (...args: unknown[]) => receiveMessageOnArc(...args),
  getUsdcAllowanceOnArc: (...args: unknown[]) => getUsdcAllowanceOnArc(...args),
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

const { transfer, completeMint, resolveBurn } = await import("../src/transfer.js");
const { TransferError, SubmissionTimeoutError, AttestationNotReadyError, AmountPrecisionError } = await import(
  "../src/errors.js"
);
const { encodeStellarForwardHook } = await import("../src/utils/encoding.js");

const FORWARD_RECIPIENT = "GCY3PLGZQZWVKQELW7GCHQVLVZGRMGI5R4HODX6QZM7ETJSPHBFVJPY2";

/**
 * Builds a CCTP V2 burn message with the offsets from Circle's MessageV2/BurnMessageV2
 * reference contracts. Only the fields the SDK reads are populated; the rest are zero,
 * which is what a real message carries for an unfilled fee and expiry.
 */
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

const arcSigner = { walletClient: {} } as any;
const stellarSigner = { publicKey: "GABCD" } as any;

beforeEach(() => {
  vi.clearAllMocks();
  getUsdcAllowanceOnArc.mockResolvedValue(0n);
  approveUsdcOnArc.mockResolvedValue("0xapprovehash");
  burnUsdcOnArc.mockResolvedValue("0xburnhash");
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

describe("transfer (Arc -> Stellar)", () => {
  it("rejects source precision the Arc destination cannot preserve before approval", async () => {
    const error = await transfer({
      from: "stellar",
      to: "arc",
      amount: "1.1234567",
      recipient: "0x1111111111111111111111111111111111111111",
      speed: "standard",
      signer: stellarSigner,
    }).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(AmountPrecisionError);
    expect(error).toMatchObject({
      amount: "1.1234567",
      precision: 7,
      supportedDecimals: 6,
      destination: "arc",
    });
    expect(approveUsdcOnStellar).not.toHaveBeenCalled();
    expect(burnUsdcOnStellar).not.toHaveBeenCalled();
  });

  it("accepts trailing-zero precision for a Stellar-to-Arc transfer", async () => {
    const result = await transfer({
      from: "stellar",
      to: "arc",
      amount: "1.1230000",
      recipient: "0x1111111111111111111111111111111111111111",
      speed: "standard",
      signer: stellarSigner,
    });

    expect(result.status).toBe("pending");
    expect(approveUsdcOnStellar).toHaveBeenCalledWith(11_230_000n, stellarSigner, "mainnet", undefined);
    expect(burnUsdcOnStellar).toHaveBeenCalledTimes(1);
  });

  it("accepts six-decimal Arc amounts when Stellar is the destination", async () => {
    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "1.123456",
      recipient: FORWARD_RECIPIENT,
      speed: "standard",
      signer: arcSigner,
    });

    expect(result.status).toBe("pending");
    expect(approveUsdcOnArc).toHaveBeenCalledWith(arcSigner, 1_123_456n, "mainnet", undefined);
    expect(burnUsdcOnArcWithStellarForward).toHaveBeenCalledWith(
      expect.objectContaining({ amountRaw: 1_123_456n }),
    );
  });

  it("routes the burn through depositForBurnWithHook and mints via CctpForwarder", async () => {
    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: { destinationSigner: stellarSigner },
    });

    expect(burnUsdcOnArcWithStellarForward).toHaveBeenCalledTimes(1);
    expect(burnUsdcOnArc).not.toHaveBeenCalled();
    expect(mintAndForwardOnStellar).toHaveBeenCalledTimes(1);
    expect(receiveMessageOnArc).not.toHaveBeenCalled();

    expect(result.status).toBe("success");
    expect(result.burnTxHash).toBe("0xburnhookhash");
    expect(result.mintTxHash).toBe("stellarminthash");
    expect(result.attestationHash).toBe("0xattestation");
  });

  it("returns pending status with no mint tx hash when no destinationSigner is given", async () => {
    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
    });

    expect(result.status).toBe("pending");
    expect(result.mintTxHash).toBe("");
    expect(mintAndForwardOnStellar).not.toHaveBeenCalled();
  });

  it("converts a burn-step SubmissionTimeoutError into a recoverable TransferError", async () => {
    burnUsdcOnArcWithStellarForward.mockRejectedValueOnce(
      new SubmissionTimeoutError("Timed out waiting for receipt", "0xburnhookhash"),
    );

    await expect(
      transfer({
        from: "arc",
        to: "stellar",
        amount: "10",
        recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
        speed: "standard",
        signer: arcSigner,
        options: { destinationSigner: stellarSigner },
      }),
    ).rejects.toMatchObject({
      burnTxHash: "0xburnhookhash",
    });
    expect(pollForAttestation).not.toHaveBeenCalled();
  });

  it("rethrows a TransferError carrying burnTxHash when the mint step fails", async () => {
    mintAndForwardOnStellar.mockRejectedValueOnce(new Error("Account not found: GABCD"));

    await expect(
      transfer({
        from: "arc",
        to: "stellar",
        amount: "10",
        recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
        speed: "standard",
        signer: arcSigner,
        options: { destinationSigner: stellarSigner },
      }),
    ).rejects.toMatchObject({
      burnTxHash: "0xburnhookhash",
      attestationHash: "0xattestation",
      message: "Account not found: GABCD",
    });
  });

  it("rethrows a TransferError carrying burnTxHash when attestation polling fails", async () => {
    pollForAttestation.mockRejectedValueOnce(new Error("Timed out after 300000ms"));

    let caught: unknown;
    try {
      await transfer({
        from: "arc",
        to: "stellar",
        amount: "10",
        recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
        speed: "standard",
        signer: arcSigner,
        options: { destinationSigner: stellarSigner },
      });
    } catch (err) {
      caught = err;
    }

    expect(caught).toBeInstanceOf(TransferError);
    expect((caught as InstanceType<typeof TransferError>).burnTxHash).toBe("0xburnhookhash");
    expect((caught as InstanceType<typeof TransferError>).attestationHash).toBeUndefined();
  });

  it("checks Stellar recipient readiness before approving or burning anything on Arc", async () => {
    await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: { destinationSigner: stellarSigner },
    });

    expect(checkStellarRecipientReady).toHaveBeenCalledWith(
      "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      "mainnet",
      undefined,
    );
  });

  it("refuses to burn toward a Stellar recipient that doesn't exist yet", async () => {
    checkStellarRecipientReady.mockResolvedValue({ exists: false, hasTrustline: false, ready: false });

    await expect(
      transfer({
        from: "arc",
        to: "stellar",
        amount: "10",
        recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
        speed: "standard",
        signer: arcSigner,
        options: { destinationSigner: stellarSigner },
      }),
    ).rejects.toThrow(/does not exist yet/);

    expect(approveUsdcOnArc).not.toHaveBeenCalled();
    expect(burnUsdcOnArcWithStellarForward).not.toHaveBeenCalled();
  });

  it("refuses to burn toward a Stellar recipient with no USDC trustline", async () => {
    checkStellarRecipientReady.mockResolvedValue({ exists: true, hasTrustline: false, ready: false });

    await expect(
      transfer({
        from: "arc",
        to: "stellar",
        amount: "10",
        recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
        speed: "standard",
        signer: arcSigner,
        options: { destinationSigner: stellarSigner },
      }),
    ).rejects.toThrow(/no USDC trustline/);

    expect(approveUsdcOnArc).not.toHaveBeenCalled();
    expect(burnUsdcOnArcWithStellarForward).not.toHaveBeenCalled();
  });

  it("can be finished later via completeMint using the returned burnTxHash", async () => {
    const pending = await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
    });

    const completed = await completeMint({
      from: "arc",
      to: "stellar",
      burnTxHash: pending.burnTxHash,
      signer: stellarSigner,
    });

    expect(mintAndForwardOnStellar).toHaveBeenCalledTimes(1);
    expect(completed.mintTxHash).toBe("stellarminthash");
    expect(completed.attestationHash).toBe("0xattestation");
  });

  it("skips approveUsdcOnArc when existing allowance covers the burn amount", async () => {
    getUsdcAllowanceOnArc.mockResolvedValue(10_000_000n);

    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: { destinationSigner: stellarSigner },
    });

    expect(getUsdcAllowanceOnArc).toHaveBeenCalledTimes(1);
    expect(approveUsdcOnArc).not.toHaveBeenCalled();
    expect(burnUsdcOnArcWithStellarForward).toHaveBeenCalledTimes(1);
    expect(result.status).toBe("success");
  });

  it("calls approveUsdcOnArc when existing allowance is less than burn amount", async () => {
    getUsdcAllowanceOnArc.mockResolvedValue(9_999_999n);

    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: { destinationSigner: stellarSigner },
    });

    expect(getUsdcAllowanceOnArc).toHaveBeenCalledTimes(1);
    expect(approveUsdcOnArc).toHaveBeenCalledTimes(1);
    expect(approveUsdcOnArc).toHaveBeenCalledWith(arcSigner, 10_000_000n, "mainnet", undefined);
    expect(burnUsdcOnArcWithStellarForward).toHaveBeenCalledTimes(1);
    expect(result.status).toBe("success");
  });

  it("fails closed when getUsdcAllowanceOnArc rejects", async () => {
    getUsdcAllowanceOnArc.mockRejectedValue(new Error("RPC failure reading allowance"));

    await expect(
      transfer({
        from: "arc",
        to: "stellar",
        amount: "10",
        recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
        speed: "standard",
        signer: arcSigner,
        options: { destinationSigner: stellarSigner },
      }),
    ).rejects.toThrow("RPC failure reading allowance");

    expect(approveUsdcOnArc).not.toHaveBeenCalled();
    expect(burnUsdcOnArcWithStellarForward).not.toHaveBeenCalled();
  });
});

describe("transfer (Stellar -> Arc)", () => {
  it("burns via TokenMessengerMinter and mints via receiveMessage", async () => {
    const result = await transfer({
      from: "stellar",
      to: "arc",
      amount: "25",
      recipient: "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
      speed: "standard",
      signer: stellarSigner,
      options: { destinationSigner: arcSigner },
    });

    expect(burnUsdcOnStellar).toHaveBeenCalledTimes(1);
    expect(receiveMessageOnArc).toHaveBeenCalledTimes(1);
    expect(result.burnTxHash).toBe("stellarburnhash");
    expect(result.mintTxHash).toBe("0xminthash");
  });
});

describe("transfer network selection", () => {
  it("defaults to mainnet: burns with network mainnet and polls the production Iris API", async () => {
    await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: { destinationSigner: stellarSigner },
    });

    expect(burnUsdcOnArcWithStellarForward.mock.calls[0]?.[0].network).toBe("mainnet");
    expect(mintAndForwardOnStellar.mock.calls[0]?.[0].network).toBe("mainnet");
    expect(pollForAttestation.mock.calls[0]?.[0].useSandbox).toBe(false);
  });

  it("routes explicit testnet to the testnet config and the sandbox Iris API", async () => {
    await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      network: "testnet",
      options: { destinationSigner: stellarSigner },
    });

    expect(checkStellarRecipientReady).toHaveBeenCalledWith(
      "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      "testnet",
      undefined,
    );
    expect(burnUsdcOnArcWithStellarForward.mock.calls[0]?.[0].network).toBe("testnet");
    expect(pollForAttestation.mock.calls[0]?.[0].useSandbox).toBe(true);
  });

  it("threads a Stellar RPC override into the recipient check and mint call", async () => {
    await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: { destinationSigner: stellarSigner, stellarRpcUrl: "https://my-soroban.example/rpc" },
    });

    expect(checkStellarRecipientReady).toHaveBeenCalledWith(
      "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      "mainnet",
      "https://my-soroban.example/rpc",
    );
    expect(mintAndForwardOnStellar.mock.calls[0]?.[0].rpcUrl).toBe("https://my-soroban.example/rpc");
  });

  it("threads an Arc RPC override into the approve and burn calls", async () => {
    await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: { destinationSigner: stellarSigner, arcRpcUrl: "https://my-arc.example/rpc" },
    });

    expect(approveUsdcOnArc.mock.calls[0]?.[3]).toBe("https://my-arc.example/rpc");
    expect(burnUsdcOnArcWithStellarForward.mock.calls[0]?.[0].rpcUrl).toBe(
      "https://my-arc.example/rpc",
    );
  });

  it("threads an Arc RPC override into receiveMessage on an Arc destination", async () => {
    await completeMint({
      from: "stellar",
      to: "arc",
      burnTxHash: "0xburnhash",
      signer: arcSigner,
      options: { arcRpcUrl: "https://my-arc.example/rpc" },
    });

    expect(receiveMessageOnArc.mock.calls[0]?.[0].rpcUrl).toBe("https://my-arc.example/rpc");
  });

  it("leaves the Arc RPC override undefined so the public endpoint is used by default", async () => {
    await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: { destinationSigner: stellarSigner },
    });

    expect(approveUsdcOnArc.mock.calls[0]?.[3]).toBeUndefined();
    expect(burnUsdcOnArcWithStellarForward.mock.calls[0]?.[0].rpcUrl).toBeUndefined();
  });

  it("threads stellarRetryAttempts and stellarRetryDelayMs into approveUsdcOnStellar and burnUsdcOnStellar", async () => {
    await transfer({
      from: "stellar",
      to: "arc",
      amount: "10",
      recipient: "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
      speed: "standard",
      signer: stellarSigner,
      options: {
        destinationSigner: arcSigner,
        stellarRetryAttempts: 5,
        stellarRetryDelayMs: 500,
      },
    });

    expect(approveUsdcOnStellar.mock.calls[0]?.[4]).toEqual({ attempts: 5, delayMs: 500 });
    expect(burnUsdcOnStellar.mock.calls[0]?.[0].retry).toEqual({ attempts: 5, delayMs: 500 });
  });

  it("completeMint defaults to mainnet and polls the production Iris API", async () => {
    await completeMint({
      from: "arc",
      to: "stellar",
      burnTxHash: "0xburnhookhash",
      signer: stellarSigner,
    });

    expect(pollForAttestation.mock.calls[0]?.[0].useSandbox).toBe(false);
    expect(mintAndForwardOnStellar.mock.calls[0]?.[0].network).toBe("mainnet");
  });
});

describe("attestation-not-ready reporting", () => {
  const arcToStellar = {
    from: "arc",
    to: "stellar",
    amount: "10",
    recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
    speed: "standard",
    signer: arcSigner,
  } as const;

  it("stamps an attestation timeout with a code the caller can branch on", async () => {
    pollForAttestation.mockRejectedValueOnce(
      new AttestationNotReadyError("Timed out after 300000ms", "0xburnhookhash"),
    );

    const err = await transfer({ ...arcToStellar }).catch((e) => e);

    expect(err).toBeInstanceOf(TransferError);
    expect((err as InstanceType<typeof TransferError>).code).toBe("ATTESTATION_NOT_READY");
    expect((err as InstanceType<typeof TransferError>).burnTxHash).toBe("0xburnhookhash");
  });

  it("leaves the code undefined for a failure that is not merely slow", async () => {
    pollForAttestation.mockRejectedValueOnce(new Error("Iris attestation request failed with 503"));

    const err = await transfer({ ...arcToStellar }).catch((e) => e);

    expect(err).toBeInstanceOf(TransferError);
    expect((err as InstanceType<typeof TransferError>).code).toBeUndefined();
  });

  it("throws AttestationNotReadyError from completeMint, unwrapped, when Iris has no attestation", async () => {
    pollForAttestation.mockResolvedValueOnce({ message: null, attestation: null });

    const err = await completeMint({
      from: "arc",
      to: "stellar",
      burnTxHash: "0xburnhookhash",
      signer: stellarSigner,
    }).catch((e) => e);

    expect(err).toBeInstanceOf(AttestationNotReadyError);
    expect((err as InstanceType<typeof AttestationNotReadyError>).burnTxHash).toBe("0xburnhookhash");
    expect(mintAndForwardOnStellar).not.toHaveBeenCalled();
  });

  it("propagates an attestation timeout from completeMint with the same type", async () => {
    pollForAttestation.mockRejectedValueOnce(
      new AttestationNotReadyError("Timed out after 300000ms", "0xburnhookhash"),
    );

    await expect(
      completeMint({
        from: "arc",
        to: "stellar",
        burnTxHash: "0xburnhookhash",
        signer: stellarSigner,
      }),
    ).rejects.toBeInstanceOf(AttestationNotReadyError);
  });
});

describe("completeMint recipient guard", () => {
  it("checks the recipient encoded in the burn rather than a caller-supplied value", async () => {
    await completeMint({
      from: "arc",
      to: "stellar",
      burnTxHash: "0xburnhookhash",
      signer: stellarSigner,
    });

    expect(checkStellarRecipientReady).toHaveBeenCalledWith(FORWARD_RECIPIENT, "mainnet", undefined);
    expect(mintAndForwardOnStellar).toHaveBeenCalledTimes(1);
  });

  it("refuses to submit a Stellar mint whose destination cannot be read from the burn", async () => {
    pollForAttestation.mockResolvedValueOnce({
      message: buildBurnMessage(),
      attestation: "0xattestation",
    });

    await expect(
      completeMint({
        from: "arc",
        to: "stellar",
        burnTxHash: "0xburnhookhash",
        signer: stellarSigner,
      }),
    ).rejects.toThrow(/no readable Stellar forward recipient/);

    expect(checkStellarRecipientReady).not.toHaveBeenCalled();
    expect(mintAndForwardOnStellar).not.toHaveBeenCalled();
  });

  it("refuses to submit when the decoded recipient cannot receive USDC", async () => {
    checkStellarRecipientReady.mockResolvedValue({
      exists: true,
      hasTrustline: false,
      ready: false,
    });

    await expect(
      completeMint({
        from: "arc",
        to: "stellar",
        burnTxHash: "0xburnhookhash",
        signer: stellarSigner,
      }),
    ).rejects.toThrow(/no USDC trustline/);

    expect(mintAndForwardOnStellar).not.toHaveBeenCalled();
  });

  it("skips the Stellar check for an Arc destination, where it does not apply", async () => {
    await completeMint({
      from: "stellar",
      to: "arc",
      burnTxHash: "0xburnhash",
      signer: arcSigner,
    });

    expect(checkStellarRecipientReady).not.toHaveBeenCalled();
    expect(receiveMessageOnArc).toHaveBeenCalledTimes(1);
  });
});

describe("completeMint options", () => {
  it("threads options.stellarRpcUrl into the recipient check and the mint call", async () => {
    await completeMint({
      from: "arc",
      to: "stellar",
      burnTxHash: "0xburnhookhash",
      signer: stellarSigner,
      options: { stellarRpcUrl: "https://my-soroban.example/rpc" },
    });

    expect(checkStellarRecipientReady).toHaveBeenCalledWith(
      FORWARD_RECIPIENT,
      "mainnet",
      "https://my-soroban.example/rpc",
    );
    expect(mintAndForwardOnStellar.mock.calls[0]?.[0].rpcUrl).toBe("https://my-soroban.example/rpc");
  });

  it("threads options.pollInterval and options.pollTimeout into attestation polling", async () => {
    await completeMint({
      from: "arc",
      to: "stellar",
      burnTxHash: "0xburnhookhash",
      signer: stellarSigner,
      options: { pollInterval: 500, pollTimeout: 60000 },
    });

    expect(pollForAttestation.mock.calls[0]?.[0]).toMatchObject({
      pollInterval: 500,
      pollTimeout: 60000,
    });
  });

  it("still honours the top-level knobs for callers written against the older shape", async () => {
    await completeMint({
      from: "arc",
      to: "stellar",
      burnTxHash: "0xburnhookhash",
      signer: stellarSigner,
      pollInterval: 250,
      pollTimeout: 30000,
      stellarRpcUrl: "https://legacy-soroban.example/rpc",
    });

    expect(pollForAttestation.mock.calls[0]?.[0]).toMatchObject({
      pollInterval: 250,
      pollTimeout: 30000,
    });
    expect(mintAndForwardOnStellar.mock.calls[0]?.[0].rpcUrl).toBe("https://legacy-soroban.example/rpc");
  });

  it("prefers options when a caller passes both shapes", async () => {
    await completeMint({
      from: "arc",
      to: "stellar",
      burnTxHash: "0xburnhookhash",
      signer: stellarSigner,
      pollInterval: 250,
      stellarRpcUrl: "https://legacy-soroban.example/rpc",
      options: { pollInterval: 500, stellarRpcUrl: "https://my-soroban.example/rpc" },
    });

    expect(pollForAttestation.mock.calls[0]?.[0].pollInterval).toBe(500);
    expect(mintAndForwardOnStellar.mock.calls[0]?.[0].rpcUrl).toBe("https://my-soroban.example/rpc");
  });
});

describe("resolveBurn", () => {
  it("decodes the burn and reports the account the mint will pay", async () => {
    const resolved = await resolveBurn({ from: "arc", burnTxHash: "0xburnhookhash" });

    expect(resolved.sourceDomain).toBe(26);
    expect(resolved.destinationDomain).toBe(27);
    expect(resolved.forwardRecipient).toBe(FORWARD_RECIPIENT);
  });

  it("reads the burn with one request instead of polling the attestation window", async () => {
    await resolveBurn({ from: "arc", burnTxHash: "0xburnhookhash" });

    expect(getAttestation).toHaveBeenCalledTimes(1);
    expect(pollForAttestation).not.toHaveBeenCalled();
  });

  it("routes a testnet burn to the sandbox Iris environment", async () => {
    await resolveBurn({ from: "arc", burnTxHash: "0xburnhookhash", network: "testnet" });

    expect(getAttestation).toHaveBeenCalledWith({
      sourceDomain: 26,
      transactionHash: "0xburnhookhash",
      useSandbox: true,
    });
  });

  it("still resolves the destination while the attestation is pending", async () => {
    getAttestation.mockResolvedValueOnce({
      message: buildBurnMessage({ forwardRecipient: FORWARD_RECIPIENT }),
      attestation: null,
    });

    const resolved = await resolveBurn({ from: "arc", burnTxHash: "0xburnhookhash" });

    expect(resolved.attestation).toBeNull();
    expect(resolved.forwardRecipient).toBe(FORWARD_RECIPIENT);
  });
});

describe("transfer fast/standard fee handling", () => {
  it("falls back to standard when the quoted fast fee exceeds maxFee", async () => {
    fetchFastTransferFeeBps.mockResolvedValue(100); // 1% - exceeds maxFee below

    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "fast",
      signer: arcSigner,
      options: { maxFee: "0.01", destinationSigner: stellarSigner },
    });

    expect(result.transferMode).toBe("standard");
    expect(result.fee).toBe("0");
  });

  it("uses fast mode and reports the quoted fee when within maxFee", async () => {
    fetchFastTransferFeeBps.mockResolvedValue(1); // 0.01%

    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "1000",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "fast",
      signer: arcSigner,
      options: { maxFee: "1", destinationSigner: stellarSigner },
    });

    expect(result.transferMode).toBe("fast");
    expect(result.fee).toBe("0.1");
  });
});

describe("transfer destination precision pre-flight check", () => {
  it("rejects Stellar -> Arc amounts with 7 significant decimals before approve or burn", async () => {
    const err = await transfer({
      from: "stellar",
      to: "arc",
      amount: "1.1234567",
      recipient: "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
      speed: "standard",
      signer: stellarSigner,
      options: { destinationSigner: arcSigner },
    }).catch((caught: unknown) => caught);

    expect(err).toBeInstanceOf(AmountPrecisionError);
    expect(err).toMatchObject({
      amount: "1.1234567",
      precision: 7,
      supportedDecimals: 6,
      destination: "arc",
    });
    expect(approveUsdcOnStellar).not.toHaveBeenCalled();
    expect(burnUsdcOnStellar).not.toHaveBeenCalled();
  });

  it("accepts Stellar -> Arc amounts when extra decimal places are trailing zeros", async () => {
    const result = await transfer({
      from: "stellar",
      to: "arc",
      amount: "1.1230000",
      recipient: "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
      speed: "standard",
      signer: stellarSigner,
      options: { destinationSigner: arcSigner },
    });

    expect(result.status).toBe("success");
    expect(approveUsdcOnStellar).toHaveBeenCalledWith(11_230_000n, stellarSigner, "mainnet", undefined, undefined);
    expect(burnUsdcOnStellar).toHaveBeenCalledTimes(1);
  });

  it("accepts Arc -> Stellar amounts with up to 6 decimal places", async () => {
    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "1.123456",
      recipient: "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPV6LY4UV2GL6VJGIQRXFDNMADI",
      speed: "standard",
      signer: arcSigner,
      options: { destinationSigner: stellarSigner },
    });

    expect(result.status).toBe("success");
    expect(approveUsdcOnArc).toHaveBeenCalledWith(arcSigner, 1_123_456n, "mainnet", undefined);
    expect(burnUsdcOnArcWithStellarForward).toHaveBeenCalledTimes(1);
  });
});
