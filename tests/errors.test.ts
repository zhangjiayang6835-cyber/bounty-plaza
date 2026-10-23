import { describe, it, expect } from "vitest";
import {
  TransferError,
  AttestationNotReadyError,
  IrisRequestError,
  SubmissionTimeoutError,
  type TransferErrorCode,
} from "../src/errors.js";

describe("TransferError", () => {
  it("populates required fields and leaves optional fields undefined when omitted", () => {
    const err = new TransferError("mint failed", "0xburn123");

    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(TransferError);
    expect(Object.getPrototypeOf(err)).toBe(TransferError.prototype);
    expect(err.name).toBe("TransferError");
    expect(err.message).toBe("mint failed");
    expect(err.burnTxHash).toBe("0xburn123");
    expect(err.attestationHash).toBeUndefined();
    expect(err.code).toBeUndefined();
    expect(typeof err.stack).toBe("string");
  });

  it("populates attestationHash and code when provided", () => {
    const code: TransferErrorCode = "ATTESTATION_NOT_READY";
    const err = new TransferError("still attesting", "0xburn456", "0xatt789", code);

    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(TransferError);
    expect(err.name).toBe("TransferError");
    expect(err.message).toBe("still attesting");
    expect(err.burnTxHash).toBe("0xburn456");
    expect(err.attestationHash).toBe("0xatt789");
    expect(err.code).toBe("ATTESTATION_NOT_READY");
  });

  it("supports passing code with undefined attestationHash", () => {
    const err = new TransferError("poll timed out", "0xburn999", undefined, "ATTESTATION_NOT_READY");

    expect(err.burnTxHash).toBe("0xburn999");
    expect(err.attestationHash).toBeUndefined();
    expect(err.code).toBe("ATTESTATION_NOT_READY");
  });
});

describe("AttestationNotReadyError", () => {
  it("populates message, burnTxHash, name, and prototype chain", () => {
    const err = new AttestationNotReadyError("not indexed yet", "0xburnabc");

    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(AttestationNotReadyError);
    expect(err).not.toBeInstanceOf(TransferError);
    expect(Object.getPrototypeOf(err)).toBe(AttestationNotReadyError.prototype);
    expect(err.name).toBe("AttestationNotReadyError");
    expect(err.message).toBe("not indexed yet");
    expect(err.burnTxHash).toBe("0xburnabc");
    expect(typeof err.stack).toBe("string");
  });
});

describe("IrisRequestError", () => {
  it("records HTTP status when provided", () => {
    const err = new IrisRequestError("Iris HTTP 503", 503);

    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(IrisRequestError);
    expect(Object.getPrototypeOf(err)).toBe(IrisRequestError.prototype);
    expect(err.name).toBe("IrisRequestError");
    expect(err.message).toBe("Iris HTTP 503");
    expect(err.status).toBe(503);
    expect(typeof err.stack).toBe("string");
  });

  it("leaves status undefined when omitted (network failure before HTTP response)", () => {
    const err = new IrisRequestError("fetch failed: ECONNRESET");

    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(IrisRequestError);
    expect(err.name).toBe("IrisRequestError");
    expect(err.message).toBe("fetch failed: ECONNRESET");
    expect(err.status).toBeUndefined();
  });
});

describe("SubmissionTimeoutError", () => {
  it("populates message, hash, name, and prototype chain", () => {
    const err = new SubmissionTimeoutError("confirmation timed out", "0xtxhash");

    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(SubmissionTimeoutError);
    expect(Object.getPrototypeOf(err)).toBe(SubmissionTimeoutError.prototype);
    expect(err.name).toBe("SubmissionTimeoutError");
    expect(err.message).toBe("confirmation timed out");
    expect(err.hash).toBe("0xtxhash");
    expect(typeof err.stack).toBe("string");
  });
});
