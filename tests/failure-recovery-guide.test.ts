import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Failure modes and recovery documentation guide', () => {
  it('contains comprehensive docs in docs/FAILURE_MODES_AND_RECOVERY.md', () => {
    const docPath = path.resolve(process.cwd(), 'docs/FAILURE_MODES_AND_RECOVERY.md');
    expect(fs.existsSync(docPath)).toBe(true);

    const content = fs.readFileSync(docPath, 'utf-8');

    // 1. Lifecycle
    expect(content).toContain('Transfer Lifecycle');
    expect(content).toContain('Source Chain Burn');
    expect(content).toContain('Circle Iris Attestation');
    expect(content).toContain('Destination Chain Mint');

    // 2. Exported errors documented
    expect(content).toContain('TransferError');
    expect(content).toContain('AttestationNotReadyError');
    expect(content).toContain('IrisRequestError');
    expect(content).toContain('SubmissionTimeoutError');
    expect(content).toContain('AmountPrecisionError');

    // 3. Clear distinction of funds safety
    expect(content).toContain('Funds are safe; retryable');
    expect(content).toContain('Outcome unknown; inspect first');

    // 4. Code examples for both directions
    expect(content).toContain('completeMint');
    expect(content).toContain('from: "arc"');
    expect(content).toContain('to: "stellar"');
    expect(content).toContain('from: "stellar"');
    expect(content).toContain('to: "arc"');

    // 5. pollTimeout & pollInterval guidance
    expect(content).toContain('pollTimeout');
    expect(content).toContain('pollInterval');
  });

  it('INTEGRATION.md contains Failure modes and recovery section', () => {
    const intPath = path.resolve(process.cwd(), 'INTEGRATION.md');
    expect(fs.existsSync(intPath)).toBe(true);

    const content = fs.readFileSync(intPath, 'utf-8');
    expect(content).toContain('## Failure modes and recovery');
    expect(content).toContain('### Transfer lifecycle');
    expect(content).toContain('### Exported error classes');
    expect(content).toContain('### Recover after `TransferError`');
    expect(content).toContain('### Choosing `pollTimeout`');
  });
});
