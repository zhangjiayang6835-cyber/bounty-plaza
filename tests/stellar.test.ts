import { describe, it, expect, vi, afterEach } from "vitest";
import { rpc } from "@stellar/stellar-sdk";
import {
  pollTransactionStatus,
  STELLAR_RPC_MAX_CONSECUTIVE_FAILURES,
} from "../src/chains/stellar.js";
import { SubmissionTimeoutError } from "../src/errors.js";

const FAKE_HASH = "a".repeat(64);

afterEach(() => {
  vi.restoreAllMocks();
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

  it("rejects with SubmissionTimeoutError carrying hash when AbortSignal is aborted", async () => {
    const server = new rpc.Server("https://mock-stellar.local");
    const controller = new AbortController();
    controller.abort();

    const promise = pollTransactionStatus(server, FAKE_HASH, {
      pollIntervalMs: 5,
      signal: controller.signal,
    });

    await expect(promise).rejects.toThrow(SubmissionTimeoutError);
    await expect(promise).rejects.toMatchObject({
      hash: FAKE_HASH,
    });
  });
});
