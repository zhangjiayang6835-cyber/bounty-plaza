/**
 * soroban-lite-sdk — tests/client.test.ts
 *
 * Unit tests for SorobanClient covering:
 *  - Constructor validation and named-network presets
 *  - simulateTransaction (success, error body, network failure)
 *  - pollTransactionStatus (immediate, retry-then-resolve, timeout, backoff)
 *  - signAndSubmit helper flow (simulate -> sign -> sendTransaction -> poll)
 *  - getAccount, getLatestLedger delegation
 *  - Utility functions: isSimulationError, decodeScVal, resolveNetworkConfig
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { rpc, xdr, Networks, TransactionBuilder, Account, Keypair, Operation } from "@stellar/stellar-sdk";
import {
  SorobanClient,
  SorobanConfig,
  SimulationResult,
  RetryOptions,
  isSimulationError,
  decodeScVal,
  resolveNetworkConfig,
  RPC_ENDPOINTS,
  WalletAdapter,
} from "../src/index";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TESTNET_CONFIG: SorobanConfig = {
  rpcUrl: "https://soroban-testnet.stellar.org",
  networkPassphrase: Networks.TESTNET,
};

const MOCK_HASH =
  "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef";

const NOT_FOUND_RESPONSE: rpc.Api.GetTransactionResponse = {
  status: rpc.Api.GetTransactionStatus.NOT_FOUND,
  latestLedger: 100,
  latestLedgerCloseTime: 0,
  oldestLedger: 1,
  oldestLedgerCloseTime: 0,
} as rpc.Api.GetTransactionResponse;

const SUCCESS_RESPONSE: rpc.Api.GetTransactionResponse = {
  status: rpc.Api.GetTransactionStatus.SUCCESS,
  latestLedger: 105,
  latestLedgerCloseTime: 0,
  oldestLedger: 1,
  oldestLedgerCloseTime: 0,
} as rpc.Api.GetTransactionResponse;

const FAILED_RESPONSE: rpc.Api.GetTransactionResponse = {
  status: rpc.Api.GetTransactionStatus.FAILED,
  latestLedger: 106,
  latestLedgerCloseTime: 0,
  oldestLedger: 1,
  oldestLedgerCloseTime: 0,
} as rpc.Api.GetTransactionResponse;

function makeClient(overrides: Partial<Extract<SorobanConfig, { rpcUrl: string }>> = {}): SorobanClient {
  return new SorobanClient({ ...TESTNET_CONFIG, ...overrides } as SorobanConfig);
}

function buildDummyTx(passphrase = Networks.TESTNET) {
  const kp = Keypair.random();
  const account = new Account(kp.publicKey(), "100");
  return new TransactionBuilder(account, { fee: "100", networkPassphrase: passphrase })
    .addOperation(Operation.payment({
      destination: Keypair.random().publicKey(),
      asset: { isNative: () => true } as any,
      amount: "10",
    }))
    .setTimeout(30)
    .build();
}

// ─── 1. Constructor & Initialization ─────────────────────────────────────────

describe("SorobanClient — constructor", () => {
  it("creates an instance with explicit rpcUrl + networkPassphrase", () => {
    const client = makeClient();
    expect(client).toBeInstanceOf(SorobanClient);
    expect(client.networkPassphrase).toBe(Networks.TESTNET);
    expect(client.rpcUrl).toBe("https://soroban-testnet.stellar.org");
  });

  it("creates an instance using named network preset: TESTNET", () => {
    const client = new SorobanClient({ network: "TESTNET" });
    expect(client.rpcUrl).toBe(RPC_ENDPOINTS.TESTNET);
    expect(client.networkPassphrase).toBe(Networks.TESTNET);
  });

  it("creates an instance using named network preset: MAINNET", () => {
    const client = new SorobanClient({ network: "MAINNET" });
    expect(client.rpcUrl).toBe(RPC_ENDPOINTS.MAINNET);
    expect(client.networkPassphrase).toBe(Networks.PUBLIC);
  });

  it("creates an instance using named network preset: FUTURENET", () => {
    const client = new SorobanClient({ network: "FUTURENET" });
    expect(client.rpcUrl).toBe(RPC_ENDPOINTS.FUTURENET);
    expect(client.networkPassphrase).toBe(Networks.FUTURENET);
  });

  it("exposes the underlying rpc.Server via .rpcServer", () => {
    const client = makeClient();
    expect(client.rpcServer).toBeDefined();
  });

  it("throws when rpcUrl is empty string", () => {
    expect(() => makeClient({ rpcUrl: "" })).toThrowError("rpcUrl");
  });

  it("throws when rpcUrl is whitespace only", () => {
    expect(() => makeClient({ rpcUrl: "   " })).toThrowError("rpcUrl");
  });

  it("throws when networkPassphrase is empty string", () => {
    expect(() => makeClient({ networkPassphrase: "" })).toThrowError(
      "networkPassphrase"
    );
  });
});

// ─── 2. simulateTransaction ───────────────────────────────────────────────────

describe("SorobanClient — simulateTransaction", () => {
  let client: SorobanClient;

  beforeEach(() => {
    client = makeClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns decoded returnValue and minResourceFee on success", async () => {
    const mockVal = xdr.ScVal.scvI32(123);
    const mockResponse = {
      minResourceFee: "1500",
      result: {
        retval: mockVal,
      },
      latestLedger: 100,
    } as any;

    vi.spyOn(client.rpcServer, "simulateTransaction").mockResolvedValue(
      mockResponse
    );

    const dummyTx = buildDummyTx();
    const result = await client.simulateTransaction(dummyTx);

    expect(result.success).toBe(true);
    expect(result.minResourceFee).toBe("1500");
    expect(result.returnValue).toBeDefined();
    expect(result.returnValue!.switch()).toBe(xdr.ScValType.scvI32());
    expect(result.returnValue!.i32()).toBe(123);
  });

  it("returns returnValue: undefined when result.retval is absent", async () => {
    const mockResponse = {
      minResourceFee: "100",
      result: {},
      latestLedger: 100,
    } as any;

    vi.spyOn(client.rpcServer, "simulateTransaction").mockResolvedValue(
      mockResponse
    );

    const dummyTx = buildDummyTx();
    const result = await client.simulateTransaction(dummyTx);

    expect(result.success).toBe(true);
    expect(result.returnValue).toBeUndefined();
  });

  it("throws contract error when response contains an error field", async () => {
    const mockErrorResponse = {
      error: "HostError: Error(Contract, #1)",
      latestLedger: 100,
    } as any;

    vi.spyOn(client.rpcServer, "simulateTransaction").mockResolvedValue(
      mockErrorResponse
    );

    const dummyTx = buildDummyTx();
    await expect(client.simulateTransaction(dummyTx)).rejects.toThrow(
      "simulateTransaction: contract error — HostError: Error(Contract, #1)"
    );
  });

  it("throws network error when rpc call fails", async () => {
    vi.spyOn(client.rpcServer, "simulateTransaction").mockRejectedValue(
      new Error("ECONNREFUSED")
    );

    const dummyTx = buildDummyTx();
    await expect(client.simulateTransaction(dummyTx)).rejects.toThrow(
      "simulateTransaction: network error — ECONNREFUSED"
    );
  });
});

// ─── 3. pollTransactionStatus ─────────────────────────────────────────────────

describe("SorobanClient — pollTransactionStatus", () => {
  let client: SorobanClient;

  beforeEach(() => {
    vi.useFakeTimers();
    client = makeClient();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("resolves immediately on first attempt if SUCCESS", async () => {
    vi.spyOn(client.rpcServer, "getTransaction").mockResolvedValue(
      SUCCESS_RESPONSE
    );

    const promise = client.pollTransactionStatus(MOCK_HASH);
    await vi.runAllTimersAsync();
    const result = await promise;

    expect(result.status).toBe(rpc.Api.GetTransactionStatus.SUCCESS);
    expect(client.rpcServer.getTransaction).toHaveBeenCalledTimes(1);
  });

  it("resolves immediately on first attempt if FAILED", async () => {
    vi.spyOn(client.rpcServer, "getTransaction").mockResolvedValue(
      FAILED_RESPONSE
    );

    const promise = client.pollTransactionStatus(MOCK_HASH);
    await vi.runAllTimersAsync();
    const result = await promise;

    expect(result.status).toBe(rpc.Api.GetTransactionStatus.FAILED);
    expect(client.rpcServer.getTransaction).toHaveBeenCalledTimes(1);
  });

  it("polls until NOT_FOUND becomes SUCCESS", async () => {
    vi.spyOn(client.rpcServer, "getTransaction")
      .mockResolvedValueOnce(NOT_FOUND_RESPONSE)
      .mockResolvedValueOnce(NOT_FOUND_RESPONSE)
      .mockResolvedValueOnce(SUCCESS_RESPONSE);

    const promise = client.pollTransactionStatus(MOCK_HASH, {
      maxAttempts: 5,
      delayMs: 100,
    });
    await vi.runAllTimersAsync();
    const result = await promise;

    expect(result.status).toBe(rpc.Api.GetTransactionStatus.SUCCESS);
    expect(client.rpcServer.getTransaction).toHaveBeenCalledTimes(3);
  });

  it("throws after exhausting maxAttempts with all NOT_FOUND", async () => {
    vi.spyOn(client.rpcServer, "getTransaction").mockResolvedValue(
      NOT_FOUND_RESPONSE
    );

    const maxAttempts = 4;
    const promise = client.pollTransactionStatus(MOCK_HASH, {
      maxAttempts,
      delayMs: 50,
    });
    await vi.runAllTimersAsync();

    await expect(promise).rejects.toThrow(
      `not found after ${maxAttempts} attempt(s)`
    );
    expect(client.rpcServer.getTransaction).toHaveBeenCalledTimes(maxAttempts);
  });

  it("resolves on the very last allowed attempt (boundary test)", async () => {
    const maxAttempts = 3;
    vi.spyOn(client.rpcServer, "getTransaction")
      .mockResolvedValueOnce(NOT_FOUND_RESPONSE)
      .mockResolvedValueOnce(NOT_FOUND_RESPONSE)
      .mockResolvedValueOnce(SUCCESS_RESPONSE);

    const promise = client.pollTransactionStatus(MOCK_HASH, {
      maxAttempts,
      delayMs: 50,
    });
    await vi.runAllTimersAsync();
    const result = await promise;

    expect(result.status).toBe(rpc.Api.GetTransactionStatus.SUCCESS);
    expect(client.rpcServer.getTransaction).toHaveBeenCalledTimes(3);
  });

  it("uses default maxAttempts=10 when no options provided", async () => {
    vi.spyOn(client.rpcServer, "getTransaction").mockResolvedValue(
      NOT_FOUND_RESPONSE
    );

    const promise = client.pollTransactionStatus(MOCK_HASH);
    await vi.runAllTimersAsync();

    await expect(promise).rejects.toThrow("after 10 attempt(s)");
    expect(client.rpcServer.getTransaction).toHaveBeenCalledTimes(10);
  });

  it("throws immediately when hash is empty", async () => {
    await expect(
      client.pollTransactionStatus("", { maxAttempts: 1, delayMs: 0 })
    ).rejects.toThrow("hash");
  });

  it("applies exponential backoff delays correctly", async () => {
    vi.spyOn(client.rpcServer, "getTransaction")
      .mockResolvedValueOnce(NOT_FOUND_RESPONSE)
      .mockResolvedValueOnce(NOT_FOUND_RESPONSE)
      .mockResolvedValueOnce(SUCCESS_RESPONSE);

    const setTimeoutSpy = vi.spyOn(global, "setTimeout");

    const promise = client.pollTransactionStatus(MOCK_HASH, {
      maxAttempts: 5,
      delayMs: 200,
      exponentialBackoff: true,
    });
    await vi.runAllTimersAsync();
    await promise;

    const delays = setTimeoutSpy.mock.calls.map((c) => c[1] as number);
    expect(delays).toContain(200);
    expect(delays).toContain(400);
  });
});

// ─── 4. signAndSubmit ─────────────────────────────────────────────────────────

describe("SorobanClient — signAndSubmit", () => {
  let client: SorobanClient;

  beforeEach(() => {
    vi.useFakeTimers();
    client = makeClient();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("executes simulate -> sign -> sendTransaction -> poll flow seamlessly", async () => {
    const dummyTx = buildDummyTx();
    const signedTx = buildDummyTx();
    const signedXdr = signedTx.toXDR();

    // 1. Mock simulation
    vi.spyOn(client, "simulateTransaction").mockResolvedValue({
      raw: {} as any,
      returnValue: undefined,
      minResourceFee: "100",
      success: true,
    });

    // 2. Mock wallet adapter
    const mockWallet: WalletAdapter = {
      name: "MockWallet",
      isAvailable: vi.fn().mockReturnValue(true),
      connect: vi.fn().mockResolvedValue("GBTY..."),
      signTransaction: vi.fn().mockResolvedValue(signedXdr),
    };

    // 3. Mock sendTransaction
    vi.spyOn(client.rpcServer, "sendTransaction").mockResolvedValue({
      status: rpc.Api.SendTransactionStatus.PENDING,
      hash: MOCK_HASH,
      latestLedger: 100,
      latestLedgerCloseTime: 0,
    } as any);

    // 4. Mock polling
    vi.spyOn(client.rpcServer, "getTransaction").mockResolvedValue(SUCCESS_RESPONSE);

    const promise = client.signAndSubmit(dummyTx, mockWallet);
    await vi.runAllTimersAsync();
    const result = await promise;

    expect(result.status).toBe(rpc.Api.GetTransactionStatus.SUCCESS);
    expect(client.simulateTransaction).toHaveBeenCalledWith(dummyTx);
    expect(mockWallet.signTransaction).toHaveBeenCalledWith(dummyTx.toXDR(), {
      networkPassphrase: client.networkPassphrase,
    });
    expect(client.rpcServer.sendTransaction).toHaveBeenCalled();
    expect(client.rpcServer.getTransaction).toHaveBeenCalledWith(MOCK_HASH);
  });

  it("accepts string XDR as input", async () => {
    const dummyTx = buildDummyTx();
    const signedTx = buildDummyTx();
    const unsignedXdr = dummyTx.toXDR();
    const signedXdr = signedTx.toXDR();

    vi.spyOn(client, "simulateTransaction").mockResolvedValue({
      raw: {} as any,
      returnValue: undefined,
      minResourceFee: "100",
      success: true,
    });

    const mockWallet: WalletAdapter = {
      name: "MockWallet",
      isAvailable: vi.fn().mockReturnValue(true),
      connect: vi.fn(),
      signTransaction: vi.fn().mockResolvedValue(signedXdr),
    };

    vi.spyOn(client.rpcServer, "sendTransaction").mockResolvedValue({
      status: rpc.Api.SendTransactionStatus.PENDING,
      hash: MOCK_HASH,
      latestLedger: 100,
      latestLedgerCloseTime: 0,
    } as any);

    vi.spyOn(client.rpcServer, "getTransaction").mockResolvedValue(SUCCESS_RESPONSE);

    const promise = client.signAndSubmit(unsignedXdr, mockWallet);
    await vi.runAllTimersAsync();
    const result = await promise;

    expect(result.status).toBe(rpc.Api.GetTransactionStatus.SUCCESS);
  });

  it("throws when wallet adapter is missing", async () => {
    const dummyTx = buildDummyTx();
    await expect(client.signAndSubmit(dummyTx, null as any)).rejects.toThrow(
      "signAndSubmit: A valid `WalletAdapter` instance must be provided."
    );
  });

  it("throws when tx string is empty", async () => {
    const mockWallet = { signTransaction: vi.fn() } as any;
    await expect(client.signAndSubmit("", mockWallet)).rejects.toThrow(
      "signAndSubmit: `tx` XDR string must not be empty."
    );
  });

  it("throws descriptive error when simulation fails", async () => {
    const dummyTx = buildDummyTx();
    vi.spyOn(client, "simulateTransaction").mockRejectedValue(new Error("contract error: out of gas"));

    const mockWallet: WalletAdapter = {
      name: "MockWallet",
      isAvailable: vi.fn().mockReturnValue(true),
      connect: vi.fn(),
      signTransaction: vi.fn(),
    };

    await expect(client.signAndSubmit(dummyTx, mockWallet)).rejects.toThrow(
      "contract error: out of gas"
    );
  });

  it("throws descriptive error when wallet signing throws", async () => {
    const dummyTx = buildDummyTx();
    vi.spyOn(client, "simulateTransaction").mockResolvedValue({
      raw: {} as any,
      returnValue: undefined,
      minResourceFee: "100",
      success: true,
    });

    const mockWallet: WalletAdapter = {
      name: "MockWallet",
      isAvailable: vi.fn().mockReturnValue(true),
      connect: vi.fn(),
      signTransaction: vi.fn().mockRejectedValue(new Error("User rejected prompt")),
    };

    await expect(client.signAndSubmit(dummyTx, mockWallet)).rejects.toThrow(
      "signAndSubmit: Wallet signing failed — User rejected prompt"
    );
  });

  it("throws descriptive error when sendTransaction returns ERROR status", async () => {
    const dummyTx = buildDummyTx();
    const signedTx = buildDummyTx();

    vi.spyOn(client, "simulateTransaction").mockResolvedValue({
      raw: {} as any,
      returnValue: undefined,
      minResourceFee: "100",
      success: true,
    });

    const mockWallet: WalletAdapter = {
      name: "MockWallet",
      isAvailable: vi.fn().mockReturnValue(true),
      connect: vi.fn(),
      signTransaction: vi.fn().mockResolvedValue(signedTx.toXDR()),
    };

    vi.spyOn(client.rpcServer, "sendTransaction").mockResolvedValue({
      status: rpc.Api.SendTransactionStatus.ERROR,
      hash: MOCK_HASH,
      latestLedger: 100,
      latestLedgerCloseTime: 0,
      errorResult: {
        toXDR: () => "error_xdr_payload",
      } as any,
    } as any);

    await expect(client.signAndSubmit(dummyTx, mockWallet)).rejects.toThrow(
      "signAndSubmit: RPC sendTransaction rejected with ERROR status: error_xdr_payload"
    );
  });
});

// ─── 5. getAccount ────────────────────────────────────────────────────────────

describe("SorobanClient — getAccount", () => {
  let client: SorobanClient;

  beforeEach(() => {
    client = makeClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("delegates to rpc.Server.getAccount and returns result", async () => {
    const mockAccount = { accountId: () => "GABC", sequenceNumber: () => "1" } as any;
    vi.spyOn(client.rpcServer, "getAccount").mockResolvedValue(mockAccount);

    const result = await client.getAccount("GABC...");
    expect(result).toBe(mockAccount);
  });

  it("throws descriptive error on RPC failure", async () => {
    vi.spyOn(client.rpcServer, "getAccount").mockRejectedValue(
      new Error("account not found")
    );

    await expect(client.getAccount("GABC...")).rejects.toThrow(
      "getAccount failed for GABC..."
    );
  });

  it("throws when publicKey is empty", async () => {
    await expect(client.getAccount("")).rejects.toThrow("publicKey");
  });
});

// ─── 6. getLatestLedger ───────────────────────────────────────────────────────

describe("SorobanClient — getLatestLedger", () => {
  let client: SorobanClient;

  beforeEach(() => {
    client = makeClient();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns the latest ledger info from RPC", async () => {
    const mockLedger = { sequence: 12345, id: "abc", protocolVersion: 20 } as any;
    vi.spyOn(client.rpcServer, "getLatestLedger").mockResolvedValue(mockLedger);

    const result = await client.getLatestLedger();
    expect(result.sequence).toBe(12345);
  });

  it("throws when RPC fails", async () => {
    vi.spyOn(client.rpcServer, "getLatestLedger").mockRejectedValue(
      new Error("503 Service Unavailable")
    );

    await expect(client.getLatestLedger()).rejects.toThrow("getLatestLedger failed");
  });
});

// ─── 7. Utility: isSimulationError ───────────────────────────────────────────

describe("isSimulationError", () => {
  it("returns true for error-shaped responses", () => {
    const err = { error: "host trapped", latestLedger: 1 } as any;
    expect(isSimulationError(err)).toBe(true);
  });

  it("returns false for success-shaped responses", () => {
    const ok = { minResourceFee: "100", result: {}, latestLedger: 1 } as any;
    expect(isSimulationError(ok)).toBe(false);
  });

  it("returns false when error field is undefined", () => {
    const ok = { error: undefined, latestLedger: 1 } as any;
    expect(isSimulationError(ok)).toBe(false);
  });
});

// ─── 8. Utility: decodeScVal ─────────────────────────────────────────────────

describe("decodeScVal", () => {
  it("returns undefined for undefined input", () => {
    expect(decodeScVal(undefined)).toBeUndefined();
  });

  it("returns undefined for null input", () => {
    expect(decodeScVal(null)).toBeUndefined();
  });

  it("returns undefined for empty string", () => {
    expect(decodeScVal("")).toBeUndefined();
  });

  it("returns undefined for invalid base64 XDR", () => {
    expect(decodeScVal("not!!valid!!xdr")).toBeUndefined();
  });

  it("decodes a valid i32 ScVal correctly", () => {
    const original = xdr.ScVal.scvI32(42);
    const base64 = original.toXDR("base64");
    const decoded = decodeScVal(base64);

    expect(decoded).toBeDefined();
    expect(decoded!.switch()).toBe(xdr.ScValType.scvI32());
    expect(decoded!.i32()).toBe(42);
  });

  it("decodes a valid bool ScVal correctly", () => {
    const original = xdr.ScVal.scvBool(true);
    const base64 = original.toXDR("base64");
    const decoded = decodeScVal(base64);

    expect(decoded).toBeDefined();
    expect(decoded!.b()).toBe(true);
  });
});

// ─── 9. Utility: resolveNetworkConfig ────────────────────────────────────────

describe("resolveNetworkConfig", () => {
  it("resolves TESTNET correctly", () => {
    const cfg = resolveNetworkConfig("TESTNET");
    expect(cfg.rpcUrl).toBe(RPC_ENDPOINTS.TESTNET);
    expect(cfg.networkPassphrase).toBe(Networks.TESTNET);
  });

  it("resolves MAINNET correctly", () => {
    const cfg = resolveNetworkConfig("MAINNET");
    expect(cfg.rpcUrl).toBe(RPC_ENDPOINTS.MAINNET);
    expect(cfg.networkPassphrase).toBe(Networks.PUBLIC);
  });

  it("resolves FUTURENET correctly", () => {
    const cfg = resolveNetworkConfig("FUTURENET");
    expect(cfg.rpcUrl).toBe(RPC_ENDPOINTS.FUTURENET);
    expect(cfg.networkPassphrase).toBe(Networks.FUTURENET);
  });
});
