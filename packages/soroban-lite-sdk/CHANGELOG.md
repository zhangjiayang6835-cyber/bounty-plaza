# Changelog

All notable changes to **soroban-lite-sdk** are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]

### Added
- **Wallet Integration Support** ([#4](https://github.com/your-org/soroban-lite-sdk/issues/4)):
  - Added `WalletAdapter` interface (`name`, `isAvailable()`, `connect()`, `signTransaction(xdr, opts)`).
  - Added `SignTransactionOptions` interface for passing network passphrases and signing parameters.
  - Added `FreighterAdapter` supporting `@stellar/freighter-api` with extension detection and descriptive error handling.
  - Added `StellarKitAdapter` supporting `@creit.tech/stellar-wallets-kit` for modal-based multi-wallet connections.
  - Added `signAndSubmit(tx, wallet, options)` helper method on `SorobanClient` to streamline the simulate -> sign -> submit -> poll lifecycle.
  - Declared `@stellar/freighter-api` and `@creit.tech/stellar-wallets-kit` as optional peer dependencies in `package.json`.
  - Comprehensive unit tests using `vi.mock` in `tests/wallets.test.ts` and `tests/client.test.ts`.
  - Updated `README.md` with complete "Wallet Integration" section and code recipes.

---

## [0.2.0] — 2024-11-18

### Added
- **Named network presets** — `SorobanConfig` now accepts `{ network: "TESTNET" | "MAINNET" | "FUTURENET" }` as a zero-config alternative to supplying `rpcUrl` + `networkPassphrase` manually.
- `RPC_ENDPOINTS` constant map exposing all three preset endpoint URLs.
- `resolveNetworkConfig(network)` utility that maps a `NetworkName` to its `rpcUrl` and `networkPassphrase`.
- `RetryOptions` interface with `maxAttempts`, `delayMs`, and `exponentialBackoff` fields.
- `SimulationResult` structured return type with `raw`, `returnValue`, `minResourceFee`, and `success` fields.
- `isSimulationError(response)` type-guard helper.
- `decodeScVal(base64)` utility for safely decoding base-64 XDR `ScVal` values.
- `getAccount(publicKey)` method.
- `getLatestLedger()` method.

---

## [0.1.0] — 2024-08-20

### Added
- Initial release of `soroban-lite-sdk`.
