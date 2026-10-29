```typescript
// tests/errors.test.ts
import { TransferError } from '../src/errors';
import { AttestationNotReadyError } from '../src/errors';
import { IrisRequestError } from '../src/errors';
import { SubmissionTimeoutError } from '../src/errors';

describe('Errors', () => {
  it('should have correct properties on TransferError', () => {
    const error = new TransferError('message');
    expect(error.message).toBeDefined();
    expect(error.code).toBeDefined();
    expect(error.TransferErrorCode).toBeDefined();
    const errorWithCode = new TransferError('message', { code: 'custom_code' });
    expect(errorWithCode.code).toBe('custom_code');
  });

  it('should have correct properties on AttestationNotReadyError', () => {
    const error = new AttestationNotReadyError('message');
    expect(error.message).toBeDefined();
    expect(error.code).toBeDefined();
    expect(error.TransferErrorCode).toBeDefined();
  });

  it('should have correct properties on IrisRequestError', () => {
    const error = new IrisRequestError('message');
    expect(error.message).toBeDefined();
    expect(error.code).toBeDefined();
    expect(error.TransferErrorCode).toBeDefined();
  });

  it('should have correct properties on SubmissionTimeoutError', () => {
    const error = new SubmissionTimeoutError('message');
    expect(error.message).toBeDefined();
    expect(error.code).toBeDefined();
    expect(error.TransferErrorCode).toBeDefined();
  });
});

// tests/exports.test.ts
import.meta.vitest();

describe('Exports', () => {
  it('should match the exports snapshot', () => {
    const exports = {
      TransferError,
      AttestationNotReadyError,
      IrisRequestError,
      SubmissionTimeoutError,
    };
    // Assert exports match the snapshot
    expect(Object.keys(exports)).toMatchSnapshot();
  });
});
```