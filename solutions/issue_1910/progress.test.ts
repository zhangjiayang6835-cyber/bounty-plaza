import { describe, it, expect, vi } from "vitest";
import { transfer } from "./transfer.js";
import type { TransferProgressEvent } from "./types.js";

const STELLAR_RECIPIENT = "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5";

describe("transfer() progress callbacks", () => {
  it("emits the expected sequence of stage events in order with payloads", async () => {
    const events: TransferProgressEvent[] = [];
    const onProgress = vi.fn((ev: TransferProgressEvent) => {
      events.push(ev);
    });

    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: STELLAR_RECIPIENT,
      signer: { address: "0x111" },
      options: {
        destinationSigner: { publicKey: STELLAR_RECIPIENT },
        onProgress,
      },
    });

    expect(result.status).toBe("success");
    expect(result.burnTxHash).toBe("0xburnhash");
    expect(result.mintTxHash).toBe("0xminthash");

    expect(onProgress).toHaveBeenCalledTimes(7);
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

    const burnConfirmed = events.find((e) => e.stage === "burn-confirmed");
    expect(burnConfirmed).toBeDefined();
    if (burnConfirmed && "burnTxHash" in burnConfirmed) {
      expect(burnConfirmed.burnTxHash).toBe("0xburnhash");
    }

    const mintConfirmed = events.find((e) => e.stage === "mint-confirmed");
    expect(mintConfirmed).toBeDefined();
    if (mintConfirmed && "mintTxHash" in mintConfirmed) {
      expect(mintConfirmed.burnTxHash).toBe("0xburnhash");
      expect(mintConfirmed.mintTxHash).toBe("0xminthash");
    }
  });

  it("swallows exceptions thrown by onProgress without breaking the transfer", async () => {
    const explodingCallback = vi.fn(() => {
      throw new Error("Consumer listener exploded!");
    });

    const result = await transfer({
      from: "arc",
      to: "stellar",
      amount: "10",
      recipient: STELLAR_RECIPIENT,
      signer: { address: "0x111" },
      options: {
        onProgress: explodingCallback,
      },
    });

    expect(result.status).toBe("pending");
    expect(result.burnTxHash).toBe("0xburnhash");
    expect(explodingCallback).toHaveBeenCalled();
  });
});
