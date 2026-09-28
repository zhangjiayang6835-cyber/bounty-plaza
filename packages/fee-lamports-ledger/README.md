# Fee-Lamports Retention in Spend Ledger (Issue #1660)

## Overview
This package implements factual network fee retention (`fee_lamports`) in the inference call ledger and receipts alongside conservative ceiling estimates (`fee_micro`), addressing Bounty Plaza Issue #1660 (Source: Grainlify Issue #1).

## Architecture & Invariants
1. **Factual Fee Recording**: Retains confirmed Solana network fee (`fee_lamports`) from on-chain `PayResult`.
2. **Conservative Budget Invariant**: Keeps `fee_micro` ceiling price ($400/SOL) unchanged to guarantee lifetime budget safety.
3. **Database Migration**: Forward-only nullable column `fee_lamports` added to `inference_calls` and `inference_spend`.
4. **Backward Compatibility**: Fully tolerates missing or null `fee_lamports` in legacy records and historical settlements.

## Testing & Verification
- **Python Test Suite**: `python -m unittest tests/test_fee_ledger.py` (5/5 passed)
- **JavaScript Test Suite**: `node packages/fee-lamports-ledger/tests/fee_lamports.test.js` (3/3 passed)
- **SQL Migration**: `packages/fee-lamports-ledger/0011_add_fee_lamports.sql`
