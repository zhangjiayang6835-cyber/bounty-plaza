import { describe, expect, it, vi, beforeEach } from "vitest";
import { FreighterAdapter } from "../src/wallets/freighter";
import { StellarKitAdapter } from "../src/wallets/stellarkit";
import { signAndSubmit } from "../src/index";

vi.mock("@stellar/freighter-api", () => ({
  isConnected: vi.fn().mockResolvedValue(true),
  getPublicKey: vi.fn().mockResolvedValue("GABC"),
  signTransaction: vi.fn().mockResolvedValue("SIGNED_XDR"),
}));

describe("FreighterAdapter", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("throws descriptive error when extension missing", async () => {
    const adapter = new FreighterAdapter();
    await expect(adapter.connect()).rejects.toThrow(/not installed/i);
    await expect(adapter.signTransaction("xdr")).rejects.toThrow(/not installed/i);
  });
});

describe("StellarKitAdapter", () => {
  it("throws descriptive error when kit missing", async () => {
    const adapter = new StellarKitAdapter(undefined);
    await expect(adapter.connect()).rejects.toThrow(/not available/i);
    await expect(adapter.signTransaction("xdr")).rejects.toThrow(/not available/i);
  });

  it("signs via kit", async () => {
    const kit = {
      getPublicKey: vi.fn().mockResolvedValue("GXYZ"),
      signTransaction: vi.fn().mockResolvedValue("SIGNED"),
    };
    const adapter = new StellarKitAdapter(kit);
    expect(await adapter.connect()).toBe("GXYZ");
    expect(await adapter.signTransaction("xdr", { networkPassphrase: "pass" })).toBe("SIGNED");
    expect(kit.signTransaction).toHaveBeenCalledWith("xdr", { networkPassphrase: "pass" });
  });
});

describe("signAndSubmit", () => {
  it("signs and submits", async () => {
    const wallet = {
      name: "test",
      isAvailable: () => true,
      connect: vi.fn().mockResolvedValue("GKEY"),
      signTransaction: vi.fn().mockResolvedValue("SIGNED_XDR"),
    };
    const tx = { toXDR: () => "RAW_XDR" };
    const result = await signAndSubmit(tx, wallet, { networkPassphrase: "net" });
    expect(wallet.signTransaction).toHaveBeenCalledWith("RAW_XDR", { networkPassphrase: "net" });
    expect(result.hash).toBe("SIGNED_XDR");
  });
});
