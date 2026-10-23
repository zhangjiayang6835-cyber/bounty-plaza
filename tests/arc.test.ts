import { describe, it, expect, vi, beforeEach } from "vitest";

const waitForTransactionReceipt = vi.fn();
const readContract = vi.fn();

vi.mock("viem", async (importOriginal) => {
  const actual = await importOriginal<typeof import("viem")>();
  return {
    ...actual,
    createPublicClient: () => ({ waitForTransactionReceipt, readContract }),
  };
});

const {
  approveUsdcOnArc,
  getUsdcAllowanceOnArc,
  burnUsdcOnArc,
  burnUsdcOnArcWithStellarForward,
  receiveMessageOnArc,
} = await import("../src/chains/arc.js");
const { ARC_TESTNET, ARC_MAINNET } = await import("../src/constants.js");

const FAKE_HASH = "0x" + "a".repeat(64);
const ZERO_BYTES32 = `0x${"0".repeat(64)}`;

function makeSigner() {
  const writeContract = vi.fn().mockResolvedValue(FAKE_HASH);
  const signer = {
    walletClient: {
      account: { address: "0x1111111111111111111111111111111111111111" },
      writeContract,
    },
  } as any;
  return { signer, writeContract };
}

beforeEach(() => {
  vi.clearAllMocks();
  waitForTransactionReceipt.mockResolvedValue({ status: "success" });
  readContract.mockResolvedValue(0n);
});

describe("approveUsdcOnArc", () => {
  it("calls approve on the USDC contract with the TokenMessengerV2 as spender", async () => {
    const { signer, writeContract } = makeSigner();

    const hash = await approveUsdcOnArc(signer, 10_000_000n, "testnet");

    expect(hash).toBe(FAKE_HASH);
    expect(readContract).toHaveBeenCalledWith(
      expect.objectContaining({
        address: ARC_TESTNET.usdc,
        functionName: "allowance",
        args: ["0x1111111111111111111111111111111111111111", ARC_TESTNET.tokenMessengerV2],
      }),
    );
    expect(writeContract).toHaveBeenCalledTimes(1);
    const call = writeContract.mock.calls[0]?.[0];
    expect(call.address).toBe(ARC_TESTNET.usdc);
    expect(call.functionName).toBe("approve");
    expect(call.args).toEqual([ARC_TESTNET.tokenMessengerV2, 10_000_000n]);
    expect(waitForTransactionReceipt).toHaveBeenCalledWith({ hash: FAKE_HASH });
  });

  it("targets the mainnet USDC and TokenMessengerV2 when network is mainnet", async () => {
    const { signer, writeContract } = makeSigner();

    await approveUsdcOnArc(signer, 10_000_000n, "mainnet");

    const call = writeContract.mock.calls[0]?.[0];
    expect(call.address).toBe(ARC_MAINNET.usdc);
    expect(call.args).toEqual([ARC_MAINNET.tokenMessengerV2, 10_000_000n]);
  });

  it("skips the approve transaction when existing allowance equals or exceeds amountRaw", async () => {
    const { signer, writeContract } = makeSigner();
    readContract.mockResolvedValueOnce(10_000_000n);

    const hashEqual = await approveUsdcOnArc(signer, 10_000_000n, "testnet");

    expect(hashEqual).toBeUndefined();
    expect(writeContract).not.toHaveBeenCalled();
    expect(waitForTransactionReceipt).not.toHaveBeenCalled();

    readContract.mockResolvedValueOnce(25_000_000n);
    const hashGreater = await approveUsdcOnArc(signer, 10_000_000n, "testnet");

    expect(hashGreater).toBeUndefined();
    expect(writeContract).not.toHaveBeenCalled();
  });

  it("replaces a partial allowance with the exact amount rather than topping it up", async () => {
    const { signer, writeContract } = makeSigner();
    readContract.mockResolvedValueOnce(9_999_999n);

    const hash = await approveUsdcOnArc(signer, 10_000_000n, "testnet");

    expect(hash).toBe(FAKE_HASH);
    expect(writeContract).toHaveBeenCalledTimes(1);
    expect(writeContract.mock.calls[0]?.[0].args).toEqual([
      ARC_TESTNET.tokenMessengerV2,
      10_000_000n,
    ]);
  });

  it("fails closed and submits the exact-amount approve when the allowance read fails", async () => {
    const { signer, writeContract } = makeSigner();
    readContract.mockRejectedValueOnce(new Error("RPC read failure"));

    const hash = await approveUsdcOnArc(signer, 10_000_000n, "testnet");

    expect(hash).toBe(FAKE_HASH);
    expect(writeContract).toHaveBeenCalledTimes(1);
    expect(writeContract.mock.calls[0]?.[0].args).toEqual([
      ARC_TESTNET.tokenMessengerV2,
      10_000_000n,
    ]);
  });
});

describe("burnUsdcOnArc", () => {
  it("calls depositForBurn on TokenMessengerV2 with an unrestricted destinationCaller", async () => {
    const { signer, writeContract } = makeSigner();
    const mintRecipient = `0x${"11".repeat(32)}` as const;

    await burnUsdcOnArc({
      amountRaw: 5_000_000n,
      destinationDomain: 27,
      mintRecipientBytes32: mintRecipient,
      maxFeeRaw: 100n,
      minFinalityThreshold: 2000,
      signer,
      network: "testnet",
    });

    const call = writeContract.mock.calls[0]?.[0];
    expect(call.address).toBe(ARC_TESTNET.tokenMessengerV2);
    expect(call.functionName).toBe("depositForBurn");
    expect(call.args).toEqual([
      5_000_000n,
      27,
      mintRecipient,
      ARC_TESTNET.usdc,
      ZERO_BYTES32,
      100n,
      2000,
    ]);
  });
});

describe("burnUsdcOnArcWithStellarForward", () => {
  it("calls depositForBurnWithHook, appending hookData after minFinalityThreshold", async () => {
    const { signer, writeContract } = makeSigner();
    const mintRecipient = `0x${"22".repeat(32)}` as const;
    const hookData = `0x${"33".repeat(10)}` as const;

    await burnUsdcOnArcWithStellarForward({
      amountRaw: 7_000_000n,
      destinationDomain: 27,
      mintRecipientBytes32: mintRecipient,
      maxFeeRaw: 50n,
      minFinalityThreshold: 1000,
      hookData,
      signer,
      network: "testnet",
    });

    const call = writeContract.mock.calls[0]?.[0];
    expect(call.address).toBe(ARC_TESTNET.tokenMessengerV2);
    expect(call.functionName).toBe("depositForBurnWithHook");
    expect(call.args).toEqual([
      7_000_000n,
      27,
      mintRecipient,
      ARC_TESTNET.usdc,
      ZERO_BYTES32,
      50n,
      1000,
      hookData,
    ]);
  });
});

describe("receiveMessageOnArc", () => {
  it("calls receiveMessage on MessageTransmitterV2 with the message and attestation", async () => {
    const { signer, writeContract } = makeSigner();
    const message = `0x${"44".repeat(20)}` as const;
    const attestation = `0x${"55".repeat(65)}` as const;

    const hash = await receiveMessageOnArc({ message, attestation, signer, network: "testnet" });

    expect(hash).toBe(FAKE_HASH);
    const call = writeContract.mock.calls[0]?.[0];
    expect(call.address).toBe(ARC_TESTNET.messageTransmitterV2);
    expect(call.functionName).toBe("receiveMessage");
    expect(call.args).toEqual([message, attestation]);
  });
});

describe("signer validation", () => {
  it("throws if the walletClient has no account attached", async () => {
    const signer = {
      walletClient: { account: undefined, writeContract: vi.fn() },
    } as any;

    await expect(approveUsdcOnArc(signer, 1n, "testnet")).rejects.toThrow(
      "ArcSigner's walletClient must have an account attached",
    );
  });
});

describe("getUsdcAllowanceOnArc", () => {
  it("reads allowance for an ArcSigner's account address on testnet", async () => {
    const { signer } = makeSigner();
    readContract.mockResolvedValue(25_000_000n);

    const allowance = await getUsdcAllowanceOnArc(signer, "testnet");

    expect(allowance).toBe(25_000_000n);
    expect(readContract).toHaveBeenCalledTimes(1);
    const call = readContract.mock.calls[0]?.[0];
    expect(call.address).toBe(ARC_TESTNET.usdc);
    expect(call.functionName).toBe("allowance");
    expect(call.args).toEqual([
      "0x1111111111111111111111111111111111111111",
      ARC_TESTNET.tokenMessengerV2,
    ]);
  });

  it("reads allowance for a direct Hex owner address on mainnet", async () => {
    readContract.mockResolvedValue(50_000_000n);
    const owner = "0x2222222222222222222222222222222222222222";

    const allowance = await getUsdcAllowanceOnArc(owner, "mainnet");

    expect(allowance).toBe(50_000_000n);
    const call = readContract.mock.calls[0]?.[0];
    expect(call.address).toBe(ARC_MAINNET.usdc);
    expect(call.args).toEqual([owner, ARC_MAINNET.tokenMessengerV2]);
  });

  it("throws if ArcSigner has no account attached", async () => {
    const signer = { walletClient: {} } as any;
    await expect(getUsdcAllowanceOnArc(signer, "testnet")).rejects.toThrow(
      "ArcSigner's walletClient must have an account attached",
    );
  });
});
