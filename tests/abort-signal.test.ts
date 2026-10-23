import { describe, it, expect, vi, beforeEach } from "vitest";

const approveUsdcOnArc = vi.fn();
const getUsdcAllowanceOnArc = vi.fn();
const burnUsdcOnArc = vi.fn();
const burnUsdcOnArcWithStellarForward = vi.fn();
const receiveMessageOnArc = vi.fn();
const approveUsdcOnStellar = vi.fn();
const burnUsdcOnStellar = vi.fn();
const mintAndForwardOnStellar = vi.fn();
const checkStellarRecipientReady = vi.fn();
const fetchFastTransferFeeBps = vi.fn();
const pollForAttestationMock = vi.fn();
const getAttestationMock = vi.fn();

vi.mock("../src/chains/arc.js", () => ({
  approveUsdcOnArc: (...args: unknown[]) => approveUsdcOnArc(...args),
  getUsdcAllowanceOnArc: (...args: unknown[]) => getUsdcAllowanceOnArc(...args),
  burnUsdcOnArc: (...args: unknown[]) => burnUsdcOnArc(...args),
  burnUsdcOnArcWithStellarForward: (...args: unknown[]) => burnUsdcOnArcWithStellarForward(...args),
  receiveMessageOnArc: (...args: unknown[]) => receiveMessageOnArc(...args),
}));

vi.mock("../src/chains/stellar.js", () => ({
  approveUsdcOnStellar: (...args: unknown[]) => approveUsdcOnStellar(...args),
  burnUsdcOnStellar: (...args: unknown[]) => burnUsdcOnStellar(...args),
  mintAndForwardOnStellar: (...args: unknown[]) => mintAndForwardOnStellar(...args),
  checkStellarRecipientReady: (...args: unknown[]) => checkStellarRecipientReady(...args),
}));

vi.mock("../src/iris/poll.js", () => ({
  fetchFastTransferFeeBps: (...args: unknown[]) => fetchFastTransferFeeBps(...args),
  pollForAttestation: (...args: unknown[]) => pollForAttestationMock(...args),
  getAttestation: (...args: unknown[]) => getAttestationMock(...args),
}));

const { transfer, completeMint, resolveBurn } = await import("../src/transfer.js");
const { TransferError } = await import("../src/errors.js");
const { encodeStellarForwardHook } = await import("../src/utils/encoding.js");

const FORWARD_RECIPIENT = "GCY3PLGZQZWVKQELW7GCHQVLVZGRMGI5R4HODX6QZM7ETJSPHBFVJPY2";

function buildBurnMessage(options: { forwardRecipient?: string } = {}): `0x${string}` {
  const header = Buffer.alloc(148);
  header.writeUInt32BE(1, 0);
  header.writeUInt32BE(26, 4);
  header.writeUInt32BE(27, 8);

  const body = Buffer.alloc(228);
  body.writeUInt32BE(1, 0);

  const hook =
    options.forwardRecipient === undefined
      ? Buffer.alloc(0)
      : Buffer.from(encodeStellarForwardHook(options.forwardRecipient).slice(2), "hex");

  return `0x${Buffer.concat([header, body, hook]).toString("hex")}`;
}

const arcSigner = { walletClient: {} } as any;
const stellarSigner = { publicKey: "GABCD" } as any;

describe("AbortSignal support across transfer, completeMint, and resolveBurn", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getUsdcAllowanceOnArc.mockResolvedValue(0n);
    approveUsdcOnArc.mockResolvedValue("0xapprovehash");
    burnUsdcOnArc.mockResolvedValue("0xburnhash");
    burnUsdcOnArcWithStellarForward.mockResolvedValue("0xburnhookhash");
    approveUsdcOnStellar.mockResolvedValue("stellarapprovehash");
    burnUsdcOnStellar.mockResolvedValue("stellarburnhash");
    checkStellarRecipientReady.mockResolvedValue({ exists: true, hasTrustline: true, ready: true });
    pollForAttestationMock.mockResolvedValue({
      message: buildBurnMessage({ forwardRecipient: FORWARD_RECIPIENT }),
      attestation: "0xattestation",
    });
    getAttestationMock.mockResolvedValue({
      message: buildBurnMessage({ forwardRecipient: FORWARD_RECIPIENT }),
      attestation: "0xattestation",
    });
  });

  describe("transfer() - pre-burn abort", () => {
    it("throws plain AbortError immediately when signal is already aborted before starting", async () => {
      const controller = new AbortController();
      controller.abort();

      await expect(
        transfer({
          from: "arc",
          to: "stellar",
          amount: "10.00",
          recipient: FORWARD_RECIPIENT,
          signer: arcSigner,
          speed: "standard",
          options: { signal: controller.signal },
        }),
      ).rejects.toSatisfy((err: any) => {
        expect(err).not.toBeInstanceOf(TransferError);
        expect(err.name === "AbortError" || /aborted/i.test(err.message)).toBe(true);
        return true;
      });

      expect(approveUsdcOnArc).not.toHaveBeenCalled();
      expect(burnUsdcOnArcWithStellarForward).not.toHaveBeenCalled();
    });

    it("throws plain AbortError if aborted during fast fee calculation before burn", async () => {
      const controller = new AbortController();
      fetchFastTransferFeeBps.mockImplementation(async () => {
        controller.abort();
        throw new DOMException("The operation was aborted", "AbortError");
      });

      await expect(
        transfer({
          from: "arc",
          to: "stellar",
          amount: "10.00",
          recipient: FORWARD_RECIPIENT,
          signer: arcSigner,
          speed: "fast",
          options: { signal: controller.signal },
        }),
      ).rejects.toSatisfy((err: any) => {
        expect(err).not.toBeInstanceOf(TransferError);
        expect(err.name === "AbortError" || /aborted/i.test(err.message)).toBe(true);
        return true;
      });

      expect(burnUsdcOnArcWithStellarForward).not.toHaveBeenCalled();
    });
  });

  describe("transfer() - post-burn abort", () => {
    it("throws TransferError with burnTxHash and code='TRANSFER_ABORTED' if aborted during attestation polling", async () => {
      const controller = new AbortController();

      burnUsdcOnArcWithStellarForward.mockResolvedValue("0xrealburnhash123");

      pollForAttestationMock.mockImplementation(async () => {
        controller.abort();
        const err = new DOMException("The operation was aborted", "AbortError");
        throw err;
      });

      let caughtError: any;
      try {
        await transfer({
          from: "arc",
          to: "stellar",
          amount: "10.00",
          recipient: FORWARD_RECIPIENT,
          signer: arcSigner,
          speed: "standard",
          options: { signal: controller.signal },
        });
      } catch (err) {
        caughtError = err;
      }

      expect(caughtError).toBeInstanceOf(TransferError);
      expect(caughtError.burnTxHash).toBe("0xrealburnhash123");
      expect(caughtError.code).toBe("TRANSFER_ABORTED");
      expect(caughtError.name).toBe("TransferError");
      expect(caughtError.attestationHash).toBeUndefined();
    });

    it("throws TransferError with burnTxHash, attestationHash, and code='TRANSFER_ABORTED' if aborted during destination mint", async () => {
      const controller = new AbortController();

      burnUsdcOnArcWithStellarForward.mockResolvedValue("0xrealburnhash456");
      pollForAttestationMock.mockResolvedValue({
        message: buildBurnMessage({ forwardRecipient: FORWARD_RECIPIENT }),
        attestation: "0xattestation789",
      });

      mintAndForwardOnStellar.mockImplementation(async () => {
        controller.abort();
        throw new DOMException("The operation was aborted", "AbortError");
      });

      let caughtError: any;
      try {
        await transfer({
          from: "arc",
          to: "stellar",
          amount: "10.00",
          recipient: FORWARD_RECIPIENT,
          signer: arcSigner,
          speed: "standard",
          options: {
            destinationSigner: stellarSigner,
            signal: controller.signal,
          },
        });
      } catch (err) {
        caughtError = err;
      }

      expect(caughtError).toBeInstanceOf(TransferError);
      expect(caughtError.burnTxHash).toBe("0xrealburnhash456");
      expect(caughtError.attestationHash).toBe("0xattestation789");
      expect(caughtError.code).toBe("TRANSFER_ABORTED");
    });
  });

  describe("completeMint() - AbortSignal support", () => {
    it("throws plain AbortError when signal is aborted before completeMint starts", async () => {
      const controller = new AbortController();
      controller.abort();

      await expect(
        completeMint({
          from: "arc",
          to: "stellar",
          burnTxHash: "0xburnhash",
          signer: stellarSigner,
          options: { signal: controller.signal },
        }),
      ).rejects.toSatisfy((err: any) => {
        expect(err.name === "AbortError" || /aborted/i.test(err.message)).toBe(true);
        return true;
      });

      expect(pollForAttestationMock).not.toHaveBeenCalled();
    });

    it("supports top-level signal param on CompleteMintParams", async () => {
      const controller = new AbortController();
      controller.abort();

      await expect(
        completeMint({
          from: "arc",
          to: "stellar",
          burnTxHash: "0xburnhash",
          signer: stellarSigner,
          signal: controller.signal,
        }),
      ).rejects.toSatisfy((err: any) => {
        expect(err.name === "AbortError" || /aborted/i.test(err.message)).toBe(true);
        return true;
      });

      expect(pollForAttestationMock).not.toHaveBeenCalled();
    });
  });

  describe("resolveBurn() - AbortSignal support", () => {
    it("throws plain AbortError when signal is aborted before resolveBurn starts", async () => {
      const controller = new AbortController();
      controller.abort();

      await expect(
        resolveBurn({
          from: "arc",
          burnTxHash: "0xburnhash",
          signal: controller.signal,
        }),
      ).rejects.toSatisfy((err: any) => {
        expect(err.name === "AbortError" || /aborted/i.test(err.message)).toBe(true);
        return true;
      });

      expect(getAttestationMock).not.toHaveBeenCalled();
    });
  });
});
