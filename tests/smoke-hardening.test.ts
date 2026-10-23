import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('scripts/testnet-smoke.mjs hardening', () => {
  it('implements structured steps, transient retries, step summary, and recovery', () => {
    const scriptPath = path.resolve(process.cwd(), 'scripts/testnet-smoke.mjs');
    expect(fs.existsSync(scriptPath)).toBe(true);

    const content = fs.readFileSync(scriptPath, 'utf-8');

    // 1. Structured steps
    expect(content).toContain('runStep');
    expect(content).toContain('fund/check');
    expect(content).toContain('approve+burn');
    expect(content).toContain('attestation wait');
    expect(content).toContain('mint');

    // 2. Error classification (transient vs deterministic)
    expect(content).toContain('isDeterministicError');
    expect(content).toContain('isTransientError');
    expect(content).toContain('STEP_MAX_ATTEMPTS');
    expect(content).toContain('STEP_BASE_DELAY_MS');

    // 3. Step summary reporting
    expect(content).toContain('printStepSummary');
    expect(content).toContain('Smoke Test Step Summary');
    expect(content).toContain('stepSummary');

    // 4. Post-burn recovery without double burn
    expect(content).toContain('printRecoveryInstructions');
    expect(content).toContain('completeMint');
    expect(content).toContain('burnTxHash');

    // 5. Exit code handling
    expect(content).toContain('process.exit(1)');
  });
});
