"""
Resilient Deterministic RPC Failover Subsystem (Python Implementation)
Target: Bounty Plaza Issue #1635 (Source: NSPG13/agent-bounties#1500)
"""

import time
import math
import random
import hashlib
import json
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum


class CircuitState(str, Enum):
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    TRIPPED = 'tripped'
    RECOVERY = 'recovery'


class FailoverEventType(str, Enum):
    FAILOVER = 'failover'
    STATE_CHANGE = 'state_change'
    REQUEST_RETRY = 'request_retry'
    REQUEST_SUCCESS = 'request_success'
    REQUEST_FAILURE = 'request_failure'
    CIRCUIT_TRIP = 'circuit_trip'
    CIRCUIT_RECOVERED = 'circuit_recovered'
    ENDPOINT_HEALTH = 'endpoint_health'


class ErrorCategory(str, Enum):
    TRANSIENT = 'transient'
    DETERMINISTIC = 'deterministic'


class RpcError(Exception):
    def __init__(self, message: str, code: Optional[int] = None, data: Any = None,
                 category: ErrorCategory = ErrorCategory.TRANSIENT,
                 status_code: Optional[int] = None, endpoint: Optional[str] = None,
                 idempotency_key: Optional[str] = None, raw_error: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data
        self.category = category
        self.status_code = status_code
        self.endpoint = endpoint
        self.idempotency_key = idempotency_key
        self.raw_error = raw_error


class DeterministicRpcError(RpcError):
    def __init__(self, message: str, **kwargs):
        kwargs['category'] = ErrorCategory.DETERMINISTIC
        super().__init__(message, **kwargs)


class TransientRpcError(RpcError):
    def __init__(self, message: str, **kwargs):
        kwargs['category'] = ErrorCategory.TRANSIENT
        super().__init__(message, **kwargs)


class EndpointExhaustionError(RpcError):
    def __init__(self, message: str, attempt_history: Optional[List[Dict[str, Any]]] = None, **kwargs):
        super().__init__(message, category=ErrorCategory.TRANSIENT, **kwargs)
        self.attempt_history = attempt_history or []


class CircuitTrippedError(RpcError):
    def __init__(self, endpoint: str, **kwargs):
        super().__init__(f"Circuit breaker tripped for endpoint: {endpoint}",
                         endpoint=endpoint, category=ErrorCategory.TRANSIENT, **kwargs)


class ChainIdMismatchError(DeterministicRpcError):
    def __init__(self, endpoint: str, expected: int, actual: int):
        super().__init__(f"Chain ID mismatch for endpoint {endpoint}: expected {expected}, got {actual}",
                         endpoint=endpoint, data={'expected': expected, 'actual': actual})


def classify_error(err: Exception, status_code: Optional[int] = None) -> Dict[str, Any]:
    if not err:
        return {'is_transient': False, 'category': ErrorCategory.DETERMINISTIC, 'reason': 'unknown'}

    if isinstance(err, DeterministicRpcError):
        return {'is_transient': False, 'category': ErrorCategory.DETERMINISTIC, 'reason': str(err)}
    if isinstance(err, TransientRpcError):
        return {'is_transient': True, 'category': ErrorCategory.TRANSIENT, 'reason': str(err)}

    status = status_code or getattr(err, 'status_code', None)
    err_msg = str(err).lower()

    if status == 429:
        return {'is_transient': True, 'category': ErrorCategory.TRANSIENT, 'reason': 'HTTP 429 Rate Limit'}
    if status and 500 <= status <= 599:
        return {'is_transient': True, 'category': ErrorCategory.TRANSIENT, 'reason': f'HTTP {status} Server Error'}

    transient_patterns = ['connection refused', 'timeout', 'timed out', 'econnrefused', 'etimedout',
                          'rate limit', 'too many requests', 'network error']
    for pat in transient_patterns:
        if pat in err_msg:
            return {'is_transient': True, 'category': ErrorCategory.TRANSIENT, 'reason': f'Transient: {pat}'}

    deterministic_codes = {-32700, -32600, -32601, -32602, -32603, -32000, -32003}
    err_code = getattr(err, 'code', None)
    if err_code in deterministic_codes:
        return {'is_transient': False, 'category': ErrorCategory.DETERMINISTIC, 'reason': f'Deterministic code: {err_code}'}

    deterministic_patterns = ['execution reverted', 'nonce too low', 'insufficient funds',
                              'invalid signature', 'invalid param', 'method not found']
    for pat in deterministic_patterns:
        if pat in err_msg:
            return {'is_transient': False, 'category': ErrorCategory.DETERMINISTIC, 'reason': f'Deterministic: {pat}'}

    return {'is_transient': False, 'category': ErrorCategory.DETERMINISTIC, 'reason': 'Unclassified deterministic'}


class CircuitBreaker:
    def __init__(self, endpoint: str, failure_threshold: int = 3, degraded_threshold: int = 1,
                 recovery_success_threshold: int = 2, cooldown_period_ms: int = 10000,
                 on_state_change: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.endpoint = endpoint
        self.failure_threshold = failure_threshold
        self.degraded_threshold = degraded_threshold
        self.recovery_success_threshold = recovery_success_threshold
        self.cooldown_period_ms = cooldown_period_ms
        self.on_state_change = on_state_change

        self.state = CircuitState.HEALTHY
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.total_successes = 0
        self.total_failures = 0
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self.last_state_change_time = time.time() * 1000

    def can_execute(self, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.time() * 1000
        if self.state in (CircuitState.HEALTHY, CircuitState.DEGRADED):
            return True
        if self.state == CircuitState.TRIPPED:
            elapsed = now - (self.last_failure_time or 0)
            if elapsed >= self.cooldown_period_ms:
                self.transition_to(CircuitState.RECOVERY, 'Cooldown elapsed, entering recovery probe mode', now)
                return True
            return False
        return self.state == CircuitState.RECOVERY

    def record_success(self, now: Optional[float] = None) -> None:
        if now is None:
            now = time.time() * 1000
        self.last_success_time = now
        self.total_successes += 1
        self.consecutive_failures = 0

        if self.state == CircuitState.RECOVERY:
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.recovery_success_threshold:
                self.transition_to(CircuitState.HEALTHY,
                                   f'Recovered after {self.consecutive_successes} consecutive successes', now)
        elif self.state == CircuitState.DEGRADED:
            self.consecutive_successes += 1
            self.transition_to(CircuitState.HEALTHY, 'Endpoint recovered from degraded state', now)
        else:
            self.consecutive_successes += 1

    def record_failure(self, err: Exception, now: Optional[float] = None) -> None:
        if now is None:
            now = time.time() * 1000
        self.last_failure_time = now
        self.total_failures += 1
        self.consecutive_successes = 0
        self.consecutive_failures += 1

        if self.state == CircuitState.RECOVERY:
            self.transition_to(CircuitState.TRIPPED, f'Probe failed during recovery: {str(err)}', now)
        elif self.consecutive_failures >= self.failure_threshold:
            self.transition_to(CircuitState.TRIPPED, 'Failure threshold reached', now)
        elif self.consecutive_failures >= self.degraded_threshold and self.state == CircuitState.HEALTHY:
            self.transition_to(CircuitState.DEGRADED, 'Degraded threshold reached', now)

    def transition_to(self, new_state: CircuitState, reason: str = '', now: Optional[float] = None) -> None:
        if self.state == new_state:
            return
        if now is None:
            now = time.time() * 1000
        old_state = self.state
        self.state = new_state
        self.last_state_change_time = now

        if new_state == CircuitState.HEALTHY:
            self.consecutive_failures = 0

        if self.on_state_change:
            self.on_state_change({
                'endpoint': self.endpoint,
                'previous_state': old_state.value,
                'new_state': new_state.value,
                'reason': reason,
                'consecutive_failures': self.consecutive_failures,
                'timestamp': now
            })

    def reset(self) -> None:
        self.state = CircuitState.HEALTHY
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.last_state_change_time = time.time() * 1000


class EndpointNode:
    def __init__(self, url: str, weight: int = 100, name: Optional[str] = None,
                 circuit_breaker_options: Optional[Dict[str, Any]] = None,
                 on_state_change: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.url = url
        self.weight = weight
        self.name = name or url
        opts = circuit_breaker_options or {}
        self.circuit_breaker = CircuitBreaker(url, on_state_change=on_state_change, **opts)
        self.metrics = {
            'total_requests': 0,
            'success_count': 0,
            'failure_count': 0,
            'failover_count': 0,
            'total_latency_ms': 0,
            'avg_latency_ms': 0
        }

    def record_latency(self, latency_ms: float) -> None:
        self.metrics['total_latency_ms'] += latency_ms
        self.metrics['avg_latency_ms'] = round(self.metrics['total_latency_ms'] / (self.metrics['total_requests'] or 1))


class ResilientRpcClient:
    def __init__(self, endpoints: List[Union[str, Dict[str, Any]]],
                 fetcher: Optional[Callable[..., Any]] = None,
                 timeout_ms: int = 8000, max_retries_per_endpoint: int = 2,
                 base_backoff_ms: int = 100, max_backoff_ms: int = 3000,
                 backoff_multiplier: float = 2.0, jitter: Union[bool, float] = True,
                 failure_threshold: int = 3, degraded_threshold: int = 1,
                 recovery_success_threshold: int = 2, cooldown_period_ms: int = 10000,
                 preserve_idempotency: bool = True, expected_chain_id: Optional[int] = None):
        if not endpoints:
            raise ValueError('ResilientRpcClient requires a non-empty array of endpoint URLs')

        self.fetcher = fetcher
        self.timeout_ms = timeout_ms
        self.max_retries_per_endpoint = max_retries_per_endpoint
        self.base_backoff_ms = base_backoff_ms
        self.max_backoff_ms = max_backoff_ms
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.preserve_idempotency = preserve_idempotency
        self.expected_chain_id = expected_chain_id

        self.event_listeners: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.global_metrics = {
            'total_dispatched_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_failovers': 0,
            'circuit_trips': 0
        }

        cb_opts = {
            'failure_threshold': failure_threshold,
            'degraded_threshold': degraded_threshold,
            'recovery_success_threshold': recovery_success_threshold,
            'cooldown_period_ms': cooldown_period_ms
        }

        def on_cb_state_change(payload: Dict[str, Any]):
            if payload['new_state'] == CircuitState.TRIPPED.value:
                self.global_metrics['circuit_trips'] += 1
                self._emit(FailoverEventType.CIRCUIT_TRIP.value, payload)
            elif payload['new_state'] == CircuitState.HEALTHY.value and payload['previous_state'] == CircuitState.RECOVERY.value:
                self._emit(FailoverEventType.CIRCUIT_RECOVERED.value, payload)
            self._emit(FailoverEventType.STATE_CHANGE.value, payload)

        self.endpoints: List[EndpointNode] = []
        for ep in endpoints:
            if isinstance(ep, str):
                self.endpoints.append(EndpointNode(ep, circuit_breaker_options=cb_opts, on_state_change=on_cb_state_change))
            else:
                self.endpoints.append(EndpointNode(ep['url'], weight=ep.get('weight', 100),
                                                   name=ep.get('name'), circuit_breaker_options=cb_opts,
                                                   on_state_change=on_cb_state_change))

    def on(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.event_listeners.setdefault(event_type, []).append(callback)

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        for cb in self.event_listeners.get(event_type, []):
            try:
                cb(payload)
            except Exception:
                pass

    def resolve_idempotency_key(self, request: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> str:
        options = options or {}
        if options.get('idempotency_key'):
            return str(options['idempotency_key'])
        headers = options.get('headers') or {}
        if 'x-idempotency-key' in headers:
            return str(headers['x-idempotency-key'])

        payload_str = json.dumps({'method': request.get('method'), 'params': request.get('params'), 'id': request.get('id')}, sort_keys=True)
        h = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()[:32]
        return f'idem-rpc-{h}'

    def compute_backoff(self, attempt: int) -> float:
        raw = self.base_backoff_ms * (self.backoff_multiplier ** max(0, attempt))
        bounded = min(raw, self.max_backoff_ms)
        jitter_val = 0.0
        if self.jitter is True:
            jitter_val = random.uniform(0, bounded * 0.5)
        elif isinstance(self.jitter, (int, float)):
            jitter_val = float(self.jitter)
        return bounded + jitter_val

    def dispatch(self, request: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Any:
        options = options or {}
        self.global_metrics['total_dispatched_requests'] += 1

        rpc_payload = {
            'jsonrpc': request.get('jsonrpc', '2.0'),
            'id': request.get('id', int(time.time() * 1000)),
            'method': request.get('method'),
            'params': request.get('params', [])
        }

        if not rpc_payload['method'] or not isinstance(rpc_payload['method'], str):
            raise DeterministicRpcError('JSON-RPC method must be a non-empty string', code=-32600)

        idempotency_key = self.resolve_idempotency_key(rpc_payload, options)
        attempt_history: List[Dict[str, Any]] = []

        now = time.time() * 1000
        eligible = [ep for ep in self.endpoints if ep.circuit_breaker.can_execute(now)]
        if not eligible:
            eligible = list(self.endpoints)

        last_error = None
        failover_counter = 0

        for ep_idx, ep_node in enumerate(eligible):
            if not ep_node.circuit_breaker.can_execute():
                continue

            for attempt in range(self.max_retries_per_endpoint + 1):
                ep_node.metrics['total_requests'] += 1
                req_start = time.time() * 1000

                try:
                    headers = dict(options.get('headers') or {})
                    headers['Content-Type'] = 'application/json'
                    headers['Accept'] = 'application/json'
                    if self.preserve_idempotency:
                        headers['x-idempotency-key'] = idempotency_key

                    if not self.fetcher:
                        raise RuntimeError("No fetcher implementation configured")

                    response = self.fetcher(ep_node.url, method='POST', headers=headers,
                                            body=json.dumps(rpc_payload), timeout=self.timeout_ms / 1000.0)

                    latency = time.time() * 1000 - req_start
                    ep_node.record_latency(latency)

                    status = getattr(response, 'status', getattr(response, 'status_code', 200))
                    if status != 200:
                        err = Exception(f"HTTP {status} Error")
                        setattr(err, 'status_code', status)
                        classification = classify_error(err, status_code=status)
                        if not classification['is_transient']:
                            ep_node.circuit_breaker.record_failure(err)
                            raise DeterministicRpcError(str(err), status_code=status, endpoint=ep_node.url, idempotency_key=idempotency_key)
                        raise TransientRpcError(str(err), status_code=status, endpoint=ep_node.url, idempotency_key=idempotency_key)

                    data = response.json() if callable(getattr(response, 'json', None)) else getattr(response, 'data', {})

                    if self.expected_chain_id and rpc_payload['method'] == 'eth_chainId':
                        raw_chain = data.get('result')
                        act_chain = int(raw_chain, 16) if isinstance(raw_chain, str) and raw_chain.startswith('0x') else int(raw_chain)
                        if act_chain != self.expected_chain_id:
                            chain_err = ChainIdMismatchError(ep_node.url, self.expected_chain_id, act_chain)
                            ep_node.circuit_breaker.record_failure(chain_err)
                            raise chain_err

                    if 'error' in data and data['error']:
                        err_obj = data['error']
                        err = Exception(err_obj.get('message', 'RPC error'))
                        setattr(err, 'code', err_obj.get('code'))
                        setattr(err, 'data', err_obj.get('data'))
                        classification = classify_error(err)
                        if not classification['is_transient']:
                            ep_node.circuit_breaker.record_success()
                            ep_node.metrics['success_count'] += 1
                            self.global_metrics['successful_requests'] += 1
                            raise DeterministicRpcError(err_obj.get('message'), code=err_obj.get('code'),
                                                         data=err_obj.get('data'), endpoint=ep_node.url,
                                                         idempotency_key=idempotency_key)
                        else:
                            raise TransientRpcError(err_obj.get('message'), code=err_obj.get('code'),
                                                    data=err_obj.get('data'), endpoint=ep_node.url,
                                                    idempotency_key=idempotency_key)

                    ep_node.circuit_breaker.record_success()
                    ep_node.metrics['success_count'] += 1
                    self.global_metrics['successful_requests'] += 1

                    self._emit(FailoverEventType.REQUEST_SUCCESS.value, {
                        'endpoint': ep_node.url,
                        'method': rpc_payload['method'],
                        'idempotency_key': idempotency_key,
                        'latency_ms': latency,
                        'attempts': attempt + 1,
                        'failovers': failover_counter
                    })

                    return data.get('result')

                except Exception as err:
                    last_error = err
                    attempt_history.append({
                        'endpoint': ep_node.url,
                        'attempt': attempt,
                        'error': str(err),
                        'status_code': getattr(err, 'status_code', None),
                        'code': getattr(err, 'code', None),
                        'timestamp': time.time() * 1000
                    })

                    if isinstance(err, DeterministicRpcError):
                        self.global_metrics['failed_requests'] += 1
                        ep_node.metrics['failure_count'] += 1
                        raise err

                    classification = classify_error(err)
                    if not classification['is_transient']:
                        self.global_metrics['failed_requests'] += 1
                        ep_node.metrics['failure_count'] += 1
                        ep_node.circuit_breaker.record_failure(err)
                        raise DeterministicRpcError(str(err), code=getattr(err, 'code', None),
                                                     endpoint=ep_node.url, idempotency_key=idempotency_key)

                    ep_node.circuit_breaker.record_failure(err)
                    ep_node.metrics['failure_count'] += 1

                    if attempt < self.max_retries_per_endpoint:
                        backoff = self.compute_backoff(attempt)
                        self._emit(FailoverEventType.REQUEST_RETRY.value, {
                            'endpoint': ep_node.url,
                            'attempt': attempt + 1,
                            'max_retries': self.max_retries_per_endpoint,
                            'backoff_ms': backoff,
                            'reason': str(err),
                            'idempotency_key': idempotency_key
                        })
                        time.sleep(backoff / 1000.0)
                        continue
                    break

            next_idx = ep_idx + 1
            if next_idx < len(eligible):
                failover_counter += 1
                self.global_metrics['total_failovers'] += 1
                ep_node.metrics['failover_count'] += 1
                next_ep = eligible[next_idx]

                self._emit(FailoverEventType.FAILOVER.value, {
                    'timestamp': time.time() * 1000,
                    'from_endpoint': ep_node.url,
                    'to_endpoint': next_ep.url,
                    'reason': str(last_error) if last_error else 'Endpoint retries exhausted',
                    'attempt': failover_counter,
                    'idempotency_key': idempotency_key,
                    'payload_id': rpc_payload['id']
                })
                time.sleep(min(self.base_backoff_ms, 100) / 1000.0)

        self.global_metrics['failed_requests'] += 1
        raise EndpointExhaustionError(
            f"All {len(eligible)} RPC endpoints exhausted after sequential failover. Last error: {str(last_error)}",
            attempt_history=attempt_history,
            idempotency_key=idempotency_key,
            endpoint=', '.join(e.url for e in eligible)
        )

    def get_metrics(self) -> Dict[str, Any]:
        return {
            'global': dict(self.global_metrics),
            'endpoints': [{
                'url': ep.url,
                'state': ep.circuit_breaker.state.value,
                'consecutive_failures': ep.circuit_breaker.consecutive_failures,
                'consecutive_successes': ep.circuit_breaker.consecutive_successes,
                'metrics': dict(ep.metrics)
            } for ep in self.endpoints]
        }

    def get_endpoint_states(self) -> Dict[str, str]:
        return {ep.url: ep.circuit_breaker.state.value for ep in self.endpoints}

    def reset_all(self) -> None:
        for ep in self.endpoints:
            ep.circuit_breaker.reset()
            ep.metrics = {
                'total_requests': 0, 'success_count': 0, 'failure_count': 0,
                'failover_count': 0, 'total_latency_ms': 0, 'avg_latency_ms': 0
            }
        self.global_metrics = {
            'total_dispatched_requests': 0, 'successful_requests': 0,
            'failed_requests': 0, 'total_failovers': 0, 'circuit_trips': 0
        }
