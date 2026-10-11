/**
 * Deterministic RPC failover utility.
 *
 * This module provides a helper to select an RPC endpoint from a list of
 * available endpoints in a deterministic manner. The selection is based on
 * a stable hash of a request identifier (e.g. a transaction hash or a
 * request ID). The list of endpoints is first sorted alphabetically to
 * guarantee that the same set of endpoints always results in the same
 * ordering, which is essential for deterministic behaviour.
 *
 * The original implementation used a non‑stable ordering of the
 * endpoints array and a non‑deterministic hash function, which caused
 * the `rpc-failover` fixture to fail.  The updated implementation
 * guarantees that the same request ID will always map to the same
 * endpoint, regardless of the order in which the endpoints were
 * supplied.
 */

import { createHash } from 'crypto';

/**
 * Compute a stable numeric hash from a string.
 *
 * @param input - The string to hash.
 * @returns A 32‑bit unsigned integer hash.
 */
function stableHash(input: string): number {
  // Use SHA‑256 and take the first 4 bytes as a 32‑bit unsigned integer.
  const hash = createHash('sha256').update(input).digest();
  // Convert first 4 bytes to a number (big‑endian).
  return (
    (hash[0] << 24) |
    (hash[1] << 16) |
    (hash[2] << 8) |
    hash[3]
  ) >>> 0; // Ensure unsigned
}

/**
 * Select an RPC endpoint deterministically.
 *
 * @param requestId - A unique identifier for the request (e.g. tx hash).
 * @param endpoints - Array of RPC endpoint URLs.
 * @returns The selected endpoint URL.
 *
 * @throws {Error} If the `endpoints` array is empty.
 */
export function selectRpcEndpoint(
  requestId: string,
  endpoints: string[]
): string {
  if (endpoints.length === 0) {
    throw new Error('No RPC endpoints provided');
  }

  // Sort endpoints alphabetically to guarantee deterministic ordering.
  const sorted = [...endpoints].sort((a, b) => a.localeCompare(b));

  const hash = stableHash(requestId);
  const index = hash % sorted.length;
  return sorted[index];
}
