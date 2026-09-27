/**
 * Resilient Deterministic RPC Failover Subsystem
 * Target: Bounty Plaza Issue #1635 (Source: NSPG13/agent-bounties#1500)
 * 
 * Objective:
 * Implement a deterministic sequential failover RPC transport that survives primary RPC
 * failures (ECONNREFUSED, timeout, HTTP 429 rate limit, HTTP 5xx errors) with circuit-breaker
 * state tracking (healthy, degraded, tripped, recovery), exponential backoff with jitter,
 * strict idempotency key preservation across endpoint switches, and structured event/metric emission.
 * 
 * Author: Autonomous Economic Agent (AEA-01) - Senior Autonomous Bug Bounty Engineer
 */

import { EventEmitter } from 'node:events';
import crypto from 'node:crypto';

// ============================================================================
// 1. CONSTANTS, ENUMS & CONFIGURATION
// ============================================================================

export const CircuitState = Object.freeze({
  HEALTHY: 'healthy',
  DEGRADED: 'degraded',
  TRIPPED: 'tripped',
  RECOVERY: 'recovery'
});

export const FailoverEventType = Object.freeze({
  FAILOVER: 'failover',
  STATE_CHANGE: 'state_change',
  REQUEST_RETRY: 'request_retry',
  REQUEST_SUCCESS: 'request_success',
  REQUEST_FAILURE: 'request_failure',
  CIRCUIT_TRIP: 'circuit_trip',
  CIRCUIT_RECOVERED: 'circuit_recovered',
  ENDPOINT_HEALTH: 'endpoint_health'
});

export const ErrorCategory = Object.freeze({
  TRANSIENT: 'transient',
  DETERMINISTIC: 'deterministic'
});

export const DEFAULT_CONFIG = Object.freeze({
  timeoutMs: 8000,
  maxRetriesPerEndpoint: 2,
  baseBackoffMs: 100,
  maxBackoffMs: 3000,
  backoffMultiplier: 2,
  jitter: true,
  failureThreshold: 3,
  degradedThreshold: 1,
  recoverySuccessThreshold: 2,
  cooldownPeriodMs: 10000,
  preserveIdempotency: true,
  expectedChainId: null
});

// ============================================================================
// 2. CUSTOM ERROR HIERARCHY
// ============================================================================

export class RpcError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = this.constructor.name;
    this.code = options.code ?? null;
    this.data = options.data ?? null;
    this.category = options.category ?? ErrorCategory.TRANSIENT;
    this.statusCode = options.statusCode ?? null;
    this.endpoint = options.endpoint ?? null;
    this.idempotencyKey = options.idempotencyKey ?? null;
    this.rawError = options.rawError ?? null;
  }
}

export class DeterministicRpcError extends RpcError {
  constructor(message, options = {}) {
    super(message, { ...options, category: ErrorCategory.DETERMINISTIC });
  }
}

export class TransientRpcError extends RpcError {
  constructor(message, options = {}) {
    super(message, { ...options, category: ErrorCategory.TRANSIENT });
  }
}

export class EndpointExhaustionError extends RpcError {
  constructor(message, options = {}) {
    super(message, { ...options, category: ErrorCategory.TRANSIENT });
    this.attemptHistory = options.attemptHistory ?? [];
  }
}

export class CircuitTrippedError extends RpcError {
  constructor(endpoint, options = {}) {
    super(`Circuit breaker tripped for endpoint: ${endpoint}`, {
      ...options,
      endpoint,
      category: ErrorCategory.TRANSIENT
    });
  }
}

export class ChainIdMismatchError extends DeterministicRpcError {
  constructor(endpoint, expected, actual) {
    super(`Chain ID mismatch for endpoint ${endpoint}: expected ${expected}, got ${actual}`, {
      endpoint,
      data: { expected, actual }
    });
  }
}

// ============================================================================
// 3. ERROR CLASSIFICATION ENGINE
// ============================================================================

/**
 * Classifies an error into TRANSIENT (failover-eligible) or DETERMINISTIC (terminal).
 * 
 * Rules:
 * - Deterministic: On-chain revert (-32000, execution reverted), method not found (-32601),
 *   invalid params (-32602), nonce too low, insufficient funds, chain ID mismatch.
 *   These MUST NOT trigger failover or retry; they must be surfaced immediately.
 * - Transient: ECONNREFUSED, ETIMEDOUT, ENOTFOUND, socket hangup, HTTP 429, HTTP 5xx.
 *   These warrant deterministic sequential failover and exponential backoff.
 */
export function classifyError(err, response = null) {
  if (!err) {
    return { isTransient: false, category: ErrorCategory.DETERMINISTIC, reason: 'unknown' };
  }

  // Check explicit category if already typed
  if (err instanceof DeterministicRpcError) {
    return { isTransient: false, category: ErrorCategory.DETERMINISTIC, reason: err.message };
  }
  if (err instanceof TransientRpcError) {
    return { isTransient: true, category: ErrorCategory.TRANSIENT, reason: err.message };
  }

  const status = response?.status || err.statusCode || err.status;
  const errMsg = (err.message || '').toLowerCase();
  const errCode = (err.code !== undefined && err.code !== null) ? String(err.code) : '';

  // 1. HTTP Status Code Checks
  if (status === 429) {
    return { isTransient: true, category: ErrorCategory.TRANSIENT, reason: 'HTTP 429 Rate Limit' };
  }
  if (status >= 500 && status <= 599) {
    return { isTransient: true, category: ErrorCategory.TRANSIENT, reason: `HTTP ${status} Server Error` };
  }

  // 2. Network-level transient system errors
  const transientSystemCodes = ['ECONNREFUSED', 'ETIMEDOUT', 'ENOTFOUND', 'EAI_AGAIN', 'ECONNRESET', 'UND_ERR_CONNECT_TIMEOUT'];
  if (transientSystemCodes.includes(errCode) || transientSystemCodes.some(c => errMsg.includes(c.toLowerCase()))) {
    return { isTransient: true, category: ErrorCategory.TRANSIENT, reason: `Network fault: ${errCode || 'connection failure'}` };
  }

  if (err.name === 'AbortError' || errMsg.includes('timeout') || errMsg.includes('timed out') || errMsg.includes('abort')) {
    return { isTransient: true, category: ErrorCategory.TRANSIENT, reason: 'Request timeout' };
  }

  if (errMsg.includes('rate limit') || errMsg.includes('too many requests')) {
    return { isTransient: true, category: ErrorCategory.TRANSIENT, reason: 'Rate limited' };
  }

  // 3. Known Deterministic JSON-RPC Execution Errors
  // Standard JSON-RPC error codes:
  // -32700: Parse error
  // -32600: Invalid Request
  // -32601: Method not found
  // -32602: Invalid params
  // -32603: Internal error (contract execution reverted)
  // -32000: Execution reverted / VM exception
  // -32003: Transaction rejected
  const deterministicRpcCodes = [-32700, -32600, -32601, -32602, -32603, -32000, -32003];
  const numCode = Number(err.code);
  if (deterministicRpcCodes.includes(numCode)) {
    return { isTransient: false, category: ErrorCategory.DETERMINISTIC, reason: `JSON-RPC Deterministic Error: ${numCode}` };
  }

  // Deterministic EVM error strings
  const deterministicPatterns = [
    'execution reverted',
    'nonce too low',
    'replacement transaction underpriced',
    'insufficient funds',
    'invalid signature',
    'invalid param',
    'method not found',
    'exceeds block gas limit',
    'chain id mismatch'
  ];

  for (const pattern of deterministicPatterns) {
    if (errMsg.includes(pattern)) {
      return { isTransient: false, category: ErrorCategory.DETERMINISTIC, reason: `Deterministic business error: ${pattern}` };
    }
  }

  // Fallback: If not explicitly transient, treat unclassified network errors as transient,
  // but unclassified app errors as deterministic
  if (errMsg.includes('fetch failed') || errMsg.includes('network') || errMsg.includes('socket')) {
    return { isTransient: true, category: ErrorCategory.TRANSIENT, reason: 'Unclassified network error' };
  }

  return { isTransient: false, category: ErrorCategory.DETERMINISTIC, reason: 'Unclassified deterministic error' };
}

// ============================================================================
// 4. CIRCUIT BREAKER
// ============================================================================

export class CircuitBreaker extends EventEmitter {
  constructor(endpoint, options = {}) {
    super();
    this.endpoint = endpoint;
    this.failureThreshold = options.failureThreshold ?? DEFAULT_CONFIG.failureThreshold;
    this.degradedThreshold = options.degradedThreshold ?? DEFAULT_CONFIG.degradedThreshold;
    this.recoverySuccessThreshold = options.recoverySuccessThreshold ?? DEFAULT_CONFIG.recoverySuccessThreshold;
    this.cooldownPeriodMs = options.cooldownPeriodMs ?? DEFAULT_CONFIG.cooldownPeriodMs;

    this.state = CircuitState.HEALTHY;
    this.consecutiveFailures = 0;
    this.consecutiveSuccesses = 0;
    this.totalSuccesses = 0;
    this.totalFailures = 0;
    this.lastFailureTime = null;
    this.lastSuccessTime = null;
    this.lastStateChangeTime = Date.now();
  }

  /**
   * Evaluates if the endpoint is permitted to receive requests.
   * Handles cooldown expiry and half-open RECOVERY transitions.
   */
  canExecute(now = Date.now()) {
    if (this.state === CircuitState.HEALTHY || this.state === CircuitState.DEGRADED) {
      return true;
    }

    if (this.state === CircuitState.TRIPPED) {
      const elapsed = now - (this.lastFailureTime || 0);
      if (elapsed >= this.cooldownPeriodMs) {
        this.transitionTo(CircuitState.RECOVERY, 'Cooldown elapsed, entering recovery probe mode', now);
        return true;
      }
      return false;
    }

    if (this.state === CircuitState.RECOVERY) {
      return true;
    }

    return false;
  }

  /**
   * Records a successful execution.
   */
  recordSuccess(now = Date.now()) {
    this.lastSuccessTime = now;
    this.totalSuccesses++;
    this.consecutiveFailures = 0;

    if (this.state === CircuitState.RECOVERY) {
      this.consecutiveSuccesses++;
      if (this.consecutiveSuccesses >= this.recoverySuccessThreshold) {
        this.transitionTo(CircuitState.HEALTHY, `Endpoint recovered after ${this.consecutiveSuccesses} consecutive successes`, now);
      }
    } else if (this.state === CircuitState.DEGRADED) {
      this.consecutiveSuccesses++;
      this.transitionTo(CircuitState.HEALTHY, 'Endpoint recovered from degraded state on success', now);
    } else {
      this.consecutiveSuccesses++;
    }
  }

  /**
   * Records an execution failure.
   */
  recordFailure(err, now = Date.now()) {
    this.lastFailureTime = now;
    this.totalFailures++;
    this.consecutiveSuccesses = 0;
    this.consecutiveFailures++;

    if (this.state === CircuitState.RECOVERY) {
      // In recovery mode, a single failure immediately trips the circuit again
      this.transitionTo(CircuitState.TRIPPED, `Probe failed during recovery: ${err.message}`, now);
    } else if (this.consecutiveFailures >= this.failureThreshold) {
      this.transitionTo(CircuitState.TRIPPED, `Failure threshold (${this.failureThreshold}) reached`, now);
    } else if (this.consecutiveFailures >= this.degradedThreshold && this.state === CircuitState.HEALTHY) {
      this.transitionTo(CircuitState.DEGRADED, `Degraded threshold (${this.degradedThreshold}) reached`, now);
    }
  }

  /**
   * Internal transition handler with event emission.
   */
  transitionTo(newState, reason = '', now = Date.now()) {
    if (this.state === newState) return;
    const oldState = this.state;
    this.state = newState;
    this.lastStateChangeTime = now;

    if (newState === CircuitState.HEALTHY) {
      this.consecutiveFailures = 0;
    }

    this.emit(FailoverEventType.STATE_CHANGE, {
      endpoint: this.endpoint,
      previousState: oldState,
      newState,
      reason,
      consecutiveFailures: this.consecutiveFailures,
      timestamp: now
    });
  }

  reset() {
    this.state = CircuitState.HEALTHY;
    this.consecutiveFailures = 0;
    this.consecutiveSuccesses = 0;
    this.lastFailureTime = null;
    this.lastSuccessTime = null;
    this.lastStateChangeTime = Date.now();
  }
}

// ============================================================================
// 5. ENDPOINT NODE & METRICS
// ============================================================================

export class EndpointNode {
  constructor(endpointConfig, globalConfig = {}) {
    if (typeof endpointConfig === 'string') {
      this.url = endpointConfig;
      this.weight = 100;
      this.name = endpointConfig;
    } else {
      this.url = endpointConfig.url;
      this.weight = endpointConfig.weight ?? 100;
      this.name = endpointConfig.name ?? endpointConfig.url;
    }

    this.circuitBreaker = new CircuitBreaker(this.url, {
      failureThreshold: globalConfig.failureThreshold,
      degradedThreshold: globalConfig.degradedThreshold,
      recoverySuccessThreshold: globalConfig.recoverySuccessThreshold,
      cooldownPeriodMs: globalConfig.cooldownPeriodMs
    });

    this.metrics = {
      totalRequests: 0,
      successCount: 0,
      failureCount: 0,
      failoverCount: 0,
      totalLatencyMs: 0,
      avgLatencyMs: 0
    };
  }

  recordLatency(latencyMs) {
    this.metrics.totalLatencyMs += latencyMs;
    this.metrics.avgLatencyMs = Math.round(this.metrics.totalLatencyMs / (this.metrics.totalRequests || 1));
  }
}

// ============================================================================
// 6. RESILIENT RPC CLIENT IMPLEMENTATION
// ============================================================================

export class ResilientRpcClient extends EventEmitter {
  /**
   * @param {Object} options
   * @param {string[]|Object[]} options.endpoints - Ordered list of RPC endpoint URLs or node configs
   * @param {Function} [options.fetcher] - Custom fetch implementation for testing / zero-IO
   * @param {number} [options.timeoutMs] - Request timeout in ms
   * @param {number} [options.maxRetriesPerEndpoint] - Retries per endpoint before failover
   * @param {number} [options.baseBackoffMs] - Initial backoff duration in ms
   * @param {number} [options.maxBackoffMs] - Maximum backoff duration in ms
   * @param {number} [options.backoffMultiplier] - Exponential multiplier
   * @param {boolean|number} [options.jitter] - Jitter configuration (boolean or custom factor)
   * @param {number} [options.expectedChainId] - Chain ID validation if specified (e.g. 8453)
   * @param {number} [options.failureThreshold] - Failures before circuit trips
   * @param {number} [options.cooldownPeriodMs] - Cooldown duration before recovery probe
   * @param {boolean} [options.preserveIdempotency] - Whether to preserve and propagate idempotency keys
   */
  constructor(options = {}) {
    super();

    if (!options.endpoints || !Array.isArray(options.endpoints) || options.endpoints.length === 0) {
      throw new Error('ResilientRpcClient requires a non-empty array of endpoint URLs or configs');
    }

    this.config = {
      ...DEFAULT_CONFIG,
      ...options
    };

    this.fetcher = options.fetcher || globalThis.fetch;
    if (typeof this.fetcher !== 'function') {
      throw new Error('Valid fetcher function is required');
    }

    // Initialize ordered endpoint pool
    this.endpoints = options.endpoints.map(ep => new EndpointNode(ep, this.config));

    // Aggregate metrics
    this.globalMetrics = {
      totalDispatchedRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      totalFailovers: 0,
      circuitTrips: 0
    };

    // Forward circuit breaker events
    for (const ep of this.endpoints) {
      ep.circuitBreaker.on(FailoverEventType.STATE_CHANGE, evt => {
        if (evt.newState === CircuitState.TRIPPED) {
          this.globalMetrics.circuitTrips++;
          this.emit(FailoverEventType.CIRCUIT_TRIP, evt);
        } else if (evt.newState === CircuitState.HEALTHY && evt.previousState === CircuitState.RECOVERY) {
          this.emit(FailoverEventType.CIRCUIT_RECOVERED, evt);
        }
        this.emit(FailoverEventType.STATE_CHANGE, evt);
      });
    }
  }

  /**
   * Generates or normalizes an idempotency key.
   */
  resolveIdempotencyKey(request, options = {}) {
    if (options.idempotencyKey) {
      return String(options.idempotencyKey);
    }
    if (options.headers && options.headers['x-idempotency-key']) {
      return String(options.headers['x-idempotency-key']);
    }

    // Deterministically hash the request payload if available to guarantee idempotent fingerprinting
    const payloadStr = JSON.stringify({
      method: request.method,
      params: request.params,
      id: request.id
    });
    const hash = crypto.createHash('sha256').update(payloadStr).digest('hex').substring(0, 32);
    return `idem-rpc-${hash}`;
  }

  /**
   * Computes exponential backoff with configurable jitter.
   */
  computeBackoff(attempt, now = Date.now()) {
    const exponent = Math.max(0, attempt);
    const rawDelay = this.config.baseBackoffMs * Math.pow(this.config.backoffMultiplier, exponent);
    const boundedDelay = Math.min(rawDelay, this.config.maxBackoffMs);

    let jitterVal = 0;
    if (this.config.jitter === true) {
      // Full jitter: random between 0 and boundedDelay * 0.5
      jitterVal = Math.floor(Math.random() * (boundedDelay * 0.5));
    } else if (typeof this.config.jitter === 'number') {
      jitterVal = Math.floor(this.config.jitter);
    }

    return boundedDelay + jitterVal;
  }

  /**
   * Pauses execution for the calculated backoff.
   */
  async sleep(ms) {
    if (ms <= 0) return;
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Dispatches a single JSON-RPC call across the pool with deterministic failover,
   * circuit-breaker checks, and strict idempotency key preservation.
   * 
   * @param {Object} request - Standard JSON-RPC 2.0 request payload { method, params, id, jsonrpc }
   * @param {Object} [options] - Additional dispatch options (headers, idempotencyKey, timeoutMs)
   * @returns {Promise<any>} Result payload from successful JSON-RPC execution
   */
  async dispatch(request, options = {}) {
    this.globalMetrics.totalDispatchedRequests++;
    const startTime = Date.now();

    // 1. Normalize JSON-RPC payload
    const rpcPayload = {
      jsonrpc: request.jsonrpc || '2.0',
      id: request.id !== undefined ? request.id : Date.now(),
      method: request.method,
      params: request.params ?? []
    };

    if (!rpcPayload.method || typeof rpcPayload.method !== 'string') {
      throw new DeterministicRpcError('JSON-RPC method must be a non-empty string', {
        code: -32600,
        data: request
      });
    }

    // 2. Establish and lock the idempotency key for all attempts
    const idempotencyKey = this.resolveIdempotencyKey(rpcPayload, options);
    const attemptHistory = [];

    // Filter available endpoints based on circuit breaker state
    const now = Date.now();
    let eligibleEndpoints = this.endpoints.filter(ep => ep.circuitBreaker.canExecute(now));

    // If all endpoints are tripped, fallback to attempting any that can probe or highest priority
    if (eligibleEndpoints.length === 0) {
      eligibleEndpoints = [...this.endpoints];
    }

    let lastError = null;
    let failoverCounter = 0;

    // 3. Deterministic Sequential Failover Loop
    for (let epIndex = 0; epIndex < eligibleEndpoints.length; epIndex++) {
      const endpointNode = eligibleEndpoints[epIndex];
      const endpointUrl = endpointNode.url;

      // Ensure circuit breaker allows execution
      if (!endpointNode.circuitBreaker.canExecute(Date.now())) {
        continue;
      }

      // Per-endpoint retry loop
      const maxRetries = this.config.maxRetriesPerEndpoint;
      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        endpointNode.metrics.totalRequests++;
        const requestStart = Date.now();

        try {
          // Prepare headers preserving exact idempotency key
          const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...(options.headers || {})
          };

          if (this.config.preserveIdempotency) {
            headers['x-idempotency-key'] = idempotencyKey;
          }

          // Build abort controller for timeout
          const timeoutMs = options.timeoutMs || this.config.timeoutMs;
          const controller = new AbortController();
          const timer = setTimeout(() => controller.abort(), timeoutMs);

          let response;
          try {
            response = await this.fetcher(endpointUrl, {
              method: 'POST',
              headers,
              body: JSON.stringify(rpcPayload),
              signal: controller.signal
            });
          } finally {
            clearTimeout(timer);
          }

          const requestLatency = Date.now() - requestStart;
          endpointNode.recordLatency(requestLatency);

          // Check HTTP Status
          if (!response.ok) {
            let errorText = '';
            try {
              errorText = await response.text();
            } catch (_) {}

            const httpErr = new Error(`HTTP ${response.status}: ${response.statusText || errorText || 'Server Error'}`);
            httpErr.statusCode = response.status;
            httpErr.status = response.status;
            httpErr.endpoint = endpointUrl;

            const classification = classifyError(httpErr, response);
            if (!classification.isTransient) {
              // Deterministic HTTP error (e.g. 400 Bad Request, 401 Unauthorized)
              endpointNode.circuitBreaker.recordFailure(httpErr);
              throw new DeterministicRpcError(httpErr.message, {
                statusCode: response.status,
                endpoint: endpointUrl,
                idempotencyKey
              });
            }

            // Transient error: throw to trigger retry / failover
            throw new TransientRpcError(httpErr.message, {
              statusCode: response.status,
              endpoint: endpointUrl,
              idempotencyKey
            });
          }

          // Parse JSON-RPC Response Body
          const data = await response.json();

          // 4. Validate Chain ID if requested
          if (this.config.expectedChainId && rpcPayload.method === 'eth_chainId') {
            const actualChainId = typeof data.result === 'string' ? parseInt(data.result, 16) : Number(data.result);
            if (actualChainId !== this.config.expectedChainId) {
              const chainErr = new ChainIdMismatchError(endpointUrl, this.config.expectedChainId, actualChainId);
              endpointNode.circuitBreaker.recordFailure(chainErr);
              throw chainErr;
            }
          }

          // 5. Evaluate JSON-RPC Error object
          if (data && data.error) {
            const rpcErr = new Error(data.error.message || 'RPC returned error object');
            rpcErr.code = data.error.code;
            rpcErr.data = data.error.data;
            rpcErr.endpoint = endpointUrl;

            const classification = classifyError(rpcErr);
            if (!classification.isTransient) {
              // Transport succeeded, but execution failed deterministically on-chain!
              // Endpoint is healthy (did not crash or timeout), so record success on transport
              endpointNode.circuitBreaker.recordSuccess();
              endpointNode.metrics.successCount++;
              this.globalMetrics.successfulRequests++;

              throw new DeterministicRpcError(data.error.message, {
                code: data.error.code,
                data: data.error.data,
                endpoint: endpointUrl,
                idempotencyKey
              });
            } else {
              // Node returned transient error in JSON body (e.g. node syncing, node rate limited)
              throw new TransientRpcError(data.error.message, {
                code: data.error.code,
                data: data.error.data,
                endpoint: endpointUrl,
                idempotencyKey
              });
            }
          }

          // SUCCESS!
          endpointNode.circuitBreaker.recordSuccess();
          endpointNode.metrics.successCount++;
          this.globalMetrics.successfulRequests++;

          this.emit(FailoverEventType.REQUEST_SUCCESS, {
            endpoint: endpointUrl,
            method: rpcPayload.method,
            idempotencyKey,
            latencyMs: requestLatency,
            attempts: attempt + 1,
            failovers: failoverCounter
          });

          return data.result;

        } catch (err) {
          lastError = err;
          attemptHistory.push({
            endpoint: endpointUrl,
            attempt,
            error: err.message,
            statusCode: err.statusCode,
            code: err.code,
            timestamp: Date.now()
          });

          // Immediate rethrow for deterministic errors
          if (err instanceof DeterministicRpcError) {
            this.globalMetrics.failedRequests++;
            endpointNode.metrics.failureCount++;
            throw err;
          }

          // Classify error to decide on retry / failover
          const classification = classifyError(err);
          if (!classification.isTransient) {
            this.globalMetrics.failedRequests++;
            endpointNode.metrics.failureCount++;
            endpointNode.circuitBreaker.recordFailure(err);
            throw new DeterministicRpcError(err.message, {
              code: err.code,
              endpoint: endpointUrl,
              idempotencyKey,
              rawError: err
            });
          }

          // Transient error handling:
          endpointNode.circuitBreaker.recordFailure(err);
          endpointNode.metrics.failureCount++;

          // If within retry limit for this endpoint, backoff and retry
          if (attempt < maxRetries) {
            const backoffMs = this.computeBackoff(attempt);
            this.emit(FailoverEventType.REQUEST_RETRY, {
              endpoint: endpointUrl,
              attempt: attempt + 1,
              maxRetries,
              backoffMs,
              reason: err.message,
              idempotencyKey
            });
            await this.sleep(backoffMs);
            continue; // retry on same endpoint
          }

          // Retries exhausted for this endpoint -> proceed to failover to next endpoint
          break;
        }
      } // end attempt loop for current endpoint

      // Check if another endpoint exists to fail over to
      const nextIndex = epIndex + 1;
      if (nextIndex < eligibleEndpoints.length) {
        failoverCounter++;
        this.globalMetrics.totalFailovers++;
        endpointNode.metrics.failoverCount++;

        const nextEndpoint = eligibleEndpoints[nextIndex];
        this.emit(FailoverEventType.FAILOVER, {
          timestamp: Date.now(),
          fromEndpoint: endpointUrl,
          toEndpoint: nextEndpoint.url,
          reason: lastError?.message || 'Endpoint retries exhausted',
          attempt: failoverCounter,
          idempotencyKey,
          payloadId: rpcPayload.id
        });

        // Small inter-endpoint jittered cooldown
        const interEndpointDelay = Math.min(this.config.baseBackoffMs, 100);
        await this.sleep(interEndpointDelay);
      }
    } // end endpoint loop

    // All eligible endpoints exhausted
    this.globalMetrics.failedRequests++;
    throw new EndpointExhaustionError(
      `All ${eligibleEndpoints.length} RPC endpoints exhausted after sequential failover. Last error: ${lastError?.message || 'unknown'}`,
      {
        attemptHistory,
        idempotencyKey,
        endpoint: eligibleEndpoints.map(e => e.url).join(', ')
      }
    );
  }

  /**
   * Retrieves overall runtime metrics and endpoint states.
   */
  getMetrics() {
    return {
      global: { ...this.globalMetrics },
      endpoints: this.endpoints.map(ep => ({
        url: ep.url,
        state: ep.circuitBreaker.state,
        consecutiveFailures: ep.circuitBreaker.consecutiveFailures,
        consecutiveSuccesses: ep.circuitBreaker.consecutiveSuccesses,
        metrics: { ...ep.metrics }
      }))
    };
  }

  /**
   * Returns current state for each endpoint.
   */
  getEndpointStates() {
    const states = {};
    for (const ep of this.endpoints) {
      states[ep.url] = ep.circuitBreaker.state;
    }
    return states;
  }

  /**
   * Resets all circuit breakers and health metrics.
   */
  resetAll() {
    for (const ep of this.endpoints) {
      ep.circuitBreaker.reset();
      ep.metrics = {
        totalRequests: 0,
        successCount: 0,
        failureCount: 0,
        failoverCount: 0,
        totalLatencyMs: 0,
        avgLatencyMs: 0
      };
    }
    this.globalMetrics = {
      totalDispatchedRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      totalFailovers: 0,
      circuitTrips: 0
    };
  }
}
