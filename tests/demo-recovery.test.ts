import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Demo app post-burn recovery flow', () => {
  it('ErrorBanner.tsx implements post-burn recovery UI with copyable hash and complete transfer button', () => {
    const bannerPath = path.resolve(process.cwd(), 'demos/wallet-transfer-demo/src/components/ErrorBanner.tsx');
    expect(fs.existsSync(bannerPath)).toBe(true);

    const content = fs.readFileSync(bannerPath, 'utf-8');

    // 1. Post-burn explanation
    expect(content).toContain('The source-chain burn already succeeded and funds left');
    expect(content).toContain('the funds haven\'t minted on');
    expect(content).toContain('Complete transfer');

    // 2. Double-burn avoidance warning
    expect(content).toContain('which would burn a second time');

    // 3. Copy burn hash button
    expect(content).toContain('Copy burn hash');
    expect(content).toContain('Copied burn hash');

    // 4. Explorer link
    expect(content).toContain('View on explorer');

    // 5. Normal retry / uncertain distinction
    expect(content).toContain('submissionUncertain');
    expect(content).toContain('Nothing was submitted on-chain yet, so it\'s safe to retry.');
  });

  it('useTransfer.ts captures transfer context on TransferError and exposes recovery state', () => {
    const hookPath = path.resolve(process.cwd(), 'demos/wallet-transfer-demo/src/hooks/useTransfer.ts');
    expect(fs.existsSync(hookPath)).toBe(true);

    const content = fs.readFileSync(hookPath, 'utf-8');

    // 1. RecoverableTransferContext definition
    expect(content).toContain('export interface RecoverableTransferContext');
    expect(content).toContain('burnTxHash: string');
    expect(content).toContain('from: ChainId');
    expect(content).toContain('to: ChainId');

    // 2. TransferError handling
    expect(content).toContain('err instanceof TransferError');
    expect(content).toContain('setRecoverableBurnTxHash(err.burnTxHash)');
    expect(content).toContain('setRecoverableTransfer');

    // 3. Return signature
    expect(content).toContain('recoverableBurnTxHash');
    expect(content).toContain('recoverableTransfer');
  });

  it('App.tsx ties recovery mint parameters to the captured burn context', () => {
    const appPath = path.resolve(process.cwd(), 'demos/wallet-transfer-demo/src/App.tsx');
    expect(fs.existsSync(appPath)).toBe(true);

    const content = fs.readFileSync(appPath, 'utf-8');

    // 1. mintParams uses captured direction
    expect(content).toContain('recoverableTransfer?.to ?? form.to');
    expect(content).toContain('recoverableTransfer?.network ?? network');

    // 2. Recovery handler
    expect(content).toContain('handleRecoverMint');
    expect(content).toContain('finishPending(params)');
  });
});
