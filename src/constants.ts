import type { Network, StellarConfig } from "./types.js";

export const STELLAR_TX_TIMEOUT_SECONDS = 300;
export const STELLAR_CONFIRMATION_TIMEOUT_MS = 60_000;
export const STELLAR_INCLUSION_FEE = "100000";

export const STELLAR_TESTNET: StellarConfig = {
  sorobanRpcUrl: "https://soroban-testnet.stellar.org",
  horizonUrl: "https://horizon-testnet.stellar.org",
  networkPassphrase: "Test SDF Network ; September 2015",
  tokenMessengerMinter: "CDNG7HXAPBWICI2E3AUBP3YZWZELJLYSB6F5CC7WLDTLTHVM74SLRTHP",
  cctpForwarder: "CA66Q2WFBND6V4UEB7RD4SAXSVIWMD6RA4X3U32ELVFGXV5PJK4T4VSZ",
  usdc: "CBIELTK6YBZJU5UP2WWQEUCYKLPU6AUNZ2BQ4WWFEIE3USCIHMXQDAMA",
  usdcDecimals: 7,
};

export const STELLAR_MAINNET: StellarConfig = {
  sorobanRpcUrl: "https://mainnet.sorobanrpc.com",
  horizonUrl: "https://horizon.stellar.org",
  networkPassphrase: "Public Global Stellar Network ; September 2015",
  tokenMessengerMinter: "CAE2G5Z77UP7GYPYGFOWFGW7C7J6I4YP2AFGSADRKQY62SYUFLPNFTXL",
  cctpForwarder: "CBZL2IH7F6BIDAA3WBNXYKIXSATJGMSW7K5P5MJ6STX5RXN47TZJDF5T",
  usdc: "CCW67TSZV3SSS2HXMBQ5JFGCKJNXKZM7UQUWUZPUTHXSTZLEO7SJMI75",
  usdcDecimals: 7,
};

export function stellarConfig(network: Network): StellarConfig {
  return network === "mainnet" ? STELLAR_MAINNET : STELLAR_TESTNET;
}
