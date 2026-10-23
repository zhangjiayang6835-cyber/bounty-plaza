/** Shortens a hex address or Stellar strkey for display: "GABCD...WXYZ" / "0x1234...abcd". */
export function shortenAddress(address: string, lead = 6, tail = 4): string {
  if (address.length <= lead + tail + 3) return address;
  return `${address.slice(0, lead)}...${address.slice(-tail)}`;
}

/** Shortens a transaction hash the same way, with a slightly longer lead by convention. */
export function shortenTxHash(hash: string): string {
  return shortenAddress(hash, 10, 8);
}

export function formatDurationMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
