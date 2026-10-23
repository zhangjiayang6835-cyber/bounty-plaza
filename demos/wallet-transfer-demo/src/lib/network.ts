import {
  arcMainnetChain,
  arcTestnetChain,
  ARC_MAINNET,
  ARC_TESTNET,
  STELLAR_MAINNET,
  STELLAR_TESTNET,
  type Network,
} from "@asctp/parabola";

export type { Network };

// The network the app opens on. Mainnet, following the convention every block explorer uses,
// with the banner turning red and spelling out that transfers move real USDC. The switch in
// the banner is the only thing that changes it, and there is no build-time override, so a
// local checkout and the deployed build behave identically.
export const DEFAULT_NETWORK: Network = "mainnet";

export function arcChainFor(network: Network) {
  return network === "mainnet" ? arcMainnetChain : arcTestnetChain;
}

export function arcNetworkConfig(network: Network) {
  return network === "mainnet" ? ARC_MAINNET : ARC_TESTNET;
}

export function stellarNetworkPassphrase(network: Network): string {
  return network === "mainnet"
    ? STELLAR_MAINNET.networkPassphrase
    : STELLAR_TESTNET.networkPassphrase;
}
