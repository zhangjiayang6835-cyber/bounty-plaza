/**
 * Re‑export the deterministic RPC failover helper.
 *
 * This file exists to provide a single entry point for RPC utilities
 * and to keep the public API stable.  It simply re‑exports the
 * `selectRpcEndpoint` function from `failover.ts`.
 */

export { selectRpcEndpoint } from './failover';
