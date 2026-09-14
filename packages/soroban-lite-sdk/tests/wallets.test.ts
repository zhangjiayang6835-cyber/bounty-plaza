/**
 * soroban-lite-sdk — tests/wallets.test.ts
 *
 * Unit tests for wallet integration adapters (FreighterAdapter and StellarKitAdapter).
 * Uses `vi.mock` for isolated testing without requiring browser extensions or DOM.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { FreighterAdapter } from "../src/wallets/freighter";
import { StellarKitAdapter } from "../src/wallets/stellarkit";
import { WalletAdapter } from "../src/wallets/types";

// ─── 1. FreighterAdapter Tests ────────────────────────────────────────────────

describe("FreighterAdapter", () => {
  const MOCK_PUBKEY = "GBTYNREJQLK3H3YMQK2F6U44EZW725O2X6Z2M5QEZQ6M6M6M6M6M6M6M";
  const MOCK_UNSIGNED_XDR = "AAAAAgAAAAD...mockUnsignedXdr...";
  const MOCK_SIGNED_XDR = "AAAAAgAAAAD...mockSignedXdr...";

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Properties & Availability", () => {
    it("has the name 'Freighter'", () => {
      const adapter = new FreighterAdapter();
      expect(adapter.name).toBe("Freighter");
    });

    it("returns true for isAvailable when API methods exist", () => {
      const mockApi = {
        isConnected: vi.fn().mockResolvedValue(true),
        getPublicKey: vi.fn().mockResolvedValue(MOCK_PUBKEY),
        signTransaction: vi.fn().mockResolvedValue(MOCK_SIGNED_XDR),
      };
      const adapter = new FreighterAdapter({ api: mockApi });
      expect(adapter.isAvailable()).toBe(true);
    });

    it("returns false for isAvailable when API is empty object", () => {
      const adapter = new FreighterAdapter({ api: {} });
      expect(adapter.isAvailable()).toBe(false);
    });
  });

  describe("connect()", () => {
    it("connects successfully and returns public key from string response", async () => {
      const mockApi = {
        isConnected: vi.fn().mockResolvedValue(true),
        getPublicKey: vi.fn().mockResolvedValue(MOCK_PUBKEY),
        signTransaction: vi.fn(),
      };
      const adapter = new FreighterAdapter({ api: mockApi });

      const pubKey = await adapter.connect();
      expect(pubKey).toBe(MOCK_PUBKEY);
      expect(mockApi.getPublicKey).toHaveBeenCalled();
    });

    it("connects successfully and returns public key from object response { address }", async () => {
      const mockApi = {
        isConnected: vi.fn().mockResolvedValue({ isConnected: true }),
        requestAccess: vi.fn().mockResolvedValue({ address: MOCK_PUBKEY }),
        signTransaction: vi.fn(),
      };
      const adapter = new FreighterAdapter({ api: mockApi });

      const pubKey = await adapter.connect();
      expect(pubKey).toBe(MOCK_PUBKEY);
      expect(mockApi.requestAccess).toHaveBeenCalled();
    });

    it("throws descriptive error when Freighter extension is not installed", async () => {
      const mockApi = {
        isConnected: vi.fn().mockResolvedValue(false),
        getPublicKey: vi.fn(),
        signTransaction: vi.fn(),
      };
      const adapter = new FreighterAdapter({ api: mockApi });

      await expect(adapter.connect()).rejects.toThrow(
        "FreighterAdapter: Freighter wallet extension is not installed or accessible."
      );
    });

    it("throws descriptive error when connection returns an error object", async () => {
      const mockApi = {
        isConnected: vi.fn().mockResolvedValue(true),
        requestAccess: vi.fn().mockResolvedValue({ error: "User declined access" }),
        signTransaction: vi.fn(),
      };
      const adapter = new FreighterAdapter({ api: mockApi });

      await expect(adapter.connect()).rejects.toThrow(
        "FreighterAdapter: Connection error — User declined access"
      );
    });

    it("throws descriptive error when connection throws an exception", async () => {
      const mockApi = {
        isConnected: vi.fn().mockResolvedValue(true),
        getPublicKey: vi.fn().mockRejectedValue(new Error("Popup blocked")),
        signTransaction: vi.fn(),
      };
      const adapter = new FreighterAdapter({ api: mockApi });

      await expect(adapter.connect()).rejects.toThrow(
        "FreighterAdapter: Connection failed — Popup blocked"
      );
    });
  });

  describe("signTransaction()", () => {
    it("signs transaction and returns signed XDR from string response", async () => {
      const mockApi = {
        isConnected: vi.fn().mockResolvedValue(true),
        signTransaction: vi.fn().mockResolvedValue(MOCK_SIGNED_XDR),
      };
      const adapter = new FreighterAdapter({ api: mockApi });

      const signed = await adapter.signTransaction(MOCK_UNSIGNED_XDR, {
        networkPassphrase: "Test SDF Network ; September 2015",
      });

      expect(signed).toBe(MOCK_SIGNED_XDR);
      expect(mockApi.signTransaction).toHaveBeenCalledWith(MOCK_UNSIGNED_XDR, {
        networkPassphrase: "Test SDF Network ; September 2015",
        network: undefined,
        accountToSign: undefined,
      });
    });

    it("signs transaction and returns signed XDR from object response { signedTxXdr }", async () => {
      const mockApi = {
        isConnected: vi.fn().mockResolvedValue(true),
        signTransaction: vi.fn().mockResolvedValue({ signedTxXdr: MOCK_SIGNED_XDR }),
      };
      const adapter = new FreighterAdapter({ api: mockApi });

      const signed = await adapter.signTransaction(MOCK_UNSIGNED_XDR);
      expect(signed).toBe(MOCK_SIGNED_XDR);
    });

    it("throws when xdr is empty string", async () => {
      const adapter = new FreighterAdapter();
      await expect(adapter.signTransaction("")).rejects.toThrow("FreighterAdapter: `xdr` must be a non-empty string.");
    });

    it("throws descriptive error when signing rejected with error in result object", async () => {
      const mockApi = {
        isConnected: vi.fn().mockResolvedValue(true),
        signTransaction: vi.fn().mockResolvedValue({ error: "User rejected transaction" }),
      };
      const adapter = new FreighterAdapter({ api: mockApi });

      await expect(adapter.signTransaction(MOCK_UNSIGNED_XDR)).rejects.toThrow(
        "FreighterAdapter: Signing rejected or failed — User rejected transaction"
      );
    });

    it("throws descriptive error when API signTransaction throws", async () => {
      const mockApi = {
        isConnected: vi.fn().mockResolvedValue(true),
        signTransaction: vi.fn().mockRejectedValue(new Error("Hardware wallet disconnected")),
      };
      const adapter = new FreighterAdapter({ api: mockApi });

      await expect(adapter.signTransaction(MOCK_UNSIGNED_XDR)).rejects.toThrow(
        "FreighterAdapter: Transaction signing failed — Hardware wallet disconnected"
      );
    });
  });
});

// ─── 2. StellarKitAdapter Tests ───────────────────────────────────────────────

describe("StellarKitAdapter", () => {
  const MOCK_PUBKEY = "GAAAZZZQQQKKK1112223334445556667778889990001112223334445556";
  const MOCK_UNSIGNED_XDR = "AAAAAgAAAAD...mockUnsignedXdr...";
  const MOCK_SIGNED_XDR = "AAAAAgAAAAD...mockSignedXdr...";

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Properties & Availability", () => {
    it("has the name 'StellarWalletsKit'", () => {
      const adapter = new StellarKitAdapter();
      expect(adapter.name).toBe("StellarWalletsKit");
    });

    it("returns true for isAvailable when kit instance is supplied", () => {
      const mockKit = {
        signTransaction: vi.fn(),
      };
      const adapter = new StellarKitAdapter({ kit: mockKit });
      expect(adapter.isAvailable()).toBe(true);
    });

    it("returns false for isAvailable when no kit or window object is provided", () => {
      const adapter = new StellarKitAdapter();
      expect(adapter.isAvailable()).toBe(false);
    });
  });

  describe("connect()", () => {
    it("opens modal and returns public key from getAddress", async () => {
      const mockKit = {
        openModal: vi.fn().mockResolvedValue(true),
        getAddress: vi.fn().mockResolvedValue({ address: MOCK_PUBKEY }),
        signTransaction: vi.fn(),
        setWallet: vi.fn(),
      };
      const adapter = new StellarKitAdapter({ kit: mockKit, modalTitle: "Select Wallet" });

      const pubKey = await adapter.connect();
      expect(pubKey).toBe(MOCK_PUBKEY);
      expect(mockKit.openModal).toHaveBeenCalled();
      expect(mockKit.getAddress).toHaveBeenCalled();
    });

    it("returns public key from getPublicKey method if getAddress is not present", async () => {
      const mockKit = {
        getPublicKey: vi.fn().mockResolvedValue(MOCK_PUBKEY),
        signTransaction: vi.fn(),
      };
      const adapter = new StellarKitAdapter(mockKit);

      const pubKey = await adapter.connect();
      expect(pubKey).toBe(MOCK_PUBKEY);
      expect(mockKit.getPublicKey).toHaveBeenCalled();
    });

    it("throws descriptive error when kit is not initialized", async () => {
      const adapter = new StellarKitAdapter();

      await expect(adapter.connect()).rejects.toThrow(
        "StellarKitAdapter: Stellar Wallets Kit is not available or initialized."
      );
    });

    it("throws descriptive error when modal connection fails", async () => {
      const mockKit = {
        openModal: vi.fn().mockRejectedValue(new Error("User closed modal")),
        signTransaction: vi.fn(),
      };
      const adapter = new StellarKitAdapter(mockKit);

      await expect(adapter.connect()).rejects.toThrow(
        "StellarKitAdapter: Connection failed — User closed modal"
      );
    });
  });

  describe("signTransaction()", () => {
    it("delegates signTransaction to kit and returns signed XDR string", async () => {
      const mockKit = {
        signTransaction: vi.fn().mockResolvedValue(MOCK_SIGNED_XDR),
      };
      const adapter = new StellarKitAdapter(mockKit);

      const signed = await adapter.signTransaction(MOCK_UNSIGNED_XDR, {
        networkPassphrase: "Test SDF Network ; September 2015",
      });

      expect(signed).toBe(MOCK_SIGNED_XDR);
      expect(mockKit.signTransaction).toHaveBeenCalledWith(MOCK_UNSIGNED_XDR, {
        networkPassphrase: "Test SDF Network ; September 2015",
        network: undefined,
        accountToSign: undefined,
      });
    });

    it("extracts signedTxXdr from object response", async () => {
      const mockKit = {
        signTransaction: vi.fn().mockResolvedValue({ signedTxXdr: MOCK_SIGNED_XDR }),
      };
      const adapter = new StellarKitAdapter(mockKit);

      const signed = await adapter.signTransaction(MOCK_UNSIGNED_XDR);
      expect(signed).toBe(MOCK_SIGNED_XDR);
    });

    it("throws when xdr is empty string", async () => {
      const adapter = new StellarKitAdapter({ signTransaction: vi.fn() } as any);
      await expect(adapter.signTransaction("")).rejects.toThrow("StellarKitAdapter: `xdr` must be a non-empty string.");
    });

    it("throws descriptive error when kit signTransaction throws", async () => {
      const mockKit = {
        signTransaction: vi.fn().mockRejectedValue(new Error("Signing cancelled by user")),
      };
      const adapter = new StellarKitAdapter(mockKit);

      await expect(adapter.signTransaction(MOCK_UNSIGNED_XDR)).rejects.toThrow(
        "StellarKitAdapter: Transaction signing failed — Signing cancelled by user"
      );
    });
  });
});
