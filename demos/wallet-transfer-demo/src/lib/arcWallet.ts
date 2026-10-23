import { createWalletClient, custom, type Address, type WalletClient } from "viem";
import type { ArcSigner, Network } from "@asctp/parabola";
import { arcChainFor, arcNetworkConfig } from "./network.js";

/**
 * Connects to an injected EVM wallet (e.g. MetaMask) via window.ethereum, switches it to
 * the requested Arc network (adding the network if the wallet doesn't know it yet), and
 * returns a viem WalletClient wrapped as an ArcSigner. This is the whole of what ArcSigner
 * needs: it's a plain viem WalletClient, so any wallet/connector that can produce one works,
 * not just this pattern.
 */
export async function connectArcWallet(
  network: Network,
): Promise<{ signer: ArcSigner; address: Address }> {
  if (!window.ethereum) {
    throw new Error("No EVM wallet found. Install MetaMask (or another injected wallet) to continue.");
  }
  const provider = window.ethereum;

  const accounts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
  const address = accounts[0];
  if (!address) {
    throw new Error("No account returned by the wallet.");
  }

  await ensureArcChain(provider, network);

  const walletClient: WalletClient = createWalletClient({
    account: address as Address,
    chain: arcChainFor(network),
    transport: custom(provider),
  });

  return { signer: { walletClient }, address: address as Address };
}

async function ensureArcChain(
  provider: NonNullable<Window["ethereum"]>,
  network: Network,
): Promise<void> {
  const arcChain = arcChainFor(network);
  const arcConfig = arcNetworkConfig(network);
  const targetChainIdHex = `0x${arcConfig.chainId.toString(16)}`;
  const currentChainIdHex = (await provider.request({ method: "eth_chainId" })) as string;

  if (currentChainIdHex.toLowerCase() === targetChainIdHex.toLowerCase()) {
    return;
  }

  try {
    await provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: targetChainIdHex }],
    });
  } catch (error) {
    // 4902: the wallet doesn't have this chain configured yet, so add it, then switch.
    const code = (error as { code?: number })?.code;
    if (code !== 4902) {
      throw error;
    }
    await provider.request({
      method: "wallet_addEthereumChain",
      params: [
        {
          chainId: targetChainIdHex,
          chainName: arcChain.name,
          nativeCurrency: arcChain.nativeCurrency,
          rpcUrls: [arcConfig.rpcUrl],
          blockExplorerUrls: [arcConfig.explorerUrl],
        },
      ],
    });
  }
}
