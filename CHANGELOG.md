# Changelog

## [Unreleased]

### Added

- Wallet adapter support for Freighter and Stellar Wallets Kit
- `WalletAdapter` interface exported from package root
- `FreighterAdapter` class using `@stellar/freighter-api`
- `StellarKitAdapter` class using `@creit.tech/stellar-wallets-kit`
- `signAndSubmit(tx, wallet)` helper on `SorobanClient`
- Unit tests for both adapters using `vi.mock`
- README updated with Wallet Integration section

### Dependencies

- Added peer dependencies: `@stellar/freighter-api`, `@creit.tech/stellar-wallets-kit`
