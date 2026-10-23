import path from "node:path";
import ts from "typescript";
import { describe, it, expect } from "vitest";
import * as sdk from "../src/index.js";

function getModuleExportSurface(entryRelativePath: string): {
  allExports: string[];
  valueExports: string[];
  typeOnlyExports: string[];
} {
  const rootDir = path.resolve(import.meta.dirname, "..");
  const configPath = path.join(rootDir, "tsconfig.json");
  const configFile = ts.readConfigFile(configPath, ts.sys.readFile);
  if (configFile.error) {
    throw new Error(ts.flattenDiagnosticMessageText(configFile.error.messageText, "\n"));
  }
  const parsed = ts.parseJsonConfigFileContent(configFile.config, ts.sys, rootDir);
  const entryPath = path.join(rootDir, entryRelativePath);
  const program = ts.createProgram([entryPath], parsed.options);
  const checker = program.getTypeChecker();
  const sourceFile = program.getSourceFile(entryPath);
  if (!sourceFile) {
    throw new Error(`Could not load entry file: ${entryPath}`);
  }
  const moduleSymbol = checker.getSymbolAtLocation(sourceFile);
  if (!moduleSymbol) {
    throw new Error(`No module symbol found for ${entryPath}`);
  }

  const allSymbols = checker.getExportsOfModule(moduleSymbol);
  const allExports = allSymbols.map((sym) => sym.getName()).sort();
  const runtimeKeys = new Set(Object.keys(sdk));
  const valueExports = [...runtimeKeys].sort();
  const typeOnlyExports = allExports.filter((name) => !runtimeKeys.has(name)).sort();

  return { allExports, valueExports, typeOnlyExports };
}

describe("public export surface snapshot (src/index.ts)", () => {
  it("matches the snapshotted runtime value exports", () => {
    const runtimeExports = Object.keys(sdk).sort();
    expect(runtimeExports).toMatchInlineSnapshot(`
      [
        "ARC_MAINNET",
        "ARC_TESTNET",
        "AmountPrecisionError",
        "AttestationNotReadyError",
        "IrisRequestError",
        "Keypair",
        "STELLAR_MAINNET",
        "STELLAR_TESTNET",
        "SubmissionTimeoutError",
        "TransferError",
        "arcMainnetChain",
        "arcTestnetChain",
        "checkStellarRecipientReady",
        "completeMint",
        "convertPrecision",
        "decimalsForChain",
        "decodeCctpMessage",
        "decodeStellarForwardHook",
        "estimateFee",
        "getAttestation",
        "resolveBurn",
        "transfer",
      ]
    `);
  });

  it("matches the snapshotted TypeScript type-only and combined exports from src/index.ts", () => {
    const surface = getModuleExportSurface("src/index.ts");

    expect(surface.valueExports).toEqual(Object.keys(sdk).sort());
    expect(surface.typeOnlyExports).toMatchInlineSnapshot(`
      [
        "ApproveProgressEvent",
        "ArcDestinationOptions",
        "ArcSigner",
        "AttestationProgressEvent",
        "BurnConfirmedProgressEvent",
        "BurnSubmittedProgressEvent",
        "CctpBurnMessage",
        "ChainId",
        "CompleteMintOptions",
        "CompleteMintParams",
        "CompleteMintResult",
        "EstimateFeeParams",
        "FeeEstimate",
        "MintConfirmedProgressEvent",
        "MintSubmittedProgressEvent",
        "Network",
        "RecipientCheckProgressEvent",
        "ResolveBurnParams",
        "ResolvedBurn",
        "Signer",
        "StellarDestinationOptions",
        "StellarRecipientStatus",
        "StellarRetryOptions",
        "StellarSignFunction",
        "StellarSigner",
        "TransferErrorCode",
        "TransferMode",
        "TransferOptions",
        "TransferOptionsBase",
        "TransferParams",
        "TransferProgressEvent",
        "TransferProgressStage",
        "TransferResult",
        "TransferSpeed",
        "TransferStatus",
      ]
    `);
    expect(surface.allExports).toMatchInlineSnapshot(`
      [
        "ARC_MAINNET",
        "ARC_TESTNET",
        "AmountPrecisionError",
        "ApproveProgressEvent",
        "ArcDestinationOptions",
        "ArcSigner",
        "AttestationNotReadyError",
        "AttestationProgressEvent",
        "BurnConfirmedProgressEvent",
        "BurnSubmittedProgressEvent",
        "CctpBurnMessage",
        "ChainId",
        "CompleteMintOptions",
        "CompleteMintParams",
        "CompleteMintResult",
        "EstimateFeeParams",
        "FeeEstimate",
        "IrisRequestError",
        "Keypair",
        "MintConfirmedProgressEvent",
        "MintSubmittedProgressEvent",
        "Network",
        "RecipientCheckProgressEvent",
        "ResolveBurnParams",
        "ResolvedBurn",
        "STELLAR_MAINNET",
        "STELLAR_TESTNET",
        "Signer",
        "StellarDestinationOptions",
        "StellarRecipientStatus",
        "StellarRetryOptions",
        "StellarSignFunction",
        "StellarSigner",
        "SubmissionTimeoutError",
        "TransferError",
        "TransferErrorCode",
        "TransferMode",
        "TransferOptions",
        "TransferOptionsBase",
        "TransferParams",
        "TransferProgressEvent",
        "TransferProgressStage",
        "TransferResult",
        "TransferSpeed",
        "TransferStatus",
        "arcMainnetChain",
        "arcTestnetChain",
        "checkStellarRecipientReady",
        "completeMint",
        "convertPrecision",
        "decimalsForChain",
        "decodeCctpMessage",
        "decodeStellarForwardHook",
        "estimateFee",
        "getAttestation",
        "resolveBurn",
        "transfer",
      ]
    `);
  });
});
