/**
 * Resilient Deterministic RPC Failover Subsystem (TypeScript Definition & Implementation)
 * Target: Bounty Plaza Issue #1635 (Source: NSPG13/agent-bounties#1500)
 */

import { EventEmitter } from 'node:events';
import crypto from 'node:crypto';

export type CircuitState = 'healthy' | 'degraded' | 'tripped' | 'recovery';

export const CircuitStateEnum = {
  HEALTHY: 'healthy' as CircuitState,
  DEGRADED: 'degraded' as CircuitState,
  TRIPPED: 'tripped' as CircuitState,
  RECOVERY: 'recovery' as CircuitState
};

export type FailoverEventType =
  | 'failover'
  | 'state_change'
  | 'request_retry'
  | 'request_success'
  | 'request_failure'
  | 'circuit_trip'
  | 'circuit_recovered'
  | 'endpoint_health';

export type ErrorCategory = 'transient' | 'deterministic';

export interface RpcRequest {
  jsonrpc?: string;
  id?: string | number;
  method: string;
  params?: any[] | Record<string, any>;
}

export interface RpcResponse<T = any> {
  jsonrpc: string;
  id: string | number;
  result?: T;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
}

export interface DispatchOptions {
  headers?: Record<string, string>;
  idempotencyKey?: string;
  timeoutMs?: number;
}

export interface EndpointConfig {
  url: string;
  weight?: number;
  name?: string;
}

export interface ClientConfig {
  timeoutMs?: number;
  maxRetriesPerEndpoint?: number;
  baseBackoffMs?: number;
  maxBackoffMs?: number;
  backoffMultiplier?: number;
  jitter?: boolean | number;
  failureThreshold?: number;
  degradedThreshold?: number;
  recoverySuccessThreshold?: number;
  cooldownPeriodMs?: number;
  preserveIdempotency?: boolean;
  expectedChainId?: number | null;
  fetcher?: (url: string, init?: any) => Promise<any>;
}

export interface FailoverEventPayload {
  timestamp: number;
  fromEndpoint: string;
  toEndpoint: string;
  reason: string;
  attempt: number;
  idempotencyKey: string;
  payloadId?: string | number;
}

export interface StateChangeEventPayload {
  endpoint: string;
  previousState: CircuitState;
  newState: CircuitState;
  reason: string;
  consecutiveFailures: number;
  timestamp: number;
}

export class RpcError extends Error {
  code: number | null;
  data: any;
  category: ErrorCategory;
  statusCode: number | null;
  endpoint: string | null;
  idempotencyKey: string | null;
  rawError: any;

  constructor(message: string, options: any = {}) {
    super(message);
    this.name = this.constructor.name;
    this.code = options.code ?? null;
    this.data = options.data ?? null;
    this.category = options.category ?? 'transient';
    this.statusCode = options.statusCode ?? null;
    this.endpoint = options.endpoint ?? null;
    this.idempotencyKey = options.idempotencyKey ?? null;
    this.rawError = options.rawError ?? null;
  }
}

export class DeterministicRpcError extends RpcError {
  constructor(message: string, options: any = {}) {
    super(message, { ...options, category: 'deterministic' });
  }
}

export class TransientRpcError extends RpcError {
  constructor(message: string, options: any = {}) {
    super(message, { ...options, category: 'transient' });
  }
}

export class EndpointExhaustionError extends RpcError {
  attemptHistory: any[];

  constructor(message: string, options: any = {}) {
    super(message, { ...options, category: 'transient' });
    this.attemptHistory = options.attemptHistory ?? [];
  }
}

export class CircuitTrippedError extends RpcError {
  constructor(endpoint: string, options: any = {}) {
    super(`Circuit breaker tripped for endpoint: ${endpoint}`, {
      ...options,
      endpoint,
      category: 'transient'
    });
  }
}

export class ChainIdMismatchError extends DeterministicRpcError {
  constructor(endpoint: string, expected: number, actual: number) {
    super(`Chain ID mismatch for endpoint ${endpoint}: expected ${expected}, got ${actual}`, {
      endpoint,
      data: { expected, actual }
    });
  }
}

export function classifyError(err: any, response: any = null): { isTransient: boolean; category: ErrorCategory; reason: string } {
  if (!err) {
    return { isTransient: false, category: 'deterministic', reason: 'unknown' };
  }

  if (err instanceof DeterministicRpcError) {
    return { isTransient: false, category: 'deterministic', reason: err.message };
  }
  if (err instanceof TransientRpcError) {
    return { isTransient: true, category: 'transient', reason: err.message };
  }

  const status = response?.status || err.statusCode || err.status;
  const errMsg = (err.message || '').toLowerCase();
  const errCode = (err.code !== undefined && err.code !== null) ? String(err.code) : '';

  if (status === 429) {
    return { isTransient: true, category: 'transient', reason: 'HTTP 429 Rate Limit' };
  }
  if (status >= 500 && status <= 599) {
    return { isTransient: true, category: 'transient', reason: `HTTP ${status} Server Error` };
  }

  const transientCodes = ['ECONNREFUSED', 'ETIMEDOUT', 'ENOTFOUND', 'EAI_AGAIN', 'ECONNRESET', 'UND_ERR_CONNECT_TIMEOUT'];
  if (transientCodes.includes(errCode) || transientCodes.some(c => errMsg.includes(c.toLowerCase()))) {
    return { isTransient: true, category: 'transient', reason: `Network fault: ${errCode || 'connection failure'}` };
  }

  if (err.name === 'AbortError' || errMsg.includes('timeout') || errMsg.includes('timed out') || errMsg.includes('abort')) {
    return { isTransient: true, category: 'transient', reason: 'Request timeout' };
  }

  if (errMsg.includes('rate limit') || errMsg.includes('too many requests')) {
    return { isTransient: true, category: 'transient', reason: 'Rate limited' };
  }

  const deterministicCodes = [-32700, -32600, -32601, -32602, -32603, -32000, -32003];
  const numCode = Number(err.code);
  if (deterministicCodes.includes(numCode)) {
    return { isTransient: false, category: 'deterministic', reason: `JSON-RPC Deterministic Error: ${numCode}` };
  }

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
      return { isTransient: false, category: 'deterministic', reason: `Deterministic business error: ${pattern}` };
    }
  }

  if (errMsg.includes('fetch failed') || errMsg.includes('network') || errMsg.includes('socket')) {
    return { isTransient: true, category: 'transient', reason: 'Unclassified network error' };
  }

  return { isTransient: false, category: 'deterministic', reason: 'Unclassified deterministic error' };
}

export class CircuitBreaker extends EventEmitter {
  endpoint: string;
  failureThreshold: number;
  degradedThreshold: number;
  recoverySuccessThreshold: number;
  cooldownPeriodMs: number;
  state: CircuitState;
  consecutiveFailures: number;
  consecutiveSuccesses: number;
  totalSuccesses: number;
  totalFailures: number;
  lastFailureTime: number | null;
  lastSuccessTime: number | null;
  lastStateChangeTime: number;

  constructor(endpoint: string, options: any = {}) {
    super();
    this.endpoint = endpoint;
    this.failureThreshold = options.failureThreshold ?? 3;
    this.degradedThreshold = options.degradedThreshold ?? 1;
    this.recoverySuccessThreshold = options.recoverySuccessThreshold ?? 2;
    this.cooldownPeriodMs = options.cooldownPeriodMs ?? 10000;
    this.state = 'healthy';
    this.consecutiveFailures = 0;
    this.consecutiveSuccesses = 0;
    this.totalSuccesses = 0;
    this.totalFailures = 0;
    this.lastFailureTime = null;
    this.lastSuccessTime = null;
    this.lastStateChangeTime = Date.now();
  }

  canExecute(now: number = Date.now()): boolean {
    if (this.state === 'healthy' || this.state === 'degraded') return true;
    if (this.state === 'tripped') {
      const elapsed = now - (this.lastFailureTime || 0);
      if (elapsed >= this.cooldownPeriodMs) {
        this.transitionTo('recovery', 'Cooldown elapsed, entering recovery probe mode', now);
        return true;
      }
      return false;
    }
    return this.state === 'recovery';
  }

  recordSuccess(now: number = Date.now()): void {
    this.lastSuccessTime = now;
    this.totalSuccesses++;
    this.consecutiveFailures = 0;

    if (this.state === 'recovery') {
      this.consecutiveSuccesses++;
      if (this.consecutiveSuccesses >= this.recoverySuccessThreshold) {
        this.transitionTo('healthy', `Endpoint recovered after ${this.consecutiveSuccesses} consecutive successes`, now);
      }
    } else if (this.state === 'degraded') {
      this.consecutiveSuccesses++;
      this.transitionTo('healthy', 'Endpoint recovered from degraded state on success', now);
    } else {
      this.consecutiveSuccesses++;
    }
  }

  recordFailure(err: Error, now: number = Date.now()): void {
    this.lastFailureTime = now;
    this.totalFailures++;
    this.consecutiveSuccesses = 0;
    this.consecutiveFailures++;

    if (this.state === 'recovery') {
      this.transitionTo('tripped', `Probe failed during recovery: ${err.message}`, now);
    } else if (this.consecutiveFailures >= this.failureThreshold) {
      this.transitionTo('tripped', `Failure threshold reached`, now);
    } else if (this.consecutiveFailures >= this.degradedThreshold && this.state === 'healthy') {
      this.transitionTo('degraded', `Degraded threshold reached`, now);
    }
  }

  transitionTo(newState: CircuitState, reason: string = '', now: number = Date.now()): void {
    if (this.state === newState) return;
    const oldState = this.state;
    this.state = newState;
    this.lastStateChangeTime = now;

    if (newState === 'healthy') {
      this.consecutiveFailures = 0;
    }

    const payload: StateChangeEventPayload = {
      endpoint: this.endpoint,
      previousState: oldState,
      newState,
      reason,
      consecutiveFailures: this.consecutiveFailures,
      timestamp: now
    };
    this.emit('state_change', payload);
  }

  reset(): void {
    this.state = 'healthy';
    this.consecutiveFailures = 0;
    this.consecutiveSuccesses = 0;
    this.lastFailureTime = null;
    this.lastSuccessTime = null;
    this.lastStateChangeTime = Date.now();
  }
}

export class EndpointNode {
  url: string;
  weight: number;
  name: string;
  circuitBreaker: CircuitBreaker;
  metrics: {
    totalRequests: number;
    successCount: number;
    failureCount: number;
    failoverCount: number;
    totalLatencyMs: number;
    avgLatencyMs: number;
  };

  constructor(endpointConfig: string | EndpointConfig, globalConfig: any = {}) {
    if (typeof endpointConfig === 'string') {
      this.url = endpointConfig;
      this.weight = 100;
      this.name = endpointConfig;
    } else {
      this.url = endpointConfig.url;
      this.weight = endpointConfig.weight ?? 100;
      this.name = endpointConfig.name ?? endpointConfig.url;
    }

    this.circuitBreaker = new CircuitBreaker(this.url, globalConfig);
    this.metrics = {
      totalRequests: 0,
      successCount: 0,
      failureCount: 0,
      failoverCount: 0,
      totalLatencyMs: 0,
      avgLatencyMs: 0
    };
  }

  recordLatency(latencyMs: number): void {
    this.metrics.totalLatencyMs += latencyMs;
    this.metrics.avgLatencyMs = Math.round(this.metrics.totalLatencyMs / (this.metrics.totalRequests || 1));
  }
}

export class ResilientRpcClient extends EventEmitter {
  config: Required<ClientConfig>;
  fetcher: (url: string, init?: any) => Promise<any>;
  endpoints: EndpointNode[];
  globalMetrics: {
    totalDispatchedRequests: number;
    successfulRequests: number;
    failedRequests: number;
    totalFailovers: number;
    circuitTrips: number;
  };

  constructor(options: { endpoints: Array<string | EndpointConfig> } & ClientConfig) {
    super();

    if (!options.endpoints || !Array.isArray(options.endpoints) || options.endpoints.length === 0) {
      throw new Error('ResilientRpcClient requires a non-empty array of endpoint URLs or configs');
    }

    this.config = {
      timeoutMs: options.timeoutMs ?? 8000,
      maxRetriesPerEndpoint: options.maxRetriesPerEndpoint ?? 2,
      baseBackoffMs: options.baseBackoffMs ?? 100,
      maxBackoffMs: options.maxBackoffMs ?? 3000,
      backoffMultiplier: options.backoffMultiplier ?? 2,
      jitter: options.jitter ?? true,
      failureThreshold: options.failureThreshold ?? 3,
      degradedThreshold: options.degradedThreshold ?? 1,
      recoverySuccessThreshold: options.recoverySuccessThreshold ?? 2,
      cooldownPeriodMs: options.cooldownPeriodMs ?? 10000,
      preserveIdempotency: options.preserveIdempotency ?? true,
      expectedChainId: options.expectedChainId ?? null,
      fetcher: options.fetcher || globalThis.fetch
    };

    this.fetcher = this.config.fetcher;
    this.endpoints = options.endpoints.map(ep => new EndpointNode(ep, this.config));
    this.globalMetrics = {
      totalDispatchedRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      totalFailovers: 0,
      circuitTrips: 0
    };

    for (const ep of this.endpoints) {
      ep.circuitBreaker.on('state_change', evt => {
        if (evt.newState === 'tripped') {
          this.globalMetrics.circuitTrips++;
          this.emit('circuit_trip', evt);
        } else if (evt.newState === 'healthy' && evt.previousState === 'recovery') {
          this.emit('circuit_recovered', evt);
        }
        this.emit('state_change', evt);
      });
    }
  }

  resolveIdempotencyKey(request: RpcRequest, options: DispatchOptions = {}): string {
    if (options.idempotencyKey) return String(options.idempotencyKey);
    if (options.headers && options.headers['x-idempotency-key']) return String(options.headers['x-idempotency-key']);

    const payloadStr = JSON.stringify({ method: request.method, params: request.params, id: request.id });
    const hash = crypto.createHash('sha256').update(payloadStr).digest('hex').substring(0, 32);
    return `idem-rpc-${hash}`;
  }

  computeBackoff(attempt: number): number {
    const rawDelay = this.config.baseBackoffMs * Math.pow(this.config.backoffMultiplier, Math.max(0, attempt));
    const boundedDelay = Math.min(rawDelay, this.config.maxBackoffMs);
    let jitterVal = 0;
    if (this.config.jitter === true) {
      jitterVal = Math.floor(Math.random() * (boundedDelay * 0.5));
    } else if (typeof this.config.jitter === 'number') {
      jitterVal = Math.floor(this.config.jitter);
    }
    return boundedDelay + jitterVal;
  }

  async sleep(ms: number): Promise<void> {
    if (ms <= 0) return;
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async dispatch<T = any>(request: RpcRequest, options: DispatchOptions = {}): Promise<T> {
    this.globalMetrics.totalDispatchedRequests++;
    const rpcPayload: RpcRequest = {
      jsonrpc: request.jsonrpc || '2.0',
      id: request.id !== undefined ? request.id : Date.now(),
      method: request.method,
      params: request.params ?? []
    };

    if (!rpcPayload.method || typeof rpcPayload.method !== 'string') {
      throw new DeterministicRpcError('JSON-RPC method must be a non-empty string', { code: -32600, data: request });
    }

    const idempotencyKey = this.resolveIdempotencyKey(rpcPayload, options);
    const attemptHistory: any[] = [];
    const now = Date.now();
    let eligibleEndpoints = this.endpoints.filter(ep => ep.circuitBreaker.canExecute(now));
    if (eligibleEndpoints.length === 0) eligibleEndpoints = [...this.endpoints];

    let lastError: any = null;
    let failoverCounter = 0;

    for (let epIndex = 0; epIndex < eligibleEndpoints.length; epIndex++) {
      const endpointNode = eligibleEndpoints[epIndex];
      const endpointUrl = endpointNode.url;

      if (!endpointNode.circuitBreaker.canExecute(Date.now())) continue;

      const maxRetries = this.config.maxRetriesPerEndpoint;
      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        endpointNode.metrics.totalRequests++;
        const requestStart = Date.now();

        try {
          const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...(options.headers || {})
          };

          if (this.config.preserveIdempotency) {
            headers['x-idempotency-key'] = idempotencyKey;
          }

          const timeoutMs = options.timeoutMs || this.config.timeoutMs;
          const controller = new AbortController();
          const timer = setTimeout(() => controller.abort(), timeoutMs);

          let response: any;
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

          endpointNode.recordLatency(Date.now() - requestStart);

          if (!response.ok) {
            let errorText = '';
            try { errorText = await response.text(); } catch (_) {}
            const httpErr: any = new Error(`HTTP ${response.status}: ${response.statusText || errorText || 'Server Error'}`);
            httpErr.statusCode = response.status;
            httpErr.status = response.status;
            httpErr.endpoint = endpointUrl;

            const classification = classifyError(httpErr, response);
            if (!classification.isTransient) {
              endpointNode.circuitBreaker.recordFailure(httpErr);
              throw new DeterministicRpcError(httpErr.message, { statusCode: response.status, endpoint: endpointUrl, idempotencyKey });
            }
            throw new TransientRpcError(httpErr.message, { statusCode: response.status, endpoint: endpointUrl, idempotencyKey });
          }

          const data: RpcResponse<T> = await response.json();

          if (this.config.expectedChainId && rpcPayload.method === 'eth_chainId') {
            const actualChainId = typeof data.result === 'string' ? parseInt(data.result, 16) : Number(data.result);
            if (actualChainId !== this.config.expectedChainId) {
              const chainErr = new ChainIdMismatchError(endpointUrl, this.config.expectedChainId, actualChainId);
              endpointNode.circuitBreaker.recordFailure(chainErr);
              throw chainErr;
            }
          }

          if (data && data.error) {
            const rpcErr: any = new Error(data.error.message || 'RPC returned error object');
            rpcErr.code = data.error.code;
            rpcErr.data = data.error.data;
            rpcErr.endpoint = endpointUrl;

            const classification = classifyError(rpcErr);
            if (!classification.isTransient) {
              endpointNode.circuitBreaker.recordSuccess();
              endpointNode.metrics.successCount++;
              this.globalMetrics.successfulRequests++;
              throw new DeterministicRpcError(data.error.message, { code: data.error.code, data: data.error.data, endpoint: endpointUrl, idempotencyKey });
            } else {
              throw new TransientRpcError(data.error.message, { code: data.error.code, data: data.error.data, endpoint: endpointUrl, idempotencyKey });
            }
          }

          endpointNode.circuitBreaker.recordSuccess();
          endpointNode.metrics.successCount++;
          this.globalMetrics.successfulRequests++;

          this.emit('request_success', {
            endpoint: endpointUrl,
            method: rpcPayload.method,
            idempotencyKey,
            latencyMs: Date.now() - requestStart,
            attempts: attempt + 1,
            failovers: failoverCounter
          });

          return data.result as T;
        } catch (err: any) {
          lastError = err;
          attemptHistory.push({
            endpoint: endpointUrl,
            attempt,
            error: err.message,
            statusCode: err.statusCode,
            code: err.code,
            timestamp: Date.now()
          });

          if (err instanceof DeterministicRpcError) {
            this.globalMetrics.failedRequests++;
            endpointNode.metrics.failureCount++;
            throw err;
          }

          const classification = classifyError(err);
          if (!classification.isTransient) {
            this.globalMetrics.failedRequests++;
            endpointNode.metrics.failureCount++;
            endpointNode.circuitBreaker.recordFailure(err);
            throw new DeterministicRpcError(err.message, { code: err.code, endpoint: endpointUrl, idempotencyKey, rawError: err });
          }

          endpointNode.circuitBreaker.recordFailure(err);
          endpointNode.metrics.failureCount++;

          if (attempt < maxRetries) {
            const backoffMs = this.computeBackoff(attempt);
            this.emit('request_retry', { endpoint: endpointUrl, attempt: attempt + 1, maxRetries, backoffMs, reason: err.message, idempotencyKey });
            await this.sleep(backoffMs);
            continue;
          }
          break;
        }
      }

      const nextIndex = epIndex + 1;
      if (nextIndex < eligibleEndpoints.length) {
        failoverCounter++;
        this.globalMetrics.totalFailovers++;
        endpointNode.metrics.failoverCount++;

        const nextEndpoint = eligibleEndpoints[nextIndex];
        const failoverPayload: FailoverEventPayload = {
          timestamp: Date.now(),
          fromEndpoint: endpointUrl,
          toEndpoint: nextEndpoint.url,
          reason: lastError?.message || 'Endpoint retries exhausted',
          attempt: failoverCounter,
          idempotencyKey,
          payloadId: rpcPayload.id
        };
        this.emit('failover', failoverPayload);
        await this.sleep(Math.min(this.config.baseBackoffMs, 100));
      }
    }

    this.globalMetrics.failedRequests++;
    throw new EndpointExhaustionError(
      `All ${eligibleEndpoints.length} RPC endpoints exhausted after sequential failover. Last error: ${lastError?.message || 'unknown'}`,
      { attemptHistory, idempotencyKey, endpoint: eligibleEndpoints.map(e => e.url).join(', ') }
    );
  }

  getMetrics(): any {
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

  getEndpointStates(): Record<string, CircuitState> {
    const states: Record<string, CircuitState> = {};
    for (const ep of this.endpoints) states[ep.url] = ep.circuitBreaker.state;
    return states;
  }

  resetAll(): void {
    for (const ep of this.endpoints) {
      ep.circuitBreaker.reset();
      ep.metrics = { totalRequests: 0, successCount: 0, failureCount: 0, failoverCount: 0, totalLatencyMs: 0, avgLatencyMs: 0 };
    }
    this.globalMetrics = { totalDispatchedRequests: 0, successfulRequests: 0, failedRequests: 0, totalFailovers: 0, circuitTrips: 0 };
  }
}
