import { describe, it, expect, vi } from "vitest";
import {
  pollTransactionStatus,
  SubmissionTimeoutError,
  STELLAR_CONFIRMATION_MAX_CONSECUTIVE_RPC_FAILURES,
  STELLAR_CONFIRMATION_RETRY_DELAY_MS,
  type StellarRpcServer,
} from "./stellar.js";

const FAKE_HASH = "0x9876543210abcdef9876543210abcdef9876543210abcdef9876543210abcdef";

describe("confirmation polling under transient RPC errors", () => {
  it("constants match spec", () => {
    expect(STELLAR_CONFIRMATION_MAX_CONSECUTIVE_RPC_FAILURES).toBe(5);
    expect(STELLAR_CONFIRMATION_RETRY_DELAY_MS).toBe(1000);
  });

  it("rides out N-1 transient getTransaction failures and resolves once the RPC recovers", async () => {
    vi.useFakeTimers();
    try {
      const getTx = vi
        .fn()
        .mockRejectedValueOnce(new Error("connect ECONNRESET"))
        .mockRejectedValueOnce(new Error("503 Service Unavailable"))
        .mockRejectedValueOnce(new Error("socket hang up"))
        .mockRejectedValueOnce(new Error("connect ECONNRESET"))
        .mockResolvedValueOnce({ status: "SUCCESS" });

      const server: StellarRpcServer = { getTransaction: getTx };

      const pollPromise = pollTransactionStatus(server, FAKE_HASH);
      const assertion = expect(pollPromise).resolves.toBe(FAKE_HASH);

      await vi.runAllTimersAsync();
      await assertion;

      expect(getTx).toHaveBeenCalledTimes(5);
    } finally {
      vi.useRealTimers();
    }
  });

  it("rejects with SubmissionTimeoutError carrying the hash when the RPC never recovers", async () => {
    vi.useFakeTimers();
    try {
      const getTx = vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED"));
      const server: StellarRpcServer = { getTransaction: getTx };

      const pollPromise = pollTransactionStatus(server, FAKE_HASH);
      const assertion = expect(pollPromise).rejects.toBeInstanceOf(SubmissionTimeoutError);

      await vi.runAllTimersAsync();
      await assertion;

      const err = (await pollPromise.catch((e: unknown) => e)) as SubmissionTimeoutError;
      expect(err.hash).toBe(FAKE_HASH);
      expect(getTx).toHaveBeenCalledTimes(5);
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps throwing immediately on FAILED without entering the retry loop", async () => {
    vi.useFakeTimers();
    try {
      const getTx = vi.fn().mockResolvedValue({ status: "FAILED" });
      const server: StellarRpcServer = { getTransaction: getTx };

      const pollPromise = pollTransactionStatus(server, FAKE_HASH);
      const assertion = expect(pollPromise).rejects.toThrow(/failed/);

      await vi.runAllTimersAsync();
      await assertion;

      expect(getTx).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });
});
