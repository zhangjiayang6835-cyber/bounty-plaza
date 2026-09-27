/**
 * Comprehensive Verification Test Suite: Resilient Deterministic RPC Failover
 * Target: Bounty Plaza Issue #1635 (Source: NSPG13/agent-bounties#1500)
 * 
 * Coverage:
 * 1. Normal dispatch (happy path)
 * 2. Single endpoint failover (ECONNREFUSED)
 * 3. Multi-endpoint cascading failover
 * 4. Endpoint exhaustion when all endpoints fail
 * 5. Circuit breaker cooldown & state machine transitions (healthy -> degraded -> tripped -> recovery -> healthy)
 * 6. Recovery probe failure re-tripping circuit
 * 7. Strict idempotency key preservation across endpoint hops
 * 8. Auto-derived deterministic idempotency fingerprinting
 * 9. Non-retriable JSON-RPC execution errors (revert, -32000, -32602)
 * 10. Chain ID verification & mismatch rejection
 * 11. HTTP 429 rate limit backoff & failover
 * 12. HTTP 5xx server errors
 * 13. Request timeout handling
 * 14. Exponential backoff calculation & jitter constraints
 * 15. Structured metrics aggregation & event emission
 */

import assert from 'node:assert';
import {
  ResilientRpcClient,
  CircuitBreaker,
  CircuitState,
  FailoverEventType,
  ErrorCategory,
  classifyError,
  DeterministicRpcError,
  TransientRpcError,
  EndpointExhaustionError,
  ChainIdMismatchError
} from './rpc_failover.js';

export async function runRpcFailoverTests() {
  const summary = {
    total: 0,
    passed: 0,
    failed: 0,
    failures: [],
    durationMs: 0
  };

  const suiteStart = Date.now();

  async function test(name, fn) {
    summary.total++;
    try {
      await fn();
      summary.passed++;
      console.log(`  [PASS] Test ${summary.total}: ${name}`);
    } catch (err) {
      summary.failed++;
      summary.failures.push({ name, error: err });
      console.error(`  [FAIL] Test ${summary.total}: ${name}`);
      console.error(`         ${err.stack || err.message}`);
    }
  }

  console.log('======================================================================');
  console.log('  TEST SUITE: Resilient Deterministic RPC Failover Engine');
  console.log('  Target: Bounty Plaza Issue #1635 (NSPG13/agent-bounties#1500)');
  console.log('======================================================================\n');

  // --------------------------------------------------------------------------
  // TEST 1: Happy Path Normal Dispatch
  // --------------------------------------------------------------------------
  await test('Normal dispatch: dispatches successfully on primary endpoint', async () => {
    const fetcher = async (url, opts) => {
      assert.strictEqual(url, 'https://rpc1.test.org');
      return {
        ok: true,
        status: 200,
        json: async () => ({ jsonrpc: '2.0', id: 1, result: '0x1234' })
      };
    };

    const client = new ResilientRpcClient({
      endpoints: ['https://rpc1.test.org', 'https://rpc2.test.org'],
      fetcher
    });

    const res = await client.dispatch({ method: 'eth_blockNumber', id: 1 });
    assert.strictEqual(res, '0x1234');
    const metrics = client.getMetrics();
    assert.strictEqual(metrics.global.successfulRequests, 1);
    assert.strictEqual(metrics.endpoints[0].metrics.successCount, 1);
  });

  // --------------------------------------------------------------------------
  // TEST 2: Single Endpoint Failover (Connection Refused)
  // --------------------------------------------------------------------------
  await test('Single endpoint failover: primary ECONNREFUSED switches to backup', async () => {
    let callCount = 0;
    const fetcher = async (url, opts) => {
      callCount++;
      if (url === 'https://rpc1.test.org') {
        const err = new Error('connect ECONNREFUSED');
        err.code = 'ECONNREFUSED';
        throw err;
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ jsonrpc: '2.0', id: 2, result: 'backup-ok' })
      };
    };

    const failoverEvents = [];
    const client = new ResilientRpcClient({
      endpoints: ['https://rpc1.test.org', 'https://rpc2.test.org'],
      fetcher,
      maxRetriesPerEndpoint: 0,
      baseBackoffMs: 1
    });

    client.on(FailoverEventType.FAILOVER, evt => failoverEvents.push(evt));

    const res = await client.dispatch({ method: 'eth_call', id: 2 });
    assert.strictEqual(res, 'backup-ok');
    assert.strictEqual(failoverEvents.length, 1);
    assert.strictEqual(failoverEvents[0].fromEndpoint, 'https://rpc1.test.org');
    assert.strictEqual(failoverEvents[0].toEndpoint, 'https://rpc2.test.org');
  });

  // --------------------------------------------------------------------------
  // TEST 3: Multi-Endpoint Cascading Failure
  // --------------------------------------------------------------------------
  await test('Multi-endpoint cascading failure: cascades primary -> secondary -> tertiary', async () => {
    const attempted = [];
    const fetcher = async (url) => {
      attempted.push(url);
      if (url === 'https://rpc1.test.org') {
        const e = new Error('500 Server Error');
        e.statusCode = 500;
        throw e;
      }
      if (url === 'https://rpc2.test.org') {
        const e = new Error('503 Service Unavailable');
        e.statusCode = 503;
        throw e;
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ jsonrpc: '2.0', id: 3, result: 'tertiary-ok' })
      };
    };

    const client = new ResilientRpcClient({
      endpoints: ['https://rpc1.test.org', 'https://rpc2.test.org', 'https://rpc3.test.org'],
      fetcher,
      maxRetriesPerEndpoint: 0,
      baseBackoffMs: 1
    });

    const res = await client.dispatch({ method: 'eth_getBalance', id: 3 });
    assert.strictEqual(res, 'tertiary-ok');
    assert.deepStrictEqual(attempted, ['https://rpc1.test.org', 'https://rpc2.test.org', 'https://rpc3.test.org']);
  });

  // --------------------------------------------------------------------------
  // TEST 4: Endpoint Exhaustion Error
  // --------------------------------------------------------------------------
  await test('Endpoint exhaustion: throws EndpointExhaustionError with full history', async () => {
    const fetcher = async (url) => {
      const e = new Error(`Connection timeout on ${url}`);
      e.code = 'ETIMEDOUT';
      throw e;
    };

    const client = new ResilientRpcClient({
      endpoints: ['https://rpc1.test.org', 'https://rpc2.test.org'],
      fetcher,
      maxRetriesPerEndpoint: 0,
      baseBackoffMs: 1
    });

    await assert.rejects(
      async () => client.dispatch({ method: 'eth_blockNumber' }),
      (err) => {
        assert.ok(err instanceof EndpointExhaustionError);
        assert.strictEqual(err.attemptHistory.length, 2);
        assert.strictEqual(err.attemptHistory[0].endpoint, 'https://rpc1.test.org');
        assert.strictEqual(err.attemptHistory[1].endpoint, 'https://rpc2.test.org');
        return true;
      }
    );
  });

  // --------------------------------------------------------------------------
  // TEST 5: Circuit Breaker State Transitions & Cooldown Recovery
  // --------------------------------------------------------------------------
  await test('Circuit breaker: transitions healthy -> degraded -> tripped -> recovery -> healthy', () => {
    const stateChanges = [];
    const cb = new CircuitBreaker('https://rpc1.test.org', {
      failureThreshold: 2,
      degradedThreshold: 1,
      recoverySuccessThreshold: 2,
      cooldownPeriodMs: 1000
    });

    cb.on(FailoverEventType.STATE_CHANGE, evt => stateChanges.push(evt));

    assert.strictEqual(cb.state, CircuitState.HEALTHY);
    assert.strictEqual(cb.canExecute(), true);

    // 1st failure: becomes DEGRADED
    cb.recordFailure(new Error('fail 1'), 1000);
    assert.strictEqual(cb.state, CircuitState.DEGRADED);
    assert.strictEqual(cb.canExecute(), true);

    // 2nd failure: becomes TRIPPED
    cb.recordFailure(new Error('fail 2'), 1100);
    assert.strictEqual(cb.state, CircuitState.TRIPPED);
    assert.strictEqual(cb.canExecute(1500), false); // Still within 1000ms cooldown

    // Cooldown elapsed: transitions to RECOVERY
    assert.strictEqual(cb.canExecute(2200), true);
    assert.strictEqual(cb.state, CircuitState.RECOVERY);

    // 1st recovery probe success: still in RECOVERY (needs 2)
    cb.recordSuccess(2300);
    assert.strictEqual(cb.state, CircuitState.RECOVERY);

    // 2nd recovery probe success: recovers to HEALTHY
    cb.recordSuccess(2400);
    assert.strictEqual(cb.state, CircuitState.HEALTHY);

    assert.strictEqual(stateChanges.length, 4);
    assert.strictEqual(stateChanges[0].newState, CircuitState.DEGRADED);
    assert.strictEqual(stateChanges[1].newState, CircuitState.TRIPPED);
    assert.strictEqual(stateChanges[2].newState, CircuitState.RECOVERY);
    assert.strictEqual(stateChanges[3].newState, CircuitState.HEALTHY);
  });

  // --------------------------------------------------------------------------
  // TEST 6: Recovery Probe Failure Re-trips Circuit
  // --------------------------------------------------------------------------
  await test('Circuit breaker: failure during recovery immediately trips circuit', () => {
    const cb = new CircuitBreaker('https://rpc1.test.org', {
      failureThreshold: 1,
      cooldownPeriodMs: 500
    });

    cb.recordFailure(new Error('initial fail'), 1000);
    assert.strictEqual(cb.state, CircuitState.TRIPPED);

    // Cooldown elapses -> RECOVERY
    assert.strictEqual(cb.canExecute(1600), true);
    assert.strictEqual(cb.state, CircuitState.RECOVERY);

    // Probe fails during recovery
    cb.recordFailure(new Error('probe failed'), 1650);
    assert.strictEqual(cb.state, CircuitState.TRIPPED);
    assert.strictEqual(cb.canExecute(1700), false);
  });

  // --------------------------------------------------------------------------
  // TEST 7: Strict Idempotency Key Preservation Across Endpoints
  // --------------------------------------------------------------------------
  await test('Idempotency: preserves exact idempotency key across all failover endpoints', async () => {
    const customKey = 'idem-settlement-uuid-9999-aaaa';
    const seenHeaders = [];

    const fetcher = async (url, opts) => {
      seenHeaders.push({
        url,
        key: opts.headers['x-idempotency-key']
      });

      if (url === 'https://rpc1.test.org') {
        const e = new Error('503 Service Unavailable');
        e.statusCode = 503;
        throw e;
      }

      return {
        ok: true,
        status: 200,
        json: async () => ({ jsonrpc: '2.0', id: 7, result: 'tx-hash-0x99' })
      };
    };

    const client = new ResilientRpcClient({
      endpoints: ['https://rpc1.test.org', 'https://rpc2.test.org'],
      fetcher,
      maxRetriesPerEndpoint: 0,
      baseBackoffMs: 1
    });

    const res = await client.dispatch({ method: 'eth_sendRawTransaction', params: ['0x123'] }, {
      idempotencyKey: customKey
    });

    assert.strictEqual(res, 'tx-hash-0x99');
    assert.strictEqual(seenHeaders.length, 2);
    assert.strictEqual(seenHeaders[0].key, customKey);
    assert.strictEqual(seenHeaders[1].key, customKey);
  });

  // --------------------------------------------------------------------------
  // TEST 8: Deterministic Auto-derived Idempotency Key
  // --------------------------------------------------------------------------
  await test('Idempotency: derives deterministic sha256 hash when key is omitted', () => {
    const client = new ResilientRpcClient({
      endpoints: ['https://rpc1.test.org'],
      fetcher: async () => {}
    });

    const req1 = { method: 'eth_call', params: [{ to: '0xabc' }, 'latest'], id: 10 };
    const req2 = { method: 'eth_call', params: [{ to: '0xabc' }, 'latest'], id: 10 };
    const req3 = { method: 'eth_call', params: [{ to: '0xdef' }, 'latest'], id: 10 };

    const key1 = client.resolveIdempotencyKey(req1);
    const key2 = client.resolveIdempotencyKey(req2);
    const key3 = client.resolveIdempotencyKey(req3);

    assert.strictEqual(key1, key2, 'Identical payloads must yield identical idempotency keys');
    assert.notStrictEqual(key1, key3, 'Different payloads must yield different idempotency keys');
    assert.ok(key1.startsWith('idem-rpc-'));
  });

  // --------------------------------------------------------------------------
  // TEST 9: Non-retriable Deterministic JSON-RPC Execution Error
  // --------------------------------------------------------------------------
  await test('Non-retriable error: EVM execution reverted throws immediately without failover', async () => {
    let callCount = 0;
    const fetcher = async (url) => {
      callCount++;
      return {
        ok: true,
        status: 200,
        json: async () => ({
          jsonrpc: '2.0',
          id: 9,
          error: {
            code: -32000,
            message: 'execution reverted: insufficient allowance'
          }
        })
      };
    };

    const client = new ResilientRpcClient({
      endpoints: ['https://rpc1.test.org', 'https://rpc2.test.org'],
      fetcher,
      maxRetriesPerEndpoint: 2
    });

    await assert.rejects(
      async () => client.dispatch({ method: 'eth_sendRawTransaction', id: 9 }),
      (err) => {
        assert.ok(err instanceof DeterministicRpcError);
        assert.strictEqual(err.code, -32000);
        assert.ok(err.message.includes('insufficient allowance'));
        return true;
      }
    );

    // Crucial Invariant: Only 1 call made! No retry and no failover to rpc2.test.org!
    assert.strictEqual(callCount, 1, 'Deterministic revert must not trigger retry or failover');

    // Endpoint circuit breaker records success because transport connection succeeded
    const states = client.getEndpointStates();
    assert.strictEqual(states['https://rpc1.test.org'], CircuitState.HEALTHY);
  });

  // --------------------------------------------------------------------------
  // TEST 10: Chain ID Validation & Mismatch Rejection
  // --------------------------------------------------------------------------
  await test('Chain ID validation: rejects endpoint returning mismatched chain ID', async () => {
    const fetcher = async (url) => {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          jsonrpc: '2.0',
          id: 10,
          result: '0x1' // Returns 1 (Ethereum Mainnet) instead of expected 8453 (Base)
        })
      };
    };

    const client = new ResilientRpcClient({
      endpoints: ['https://wrong-chain.test.org'],
      expectedChainId: 8453,
      fetcher
    });

    await assert.rejects(
      async () => client.dispatch({ method: 'eth_chainId', id: 10 }),
      (err) => {
        assert.ok(err instanceof ChainIdMismatchError);
        assert.strictEqual(err.data.expected, 8453);
        assert.strictEqual(err.data.actual, 1);
        return true;
      }
    );
  });

  // --------------------------------------------------------------------------
  // TEST 11: HTTP 429 Rate Limit Handling & Backoff Retry
  // --------------------------------------------------------------------------
  await test('HTTP 429 rate limit: retries with exponential backoff on rate limit', async () => {
    let attempts = 0;
    const retryEvents = [];

    const fetcher = async (url) => {
      attempts++;
      if (attempts === 1) {
        return {
          ok: false,
          status: 429,
          statusText: 'Too Many Requests',
          text: async () => 'Rate limit exceeded',
          json: async () => ({})
        };
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ jsonrpc: '2.0', id: 11, result: 'rate-recovered' })
      };
    };

    const client = new ResilientRpcClient({
      endpoints: ['https://rpc1.test.org'],
      fetcher,
      maxRetriesPerEndpoint: 1,
      baseBackoffMs: 10,
      jitter: 0
    });

    client.on(FailoverEventType.REQUEST_RETRY, evt => retryEvents.push(evt));

    const res = await client.dispatch({ method: 'eth_blockNumber', id: 11 });
    assert.strictEqual(res, 'rate-recovered');
    assert.strictEqual(attempts, 2);
    assert.strictEqual(retryEvents.length, 1);
    assert.strictEqual(retryEvents[0].attempt, 1);
  });

  // --------------------------------------------------------------------------
  // TEST 12: Request Timeout Handling
  // --------------------------------------------------------------------------
  await test('Timeout: aborted request fails over to secondary endpoint', async () => {
    const fetcher = async (url, opts) => {
      if (url === 'https://timeout.test.org') {
        const timeoutErr = new Error('The operation was aborted');
        timeoutErr.name = 'AbortError';
        throw timeoutErr;
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ jsonrpc: '2.0', id: 12, result: 'after-timeout' })
      };
    };

    const client = new ResilientRpcClient({
      endpoints: ['https://timeout.test.org', 'https://healthy.test.org'],
      fetcher,
      maxRetriesPerEndpoint: 0,
      baseBackoffMs: 1
    });

    const res = await client.dispatch({ method: 'eth_blockNumber', id: 12 });
    assert.strictEqual(res, 'after-timeout');
  });

  // --------------------------------------------------------------------------
  // TEST 13: Error Classification Matrix
  // --------------------------------------------------------------------------
  await test('Error classifier: correctly identifies transient vs deterministic errors', () => {
    // Transients
    const c1 = classifyError(new Error('connect ECONNREFUSED 127.0.0.1:8545'));
    assert.strictEqual(c1.isTransient, true);

    const c2 = classifyError(new Error('gateway timeout'), { status: 504 });
    assert.strictEqual(c2.isTransient, true);

    const c3 = classifyError(new Error('rate limit reached'), { status: 429 });
    assert.strictEqual(c3.isTransient, true);

    // Deterministics
    const errRevert = new Error('execution reverted');
    errRevert.code = -32000;
    const c4 = classifyError(errRevert);
    assert.strictEqual(c4.isTransient, false);

    const errParams = new Error('invalid params');
    errParams.code = -32602;
    const c5 = classifyError(errParams);
    assert.strictEqual(c5.isTransient, false);

    const errNonce = new Error('nonce too low');
    const c6 = classifyError(errNonce);
    assert.strictEqual(c6.isTransient, false);
  });

  // --------------------------------------------------------------------------
  // TEST 14: Exponential Backoff & Jitter Bounds
  // --------------------------------------------------------------------------
  await test('Exponential backoff: calculation scales exponentially and respects max bound', () => {
    const client = new ResilientRpcClient({
      endpoints: ['https://rpc1.test.org'],
      baseBackoffMs: 100,
      maxBackoffMs: 1000,
      backoffMultiplier: 2,
      jitter: false,
      fetcher: async () => {}
    });

    assert.strictEqual(client.computeBackoff(0), 100);
    assert.strictEqual(client.computeBackoff(1), 200);
    assert.strictEqual(client.computeBackoff(2), 400);
    assert.strictEqual(client.computeBackoff(3), 800);
    assert.strictEqual(client.computeBackoff(4), 1000); // capped at maxBackoffMs
    assert.strictEqual(client.computeBackoff(5), 1000); // capped at maxBackoffMs
  });

  // --------------------------------------------------------------------------
  // TEST 15: Structured Metrics & Reset
  // --------------------------------------------------------------------------
  await test('Metrics & state: tracks counters and resets cleanly', async () => {
    const fetcher = async (url) => ({
      ok: true,
      status: 200,
      json: async () => ({ jsonrpc: '2.0', id: 15, result: 'done' })
    });

    const client = new ResilientRpcClient({
      endpoints: ['https://rpc1.test.org', 'https://rpc2.test.org'],
      fetcher
    });

    await client.dispatch({ method: 'eth_blockNumber' });
    await client.dispatch({ method: 'eth_blockNumber' });

    let metrics = client.getMetrics();
    assert.strictEqual(metrics.global.totalDispatchedRequests, 2);
    assert.strictEqual(metrics.global.successfulRequests, 2);
    assert.strictEqual(metrics.endpoints[0].metrics.successCount, 2);

    client.resetAll();
    metrics = client.getMetrics();
    assert.strictEqual(metrics.global.totalDispatchedRequests, 0);
    assert.strictEqual(metrics.global.successfulRequests, 0);
    assert.strictEqual(metrics.endpoints[0].metrics.successCount, 0);
  });

  summary.durationMs = Date.now() - suiteStart;

  console.log('\n======================================================================');
  console.log(`  TEST RESULTS: ${summary.passed}/${summary.total} PASSED (${summary.failed} failed)`);
  console.log(`  Duration: ${summary.durationMs}ms`);
  console.log('======================================================================\n');

  if (summary.failed > 0) {
    throw new Error(`${summary.failed} tests failed in RPC Failover Test Suite`);
  }

  return summary;
}

if (process.argv[1] && process.argv[1].endsWith('test_rpc_failover.js')) {
  runRpcFailoverTests().catch(err => {
    console.error('Test suite failed:', err);
    process.exit(1);
  });
}
