import { describe, it, expect, vi, afterEach } from "vitest";
import { Account, Contract, Keypair, StrKey, nativeToScVal, rpc } from "@stellar/stellar-sdk";
import {
  burnUsdcOnStellar,
  mintAndForwardOnStellar,
  approveUsdcOnStellar,
  checkStellarRecipientReady,
  pollTransactionStatus,
} from "../src/chains/stellar.js";
import { SubmissionTimeoutError } from "../src/errors.js";
import { STELLAR_TESTNET } from "../src/constants.js";
import { stellarAddressToBytes32 } from "../src/utils/encoding.js";

function contractIdOf(contract: Contract): string {
  return StrKey.encodeContract((contract as unknown as { _id: Buffer })._id);
}

const FAKE_HASH = "a".repeat(64);

function mockHappyPathRpc() {
  const signerKeypair = Keypair.random();

  vi.spyOn(rpc.Server.prototype, "getAccount").mockResolvedValue(
    new Account(signerKeypair.publicKey(), "1"),
  );
  vi.spyOn(rpc.Server.prototype, "prepareTransaction").mockImplementation(
    async (tx) => tx as any,
  );
  vi.spyOn(rpc.Server.prototype, "sendTransaction").mockResolvedValue({
    status: "PENDING",
    hash: FAKE_HASH,
  } as any);
  vi.spyOn(rpc.Server.prototype, "getTransaction").mockResolvedValue({
    status: "SUCCESS",
  } as any);

  return signerKeypair;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("burnUsdcOnStellar (TokenMessengerMinter.deposit_for_burn)", () => {
  it("invokes TokenMessengerMinter with deposit_for_burn and returns the tx hash", async () => {
    const signerKeypair = mockHappyPathRpc();
    const callSpy = vi.spyOn(Contract.prototype, "call");

    const recipient = Keypair.random().publicKey();
    const hash = await burnUsdcOnStellar({
      amountRaw: 10_000_000n,
      destinationDomain: 26,
      mintRecipientBytes32: stellarAddressToBytes32(recipient),
      maxFeeRaw: 1000n,
      minFinalityThreshold: 2000,
      signer: { publicKey: signerKeypair.publicKey(), keypair: signerKeypair },
      network: "testnet",
    });

    expect(hash).toBe(FAKE_HASH);
    expect(callSpy).toHaveBeenCalledTimes(1);
    expect(contractIdOf(callSpy.mock.instances[0] as unknown as Contract)).toBe(STELLAR_TESTNET.tokenMessengerMinter);
    expect(callSpy.mock.calls[0]?.[0]).toBe("deposit_for_burn");
  });

  it("retries once on a transient 'not enough allowance' error and then succeeds", async () => {
    const signerKeypair = mockHappyPathRpc();
    vi.spyOn(rpc.Server.prototype, "prepareTransaction")
      .mockRejectedValueOnce(
        new Error('HostError: ... data:["not enough allowance to spend", 0, 10000000] ...'),
      )
      .mockImplementation(async (tx) => tx as any);

    const recipient = Keypair.random().publicKey();
    const hash = await burnUsdcOnStellar({
      amountRaw: 10_000_000n,
      destinationDomain: 26,
      mintRecipientBytes32: stellarAddressToBytes32(recipient),
      maxFeeRaw: 1000n,
      minFinalityThreshold: 2000,
      signer: { publicKey: signerKeypair.publicKey(), keypair: signerKeypair },
      network: "testnet",
    });

    expect(hash).toBe(FAKE_HASH);
  }, 10_000);

  it("retries once on a transient txBadSeq error and then succeeds", async () => {
    const signerKeypair = mockHappyPathRpc();
    vi.spyOn(rpc.Server.prototype, "sendTransaction")
      .mockResolvedValueOnce({
        status: "ERROR",
        errorResult: { _switch: { name: "txBadSeq", value: -5 } },
      } as any)
      .mockResolvedValue({ status: "PENDING", hash: FAKE_HASH } as any);

    const recipient = Keypair.random().publicKey();
    const hash = await burnUsdcOnStellar({
      amountRaw: 10_000_000n,
      destinationDomain: 26,
      mintRecipientBytes32: stellarAddressToBytes32(recipient),
      maxFeeRaw: 1000n,
      minFinalityThreshold: 2000,
      signer: { publicKey: signerKeypair.publicKey(), keypair: signerKeypair },
      network: "testnet",
    });

    expect(hash).toBe(FAKE_HASH);
  }, 10_000);

  it("does not retry a non-allowance failure", async () => {
    const signerKeypair = mockHappyPathRpc();
    vi.spyOn(rpc.Server.prototype, "prepareTransaction").mockRejectedValue(
      new Error("some unrelated simulation failure"),
    );

    const recipient = Keypair.random().publicKey();
    await expect(
      burnUsdcOnStellar({
        amountRaw: 10_000_000n,
        destinationDomain: 26,
        mintRecipientBytes32: stellarAddressToBytes32(recipient),
        maxFeeRaw: 1000n,
        minFinalityThreshold: 2000,
        signer: { publicKey: signerKeypair.publicKey(), keypair: signerKeypair },
        network: "testnet",
      }),
    ).rejects.toThrow("some unrelated simulation failure");
  });

  it("honors custom retry attempts and delayMs on transient RPC lag", async () => {
    vi.useFakeTimers();
    try {
      const signerKeypair = mockHappyPathRpc();
      const prepareSpy = vi
        .spyOn(rpc.Server.prototype, "prepareTransaction")
        .mockRejectedValueOnce(new Error("not enough allowance"))
        .mockRejectedValueOnce(new Error("not enough allowance"))
        .mockRejectedValueOnce(new Error("not enough allowance"))
        .mockImplementation(async (tx) => tx as any);

      const recipient = Keypair.random().publicKey();
      const promise = burnUsdcOnStellar({
        amountRaw: 10_000_000n,
        destinationDomain: 26,
        mintRecipientBytes32: stellarAddressToBytes32(recipient),
        maxFeeRaw: 1000n,
        minFinalityThreshold: 2000,
        signer: { publicKey: signerKeypair.publicKey(), keypair: signerKeypair },
        network: "testnet",
        retry: { attempts: 4, delayMs: 250 },
      });

      await vi.advanceTimersByTimeAsync(750);
      const hash = await promise;
      expect(hash).toBe(FAKE_HASH);
      expect(prepareSpy).toHaveBeenCalledTimes(4);
    } finally {
      vi.useRealTimers();
    }
  });

  it("rejects non-positive or non-integer retry options", async () => {
    const signerKeypair = mockHappyPathRpc();
    const recipient = Keypair.random().publicKey();

    await expect(
      burnUsdcOnStellar({
        amountRaw: 10_000_000n,
        destinationDomain: 26,
        mintRecipientBytes32: stellarAddressToBytes32(recipient),
        maxFeeRaw: 1000n,
        minFinalityThreshold: 2000,
        signer: { publicKey: signerKeypair.publicKey(), keypair: signerKeypair },
        network: "testnet",
        retry: { attempts: 0 },
      }),
    ).rejects.toThrow(/Invalid Stellar retry attempts/);
  });
});

describe("approveUsdcOnStellar", () => {
  it("waits for the allowance to actually be readable before returning", async () => {
    const signerKeypair = mockHappyPathRpc();
    vi.spyOn(rpc.Server.prototype, "getLatestLedger").mockResolvedValue({ sequence: 100 } as any);

    // Simulates the RPC read-after-write lag this polling exists to cover: the first
    // simulateTransaction call still sees the pre-approval allowance (0), the second
    // reflects the just-confirmed approve. approveUsdcOnStellar must not return until
    // the real on-chain state agrees with the approve it just submitted.
    const simulate = vi
      .spyOn(rpc.Server.prototype, "simulateTransaction")
      .mockResolvedValueOnce({
        transactionData: {},
        result: { retval: nativeToScVal(0n, { type: "i128" }) },
      } as any)
      .mockResolvedValueOnce({
        transactionData: {},
        result: { retval: nativeToScVal(10_000_000n, { type: "i128" }) },
      } as any);

    const hash = await approveUsdcOnStellar(10_000_000n, {
      publicKey: signerKeypair.publicKey(),
      keypair: signerKeypair,
    }, "testnet");

    expect(hash).toBe(FAKE_HASH);
    expect(simulate).toHaveBeenCalledTimes(2);
  });

  it("throws a clear error if the allowance never reflects the approval", async () => {
    mockHappyPathRpc();
    vi.spyOn(rpc.Server.prototype, "getLatestLedger").mockResolvedValue({ sequence: 100 } as any);
    vi.spyOn(rpc.Server.prototype, "simulateTransaction").mockResolvedValue({
      transactionData: {},
      result: { retval: nativeToScVal(0n, { type: "i128" }) },
    } as any);

    const signerKeypair = Keypair.random();
    await expect(
      approveUsdcOnStellar(10_000_000n, { publicKey: signerKeypair.publicKey(), keypair: signerKeypair }, "testnet"),
    ).rejects.toThrow(/did not reach/);
  }, 15_000);

  it("honors custom retry attempts and delayMs in waitForAllowance", async () => {
    vi.useFakeTimers();
    try {
      const signerKeypair = mockHappyPathRpc();
      vi.spyOn(rpc.Server.prototype, "getLatestLedger").mockResolvedValue({ sequence: 100 } as any);
      const simulate = vi.spyOn(rpc.Server.prototype, "simulateTransaction").mockResolvedValue({
        transactionData: {},
        result: { retval: nativeToScVal(0n, { type: "i128" }) },
      } as any);

      const promise = approveUsdcOnStellar(
        10_000_000n,
        { publicKey: signerKeypair.publicKey(), keypair: signerKeypair },
        "testnet",
        undefined,
        { attempts: 2, delayMs: 300 },
      );
      const assertion = expect(promise).rejects.toThrow(/after 0\.6s of polling/);
      await vi.advanceTimersByTimeAsync(600);
      await assertion;
      expect(simulate).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("checkStellarRecipientReady", () => {
  it("reports not-existing when the account has never been funded", async () => {
    vi.spyOn(rpc.Server.prototype, "getAccount").mockRejectedValue(
      new Error("Account not found: G..."),
    );

    const status = await checkStellarRecipientReady(Keypair.random().publicKey());

    expect(status).toEqual({ exists: false, hasTrustline: false, ready: false });
  });

  it("reports missing-trustline when the account exists but has never held USDC", async () => {
    const recipient = Keypair.random().publicKey();
    vi.spyOn(rpc.Server.prototype, "getAccount").mockResolvedValue(new Account(recipient, "1"));
    vi.spyOn(rpc.Server.prototype, "simulateTransaction").mockResolvedValue({
      error:
        'HostError: Error(Contract, #13)\n\nEvent log (newest first):\n   0: [Diagnostic Event] ... data:["trustline entry is missing for account", "' +
        recipient +
        '"]',
    } as any);

    const status = await checkStellarRecipientReady(recipient);

    expect(status).toEqual({ exists: true, hasTrustline: false, ready: false });
  });

  it("reports ready when the account exists and holds the USDC trustline", async () => {
    const recipient = Keypair.random().publicKey();
    vi.spyOn(rpc.Server.prototype, "getAccount").mockResolvedValue(new Account(recipient, "1"));
    vi.spyOn(rpc.Server.prototype, "simulateTransaction").mockResolvedValue({
      transactionData: {},
      result: { retval: nativeToScVal(0n, { type: "i128" }) },
    } as any);

    const status = await checkStellarRecipientReady(recipient);

    expect(status).toEqual({ exists: true, hasTrustline: true, ready: true });
  });

  it("rethrows an unrelated simulation error instead of misreporting it as a missing trustline", async () => {
    const recipient = Keypair.random().publicKey();
    vi.spyOn(rpc.Server.prototype, "getAccount").mockResolvedValue(new Account(recipient, "1"));
    vi.spyOn(rpc.Server.prototype, "simulateTransaction").mockResolvedValue({
      error: "HostError: some unrelated simulation failure",
    } as any);

    await expect(checkStellarRecipientReady(recipient)).rejects.toThrow(
      /Failed to check Stellar recipient's USDC trustline/,
    );
  });

  it("rejects on transport errors instead of reporting the account as non-existent", async () => {
    vi.spyOn(rpc.Server.prototype, "getAccount").mockRejectedValue(
      new Error("fetch failed: ECONNREFUSED"),
    );

    await expect(checkStellarRecipientReady(Keypair.random().publicKey())).rejects.toThrow(
      /fetch failed: ECONNREFUSED/,
    );
  });

  it("rejects on 5xx server errors instead of reporting the account as non-existent", async () => {
    vi.spyOn(rpc.Server.prototype, "getAccount").mockRejectedValue(
      new Error("Soroban RPC error: 503 Service Unavailable"),
    );

    await expect(checkStellarRecipientReady(Keypair.random().publicKey())).rejects.toThrow(
      /503 Service Unavailable/,
    );
  });
});

describe("mintAndForwardOnStellar (CctpForwarder.mint_and_forward)", () => {
  it("routes inbound transfers through the CctpForwarder contract, not a direct mint", async () => {
    const signerKeypair = mockHappyPathRpc();
    const callSpy = vi.spyOn(Contract.prototype, "call");

    const hash = await mintAndForwardOnStellar({
      message: `0x${"11".repeat(32)}`,
      attestation: `0x${"22".repeat(65)}`,
      signer: { publicKey: signerKeypair.publicKey(), keypair: signerKeypair },
      network: "testnet",
    });

    expect(hash).toBe(FAKE_HASH);
    expect(callSpy).toHaveBeenCalledTimes(1);
    expect(contractIdOf(callSpy.mock.instances[0] as unknown as Contract)).toBe(STELLAR_TESTNET.cctpForwarder);
    expect(callSpy.mock.calls[0]?.[0]).toBe("mint_and_forward");
  });
});

describe("pollTransactionStatus (transient RPC error tolerance & hash preservation)", () => {
  it("resolves with the tx hash when a mocked getTransaction succeeds immediately", async () => {
    const server = new rpc.Server("https://mock-stellar.local");
    vi.spyOn(server, "getTransaction").mockResolvedValueOnce({
      status: "SUCCESS",
    } as any);

    const hash = await pollTransactionStatus(server, FAKE_HASH, { pollIntervalMs: 5 });
    expect(hash).toBe(FAKE_HASH);
  });

  it("resolves with the tx hash when getTransaction throws N-1 transient RPC errors then succeeds", async () => {
    const server = new rpc.Server("https://mock-stellar.local");
    const getTxSpy = vi.spyOn(server, "getTransaction");

    // Throws 4 times (N-1 where N=5), then succeeds on the 5th attempt
    getTxSpy
      .mockRejectedValueOnce(new Error("Connection reset by peer"))
      .mockRejectedValueOnce(new Error("HTTP 504 Gateway Timeout"))
      .mockRejectedValueOnce(new Error("Soroban RPC network blip"))
      .mockRejectedValueOnce(new Error("ECONNREFUSED"))
      .mockResolvedValueOnce({ status: "SUCCESS" } as any);

    const hash = await pollTransactionStatus(server, FAKE_HASH, {
      pollIntervalMs: 5,
      maxConsecutiveFailures: 5,
    });

    expect(hash).toBe(FAKE_HASH);
    expect(getTxSpy).toHaveBeenCalledTimes(5);
  });

  it("rejects with SubmissionTimeoutError preserving the tx hash when getTransaction always throws", async () => {
    const server = new rpc.Server("https://mock-stellar.local");
    vi.spyOn(server, "getTransaction").mockRejectedValue(
      new Error("Persistent 500 Internal Server Error"),
    );

    const promise = pollTransactionStatus(server, FAKE_HASH, {
      pollIntervalMs: 5,
      maxConsecutiveFailures: 3,
    });

    await expect(promise).rejects.toThrow(SubmissionTimeoutError);
    await expect(promise).rejects.toMatchObject({
      hash: FAKE_HASH,
    });
  });

  it("rejects immediately on FAILED transaction status without retrying or exhausting retries", async () => {
    const server = new rpc.Server("https://mock-stellar.local");
    const getTxSpy = vi.spyOn(server, "getTransaction").mockResolvedValueOnce({
      status: "FAILED",
    } as any);

    const promise = pollTransactionStatus(server, FAKE_HASH, {
      pollIntervalMs: 5,
      maxConsecutiveFailures: 5,
    });

    await expect(promise).rejects.toThrow(`Stellar transaction ${FAKE_HASH} failed`);
    // Crucially: it must NOT retry on FAILED status
    expect(getTxSpy).toHaveBeenCalledTimes(1);
  });

  it("preserves burnTxHash through burnUsdcOnStellar when polling encounters transient RPC failure", async () => {
    const signerKeypair = mockHappyPathRpc();
    // Simulate sendTransaction returning the broadcast hash, but getTransaction throwing transiently then resolving
    vi.spyOn(rpc.Server.prototype, "getTransaction")
      .mockRejectedValueOnce(new Error("Transient connection blip"))
      .mockResolvedValueOnce({ status: "SUCCESS" } as any);

    const recipient = Keypair.random().publicKey();
    const hash = await burnUsdcOnStellar({
      amountRaw: 10_000_000n,
      destinationDomain: 26,
      mintRecipientBytes32: stellarAddressToBytes32(recipient),
      maxFeeRaw: 1000n,
      minFinalityThreshold: 2000,
      signer: { publicKey: signerKeypair.publicKey(), keypair: signerKeypair },
      network: "testnet",
    });

    expect(hash).toBe(FAKE_HASH);
  });
});

