import { describe, it, expect } from "vitest";
import { AmountPrecisionError } from "../src/errors.js";
import {
  decimalsForChain,
  toRawAmount,
  fromRawAmount,
  significantDecimals,
  assertDestinationPrecision,
} from "../src/utils/amount.js";
import { ARC_TESTNET, STELLAR_TESTNET } from "../src/constants.js";

describe("decimalsForChain", () => {
  it("returns Arc's decimals for arc", () => {
    expect(decimalsForChain("arc")).toBe(ARC_TESTNET.usdcDecimals);
    expect(decimalsForChain("arc")).toBe(6);
  });

  it("returns Stellar's decimals for stellar", () => {
    expect(decimalsForChain("stellar")).toBe(STELLAR_TESTNET.usdcDecimals);
    expect(decimalsForChain("stellar")).toBe(7);
  });
});

// The precision math itself (parseUsdcAmount/formatUsdcAmount) is covered in
// encoding.test.ts. What matters here is that toRawAmount/fromRawAmount wire the
// correct chain to the correct decimals -- a swapped mapping here would silently
// truncate or inflate every transfer by an order of magnitude, exactly the class of
// bug this SDK exists to prevent developers from hitting themselves.
describe("toRawAmount", () => {
  it("parses at Arc's 6 decimals, not Stellar's 7", () => {
    expect(toRawAmount("10.50", "arc")).toBe(10_500_000n);
  });

  it("parses at Stellar's 7 decimals, not Arc's 6", () => {
    expect(toRawAmount("10.50", "stellar")).toBe(105_000_000n);
  });

  it("rejects an amount with more precision than the target chain supports", () => {
    // 7 decimals of precision is valid on Stellar but not on Arc's 6.
    expect(() => toRawAmount("1.1234567", "arc")).toThrow();
    expect(() => toRawAmount("1.1234567", "stellar")).not.toThrow();
  });
});

describe("fromRawAmount", () => {
  it("formats Arc raw subunits at 6 decimals", () => {
    expect(fromRawAmount(10_500_000n, "arc")).toBe("10.5");
  });

  it("formats Stellar raw subunits at 7 decimals", () => {
    expect(fromRawAmount(105_000_000n, "stellar")).toBe("10.5");
  });

  it("round-trips through toRawAmount for both chains", () => {
    for (const chain of ["arc", "stellar"] as const) {
      const raw = toRawAmount("42.5", chain);
      expect(fromRawAmount(raw, chain)).toBe("42.5");
    }
  });
});

describe("significantDecimals and assertDestinationPrecision", () => {
  it("counts significant fractional places ignoring trailing zeros", () => {
    expect(significantDecimals("1.1234567")).toBe(7);
    expect(significantDecimals("1.1230000")).toBe(3);
    expect(significantDecimals("10")).toBe(0);
    expect(significantDecimals("10.000000")).toBe(0);
  });

  it("rejects amounts whose significant precision exceeds destination USDC decimals", () => {
    expect(() => assertDestinationPrecision("1.1234567", "arc")).toThrow(AmountPrecisionError);
    try {
      assertDestinationPrecision("1.1234567", "arc");
    } catch (err) {
      expect(err).toBeInstanceOf(AmountPrecisionError);
      expect(err).toMatchObject({
        name: "AmountPrecisionError",
        amount: "1.1234567",
        precision: 7,
        supportedDecimals: 6,
        destination: "arc",
      });
    }
  });

  it("accepts trailing-zero padded amounts and exact-fit destination precision", () => {
    expect(() => assertDestinationPrecision("1.1230000", "arc")).not.toThrow();
    expect(() => assertDestinationPrecision("1.123456", "arc")).not.toThrow();
    expect(() => assertDestinationPrecision("1.1234567", "stellar")).not.toThrow();
  });
});
