// Contract addresses and network parameters sourced from official docs, never inferred:
// Circle CCTP (developers.circle.com/cctp/evm-smart-contracts and .../references/stellar-contracts),
// Arc (docs.arc.io/arc/references/connect-to-arc and .../contract-addresses), and Circle's USDC
// contract list (developers.circle.com/stablecoins/usdc-contract-addresses). Verified 2026-09-23.
// The Stellar mainnet USDC SAC is the deterministic Stellar Asset Contract ID for
// USDC-GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN on the public network; the same
// derivation reproduces the known testnet USDC SAC exactly. pnpm verify:addresses confirms every
// address below is live on its network.

import type { Network } from "./types.js";

export const ARC_DOMAIN = 26;
export const STELLAR_DOMAIN = 27;

export const ARC_TESTNET = {
  chainId: 5042002,
  rpcUrl: "https://rpc.testnet.arc.network",
  wsUrl: "wss://rpc.testnet.arc.network",
  explorerUrl: "https://testnet.arcscan.app",
  tokenMessengerV2: "0x8FE6B999Dc680CcFDD5Bf7EB0974218be2542DAA",
  messageTransmitterV2: "0xE737e5cEBEEBa77EFE34D4aa090756590b1CE275",
  usdc: "0x3600000000000000000000000000000000000000",
  usdcDecimals: 6,
} as const;

export const ARC_MAINNET = {
  chainId: 5042,
  rpcUrl: "https://rpc.mainnet.arc.io",
  // Arc docs list no primary mainnet wss endpoint (only third-party providers). Unused by the SDK.
  wsUrl: "",
  explorerUrl: "https://explorer.arc.io",
  tokenMessengerV2: "0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d",
  messageTransmitterV2: "0x81D40F21F12A8F0E3252Bccb954D722d4c464B64",
  usdc: "0x3600000000000000000000000000000000000000",
  usdcDecimals: 6,
} as const;

export const STELLAR_TESTNET = {
  sorobanRpcUrl: "https://soroban-testnet.stellar.org",
  horizonUrl: "https://horizon-testnet.stellar.org",
  networkPassphrase: "Test SDF Network ; September 2015",
  tokenMessengerMinter: "CDNG7HXAPBWICI2E3AUBP3YZWZELJLYSB6F5CC7WLDTLTHVM74SLRTHP",
  cctpForwarder: "CA66Q2WFBND6V4UEB7RD4SAXSVIWMD6RA4X3U32ELVFGXV5PJK4T4VSZ",
  usdc: "CBIELTK6YBZJU5UP2WWQEUCYKLPU6AUNZ2BQ4WWFEIE3USCIHMXQDAMA",
  usdcDecimals: 7,
} as const;

export const STELLAR_MAINNET = {
  // Stellar runs no free public production Soroban RPC. This SDF-adjacent public endpoint works
  // out of the box but is rate-limited; callers should override it with their own provider for
  // real usage (options.stellarRpcUrl on transfer/completeMint).
  sorobanRpcUrl: "https://mainnet.sorobanrpc.com",
  horizonUrl: "https://horizon.stellar.org",
  networkPassphrase: "Public Global Stellar Network ; September 2015",
  tokenMessengerMinter: "CAE2G5Z77UP7GYPYGFOWFGW7C7J6I4YP2AFGSADRKQY62SYUFLPNFTXL",
  cctpForwarder: "CBZL2IH7F6BIDAA3WBNXYKIXSATJGMSW7K5P5MJ6STX5RXN47TZJDF5T",
  usdc: "CCW67TSZV3SSS2HXMBQ5JFGCKJNXKZM7UQUWUZPUTHXSTZLEO7SJMI75",
  usdcDecimals: 7,
} as const;

export type ArcConfig = typeof ARC_TESTNET | typeof ARC_MAINNET;
export type StellarConfig = typeof STELLAR_TESTNET | typeof STELLAR_MAINNET;

export function arcConfig(network: Network): ArcConfig {
  return network === "mainnet" ? ARC_MAINNET : ARC_TESTNET;
}

export function stellarConfig(network: Network): StellarConfig {
  return network === "mainnet" ? STELLAR_MAINNET : STELLAR_TESTNET;
}

export const IRIS_MAINNET_BASE_URL = "https://iris-api.circle.com/v2/";
export const IRIS_SANDBOX_BASE_URL = "https://iris-api-sandbox.circle.com/v2/";

// Per Circle's CCTP V2 technical guide: values are normalized, below 1000 -> Fast (1000), above -> Standard (2000).
export const FINALITY_THRESHOLD_STANDARD = 2000;
export const FINALITY_THRESHOLD_FAST = 1000;

export const DEFAULT_POLL_INTERVAL_MS = 3000;
export const DEFAULT_POLL_TIMEOUT_MS = 300_000;

// A Stellar transaction's time bound is fixed at build time, before prepareTransaction's
// RPC round trip and before signTransaction. Extension wallets such as Freighter add human
// review time to signing, so a short bound can expire (txTooLate) while the signer is still
// being approved. 180s accommodates interactive signers; the Stellar SDK's typical 60s
// example value assumes machine-speed signing.
export const STELLAR_TX_TIMEOUT_SECONDS = 180;

// How long to wait for a submitted Stellar transaction's confirmation before giving up
// (distinct from the tx's own validity window above). Short windows can elapse before a
// slow or congested RPC returns confirmation; a timeout here does not indicate the
// transaction failed, only that confirmation was not observed within the window (see
// SubmissionTimeoutError in src/errors.ts).
export const STELLAR_CONFIRMATION_TIMEOUT_MS = 120_000;

// Inclusion fee, in stroops, set on a Soroban transaction before prepareTransaction,
// which assembles the final fee as this value plus the simulation's minResourceFee.
// BASE_FEE (100) leaves no headroom to absorb an increase in the resource fee between
// simulation and submission, so a transaction built at BASE_FEE can be rejected with
// txInsufficientFee. This is a per-transaction ceiling rather than a flat charge: the
// network still only takes the resource fee plus the prevailing inclusion fee.
export const STELLAR_INCLUSION_FEE = "1000000";
