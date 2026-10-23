import { describe, it, expect, vi, beforeEach } from "vitest";

const fetchFastTransferFeeBps = vi.fn();

vi.mock("../src/iris/poll.js", () => ({
  fetchFastTransferFeeBps: (...args: unknown[]) => fetchFastTransferFeeBps(...args),
}));

const { estimateFee } = await import("../src/estimate.js");

beforeEach(() => {
  vi.clearAllMocks();
});

describe("estimateFee", () => {
  it("returns a zero protocol fee for standard transfers without calling Iris", async () => {
    const estimate = await estimateFee({
      from: "arc",
      to: "stellar",
      amount: "100",
      speed: "standard",
    });

    expect(estimate).toMatchObject({ protocolFee: "0", transferMode: "standard" });
    expect(fetchFastTransferFeeBps).not.toHaveBeenCalled();
  });

  it("computes the protocol fee for fast transfers from the quoted basis points", async () => {
    fetchFastTransferFeeBps.mockResolvedValue(10); // 0.1%

    const estimate = await estimateFee({
      from: "arc",
      to: "stellar",
      amount: "100",
      speed: "fast",
    });

    expect(estimate.transferMode).toBe("fast");
    expect(estimate.protocolFee).toBe("0.1");
  });

  it("defaults to mainnet, quoting fees against the production Iris API", async () => {
    fetchFastTransferFeeBps.mockResolvedValue(10);

    await estimateFee({ from: "arc", to: "stellar", amount: "100", speed: "fast" });

    expect(fetchFastTransferFeeBps).toHaveBeenCalledWith(26, 27, false);
  });

  it("quotes against the sandbox Iris API when network is testnet", async () => {
    fetchFastTransferFeeBps.mockResolvedValue(10);

    await estimateFee({ from: "arc", to: "stellar", amount: "100", speed: "fast", network: "testnet" });

    expect(fetchFastTransferFeeBps).toHaveBeenCalledWith(26, 27, true);
  });

  it("falls back to standard when maxFee is below the quoted Iris fast fee", async () => {
    fetchFastTransferFeeBps.mockResolvedValue(10); // 0.1% -> 0.1 USDC on 100

    const estimate = await estimateFee({
      from: "arc",
      to: "stellar",
      amount: "100",
      speed: "fast",
      maxFee: "0.01",
    });

    expect(estimate).toEqual({
      protocolFee: "0",
      estimatedDurationSeconds: 20,
      transferMode: "standard",
    });
  });

  it("falls back to standard when maxWait is below the fast duration estimate without calling Iris", async () => {
    const estimate = await estimateFee({
      from: "arc",
      to: "stellar",
      amount: "100",
      speed: "fast",
      maxWait: 10,
    });

    expect(estimate).toEqual({
      protocolFee: "0",
      estimatedDurationSeconds: 20,
      transferMode: "standard",
    });
    expect(fetchFastTransferFeeBps).not.toHaveBeenCalled();
  });

  it("stays in fast mode when maxFee and maxWait both accommodate the fast transfer", async () => {
    fetchFastTransferFeeBps.mockResolvedValue(10); // 0.1% -> 0.1 USDC on 100

    const estimate = await estimateFee({
      from: "arc",
      to: "stellar",
      amount: "100",
      speed: "fast",
      maxFee: "0.1",
      maxWait: 15,
    });

    expect(estimate).toEqual({
      protocolFee: "0.1",
      estimatedDurationSeconds: 15,
      transferMode: "fast",
    });
  });
});
