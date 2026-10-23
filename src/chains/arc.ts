import { createPublicClient, http, defineChain, type Hex } from "viem";
import { ARC_TESTNET, ARC_MAINNET, arcConfig } from "../constants.js";
import type { ArcSigner, Network } from "../types.js";
import { SubmissionTimeoutError } from "../errors.js";

export const arcTestnetChain = defineChain({
  id: ARC_TESTNET.chainId,
  name: "Arc Testnet",
  nativeCurrency: { name: "USDC", symbol: "USDC", decimals: 18 },
  rpcUrls: {
    default: { http: [ARC_TESTNET.rpcUrl] },
  },
  blockExplorers: {
    default: { name: "Arcscan", url: ARC_TESTNET.explorerUrl },
  },
  testnet: true,
});

export const arcMainnetChain = defineChain({
  id: ARC_MAINNET.chainId,
  name: "Arc",
  nativeCurrency: { name: "USDC", symbol: "USDC", decimals: 18 },
  rpcUrls: {
    default: { http: [ARC_MAINNET.rpcUrl] },
  },
  blockExplorers: {
    default: { name: "Arc Explorer", url: ARC_MAINNET.explorerUrl },
  },
  testnet: false,
});

function chainFor(network: Network) {
  return network === "mainnet" ? arcMainnetChain : arcTestnetChain;
}

const tokenMessengerV2Abi = [
  {
    type: "function",
    name: "depositForBurn",
    stateMutability: "nonpayable",
    inputs: [
      { name: "amount", type: "uint256" },
      { name: "destinationDomain", type: "uint32" },
      { name: "mintRecipient", type: "bytes32" },
      { name: "burnToken", type: "address" },
      { name: "destinationCaller", type: "bytes32" },
      { name: "maxFee", type: "uint256" },
      { name: "minFinalityThreshold", type: "uint32" },
    ],
    outputs: [],
  },
  {
    type: "function",
    name: "depositForBurnWithHook",
    stateMutability: "nonpayable",
    inputs: [
      { name: "amount", type: "uint256" },
      { name: "destinationDomain", type: "uint32" },
      { name: "mintRecipient", type: "bytes32" },
      { name: "burnToken", type: "address" },
      { name: "destinationCaller", type: "bytes32" },
      { name: "maxFee", type: "uint256" },
      { name: "minFinalityThreshold", type: "uint32" },
      { name: "hookData", type: "bytes" },
    ],
    outputs: [],
  },
] as const;

const messageTransmitterV2Abi = [
  {
    type: "function",
    name: "receiveMessage",
    stateMutability: "nonpayable",
    inputs: [
      { name: "message", type: "bytes" },
      { name: "attestation", type: "bytes" },
    ],
    outputs: [{ name: "success", type: "bool" }],
  },
] as const;

const erc20Abi = [
  {
    type: "function",
    name: "allowance",
    stateMutability: "view",
    inputs: [
      { name: "owner", type: "address" },
      { name: "spender", type: "address" },
    ],
    outputs: [{ name: "", type: "uint256" }],
  },
  {
    type: "function",
    name: "approve",
    stateMutability: "nonpayable",
    inputs: [
      { name: "spender", type: "address" },
      { name: "amount", type: "uint256" },
    ],
    outputs: [{ name: "", type: "bool" }],
  },
] as const;

/**
 * Builds a read client for Arc. The explicit transport is what makes rpcUrl an override:
 * viem prefers a supplied transport over the chain's rpcUrls.default, so a caller routing
 * around the public endpoint gets it for the receipt waits too.
 */
function publicClient(network: Network, rpcUrl?: string) {
  const chain = chainFor(network);
  return createPublicClient({ chain, transport: http(rpcUrl ?? arcConfig(network).rpcUrl) });
}

type WriteContractRequest = Omit<
  Parameters<ArcSigner["walletClient"]["writeContract"]>[0],
  "chain" | "account"
>;

async function writeAndWait(
  signer: ArcSigner,
  request: WriteContractRequest,
  network: Network,
  rpcUrl?: string,
) {
  const account = signer.walletClient.account;
  if (!account) {
    throw new Error("ArcSigner's walletClient must have an account attached");
  }
  const hash = await signer.walletClient.writeContract({
    ...request,
    account,
    chain: chainFor(network),
  } as Parameters<ArcSigner["walletClient"]["writeContract"]>[0]);
  try {
    await publicClient(network, rpcUrl).waitForTransactionReceipt({ hash });
  } catch (err) {
    // The transaction was already broadcast (hash exists); a failure here means we
    // couldn't confirm it in time, not that it didn't happen. Surface the hash instead
    // of discarding it in a bare error.
    const message = err instanceof Error ? err.message : String(err);
    throw new SubmissionTimeoutError(message, hash);
  }
  return hash;
}

/**
 * Reads the current USDC allowance granted by `owner` to TokenMessengerV2 on Arc.
 * Returns 0n if the read fails so callers fail closed and still submit the exact-amount approve.
 */
export async function getUsdcAllowanceOnArc(
  owner: Hex,
  network: Network,
  rpcUrl?: string,
): Promise<bigint> {
  const arc = arcConfig(network);
  try {
    return await publicClient(network, rpcUrl).readContract({
      address: arc.usdc as Hex,
      abi: erc20Abi,
      functionName: "allowance",
      args: [owner, arc.tokenMessengerV2 as Hex],
    });
  } catch {
    return 0n;
  }
}

/**
 * Approves the TokenMessengerV2 contract to spend USDC on the signer's behalf,
 * skipping the on-chain write when the existing allowance already covers `amountRaw`.
 */
export async function approveUsdcOnArc(
  signer: ArcSigner,
  amountRaw: bigint,
  network: Network,
  rpcUrl?: string,
): Promise<Hex | undefined> {
  const account = signer.walletClient.account;
  if (!account) {
    throw new Error("ArcSigner's walletClient must have an account attached");
  }
  const currentAllowance = await getUsdcAllowanceOnArc(account.address, network, rpcUrl);
  if (currentAllowance >= amountRaw) {
    return undefined;
  }
  const arc = arcConfig(network);
  return writeAndWait(
    signer,
    {
      address: arc.usdc as Hex,
      abi: erc20Abi,
      functionName: "approve",
      args: [arc.tokenMessengerV2 as Hex, amountRaw],
    },
    network,
    rpcUrl,
  );
}

/** Reads the current USDC allowance granted to TokenMessengerV2 by the signer or owner address. */
export async function getUsdcAllowanceOnArc(
  signerOrOwner: ArcSigner | Hex,
  network: Network,
  rpcUrl?: string,
): Promise<bigint> {
  let owner: Hex;
  if (typeof signerOrOwner === "string") {
    owner = signerOrOwner;
  } else {
    const account = signerOrOwner.walletClient.account;
    if (!account) {
      throw new Error("ArcSigner's walletClient must have an account attached");
    }
    owner = account.address;
  }
  const arc = arcConfig(network);
  return publicClient(network, rpcUrl).readContract({
    address: arc.usdc as Hex,
    abi: erc20Abi,
    functionName: "allowance",
    args: [owner, arc.tokenMessengerV2 as Hex],
  });
}

/** Burns USDC on Arc via TokenMessengerV2.depositForBurn for a plain (non-Stellar) destination. */
export async function burnUsdcOnArc(params: {
  amountRaw: bigint;
  destinationDomain: number;
  mintRecipientBytes32: Hex;
  maxFeeRaw: bigint;
  minFinalityThreshold: number;
  signer: ArcSigner;
  network: Network;
  /** Overrides the Arc RPC endpoint. Falls back to the network's public default. */
  rpcUrl?: string;
}): Promise<Hex> {
  const arc = arcConfig(params.network);
  return writeAndWait(
    params.signer,
    {
      address: arc.tokenMessengerV2 as Hex,
      abi: tokenMessengerV2Abi,
      functionName: "depositForBurn",
      args: [
        params.amountRaw,
        params.destinationDomain,
        params.mintRecipientBytes32,
        arc.usdc as Hex,
        `0x${"0".repeat(64)}` as Hex,
        params.maxFeeRaw,
        params.minFinalityThreshold,
      ],
    },
    params.network,
    params.rpcUrl,
  );
}

/**
 * Burns USDC on Arc via TokenMessengerV2.depositForBurnWithHook, encoding the
 * Stellar recipient's strkey into the hook payload so CctpForwarder on Stellar
 * knows where to forward the minted USDC.
 */
export async function burnUsdcOnArcWithStellarForward(params: {
  amountRaw: bigint;
  destinationDomain: number;
  mintRecipientBytes32: Hex;
  maxFeeRaw: bigint;
  minFinalityThreshold: number;
  hookData: Hex;
  signer: ArcSigner;
  network: Network;
  /** Overrides the Arc RPC endpoint. Falls back to the network's public default. */
  rpcUrl?: string;
}): Promise<Hex> {
  const arc = arcConfig(params.network);
  return writeAndWait(
    params.signer,
    {
      address: arc.tokenMessengerV2 as Hex,
      abi: tokenMessengerV2Abi,
      functionName: "depositForBurnWithHook",
      args: [
        params.amountRaw,
        params.destinationDomain,
        params.mintRecipientBytes32,
        arc.usdc as Hex,
        `0x${"0".repeat(64)}` as Hex,
        params.maxFeeRaw,
        params.minFinalityThreshold,
        params.hookData,
      ],
    },
    params.network,
    params.rpcUrl,
  );
}

/** Submits an attested CCTP message on Arc via MessageTransmitterV2.receiveMessage. */
export async function receiveMessageOnArc(params: {
  message: Hex;
  attestation: Hex;
  signer: ArcSigner;
  network: Network;
  /** Overrides the Arc RPC endpoint. Falls back to the network's public default. */
  rpcUrl?: string;
}): Promise<Hex> {
  const arc = arcConfig(params.network);
  return writeAndWait(
    params.signer,
    {
      address: arc.messageTransmitterV2 as Hex,
      abi: messageTransmitterV2Abi,
      functionName: "receiveMessage",
      args: [params.message, params.attestation],
    },
    params.network,
    params.rpcUrl,
  );
}
