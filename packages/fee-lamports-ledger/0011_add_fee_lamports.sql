-- Forward-only database migration to add fee_lamports to inference_calls and inference_spend
-- Resolves Bounty Plaza Issue #1660 & Grainlify Issue #1

ALTER TABLE inference_calls
    ADD COLUMN IF NOT EXISTS fee_lamports BIGINT DEFAULT NULL;

ALTER TABLE inference_spend
    ADD COLUMN IF NOT EXISTS fee_lamports BIGINT DEFAULT NULL;
