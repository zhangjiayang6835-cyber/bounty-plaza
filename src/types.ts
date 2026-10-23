import type { Keypair } from "@stellar/stellar-sdk";

export type Network = "mainnet" | "testnet";
export type ChainId = number;

export interface StellarSigner {
  publicKey: string;
  keypair?: Keypair;
  signTransaction?: (xdr: string, passphrase: string) => Promise<string>;
}

export interface StellarConfig {
  sorobanRpcUrl: string;
  horizonUrl: string;
  networkPassphrase: string;
  tokenMessengerMinter: string;
  cctpForwarder: string;
  usdc: string;
  usdcDecimals: number;
}
