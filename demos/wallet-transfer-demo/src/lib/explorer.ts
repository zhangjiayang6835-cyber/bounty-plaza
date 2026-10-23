import type { ChainId, Network } from "@asctp/parabola";
import { arcNetworkConfig } from "./network.js";

/** Block explorer link for a transaction on either chain, on the selected network. */
export function explorerUrl(chain: ChainId, txHash: string, network: Network): string {
  if (chain === "arc") return `${arcNetworkConfig(network).explorerUrl}/tx/${txHash}`;
  const stellarNetwork = network === "mainnet" ? "public" : "testnet";
  return `https://stellar.expert/explorer/${stellarNetwork}/tx/${txHash}`;
}
