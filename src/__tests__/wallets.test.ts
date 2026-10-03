import { describe, it, expect, vi, beforeEach } from "vitest";
import { FreighterAdapter, StellarKitAdapter } from "../wallets";
import type { WalletAdapter } from "../wallets";

vi.mock("@stellar/freighter-api", () => ({
  getPublicAddress: vi.fn().mockResolvedValue("GABCDEFGHIJKLMNOPQRSTUVWXYZ"),
  signTransaction: vi.fn().mockResolvedValue("signed-xdr-freighter"),
}));

vi.mock("@creit.tech/stellar-wallets-kit", () => ({
  StellarWalletsKit: vi.fn().mockImplementation(() => ({
    connect: vi.fn().mockResolvedValue("GQRSTUVWXYZABCDEFghijklmnop"),
    signTransaction: vi.fn().mockResolvedValue("signed-xdr-kit"),
  })),
  Networks: { STANDALONE: "standalone", PUBLIC: "Public Network" },
  SEP10Challenge: vi.fn(),
}));

describe("FreighterAdapter", () => {
  let adapter: WalletAdapter;

  beforeEach(() => {
    vi.stubGlobal("freighterAPI", {});
    adapter = new FreighterAdapter();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("isAvailable returns true when extension is present", () => {
    expect(adapter.isAvailable()).toBe(true);
  });

  it("throws descriptive error when extension is not installed", async () => {
    vi.unstubAllGlobals();
    const noExt = new FreighterAdapter();
    expect(noExt.isAvailable()).toBe(false);
    await expect(noExt.connect()).rejects.toThrow("Freighter wallet extension is not installed");
    await expect(noExt.signTransaction("xdr")).rejects.toThrow("Freighter wallet extension is not installed");
  });

  it("connect returns the public address", async () => {
    const addr = await adapter.connect();
    expect(addr).toBe("GABCDEFGHIJKLMNOPQRSTUVWXYZ");
  });

  it("signTransaction returns signed XDR", async () => {
    const result = await adapter.signTransaction("my-xdr", { networkPassphrase: "test" });
    expect(result).toBe("signed-xdr-freighter");
  });
});

describe("StellarKitAdapter", () => {
  let adapter: WalletAdapter;

  beforeEach(() => {
    vi.stubGlobal("stellarWalletsKit", {});
    adapter = new StellarKitAdapter();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("isAvailable returns true when kit is present", () => {
    expect(adapter.isAvailable()).toBe(true);
  });

  it("throws descriptive error when kit is not installed", async () => {
    vi.unstubAllGlobals();
    const noKit = new StellarKitAdapter();
    expect(noKit.isAvailable()).toBe(false);
    await expect(noKit.connect()).rejects.toThrow();
    await expect(noKit.signTransaction("xdr")).rejects.toThrow();
  });

  it("connect returns the address", async () => {
    const addr = await adapter.connect();
    expect(addr).toBe("GQRSTUVWXYZABCDEFghijklmnop");
  });

  it("signTransaction returns signed XDR", async () => {
    const result = await adapter.signTransaction("my-xdr");
    expect(result).toBe("signed-xdr-kit");
  });
});
