"""GraphQL Nested Query IDOR Defense & DataLoader Ownership Resolver Engine.
Resolves Issue #278: IDOR in GraphQL Nested Query -> Mass Data Leak ($150 USD).

Implements:
1. Contextual authentication & authorization enforcement (AuthContext).
2. Strict data ownership checks at every resolver / DataLoader boundary.
3. Prevention of horizontal and vertical privilege escalation in nested object graphs.
4. Token bucket query rate limiting per identity to prevent automated user ID enumeration.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


class GraphQLError(Exception):
    """Base exception for GraphQL security errors."""
    pass


class GraphQLUnauthorizedError(GraphQLError):
    """Raised when query execution requires an authenticated session."""
    pass


class GraphQLForbiddenError(GraphQLError):
    """Raised when an authenticated user attempts unauthorized access to another user's data (IDOR)."""
    pass


class GraphQLRateLimitError(GraphQLError):
    """Raised when client exceeds allowed query request rate."""
    pass


@dataclass
class AuthContext:
    """Represents the verified security context passed into GraphQL execution."""
    user_id: Optional[str]
    roles: Set[str] = field(default_factory=set)
    is_authenticated: bool = False
    client_ip: str = "127.0.0.1"

    @property
    def is_admin(self) -> bool:
        return "ADMIN" in self.roles


class RateLimiter:
    """Sliding-window token bucket rate limiter to stop brute-force ID enumeration."""

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # client_key -> list of timestamps
        self._history: Dict[str, List[float]] = {}

    def check_rate_limit(self, client_key: str) -> None:
        now = time.time()
        timestamps = self._history.setdefault(client_key, [])
        # Prune expired timestamps
        self._history[client_key] = [t for t in timestamps if now - t < self.window_seconds]
        if len(self._history[client_key]) >= self.max_requests:
            raise GraphQLRateLimitError(
                f"Rate limit exceeded: max {self.max_requests} queries per {self.window_seconds}s"
            )
        self._history[client_key].append(now)


class SecureGraphQLService:
    """Secure GraphQL schema resolver engine with multi-tier ownership validation."""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or RateLimiter(max_requests=100, window_seconds=60.0)

        # In-memory mock data store
        self._users: Dict[str, Dict[str, Any]] = {
            "usr_101": {"id": "usr_101", "username": "alice", "email": "alice@corp.internal"},
            "usr_102": {"id": "usr_102", "username": "bob", "email": "bob@corp.internal"},
            "usr_999": {"id": "usr_999", "username": "charlie", "email": "charlie@corp.internal"},
        }
        self._orders: Dict[str, List[Dict[str, Any]]] = {
            "usr_101": [
                {
                    "order_id": "ord_a1",
                    "user_id": "usr_101",
                    "total": 125.50,
                    "items": [
                        {"item_id": "item_1", "product": "Hardware Key", "price": 125.50}
                    ]
                }
            ],
            "usr_102": [
                {
                    "order_id": "ord_b1",
                    "user_id": "usr_102",
                    "total": 890.00,
                    "items": [
                        {"item_id": "item_2", "product": "Encrypted Drive", "price": 890.00}
                    ]
                }
            ],
            "usr_999": [
                {
                    "order_id": "ord_c1",
                    "user_id": "usr_999",
                    "total": 45.00,
                    "items": [
                        {"item_id": "item_3", "product": "RFID Shield", "price": 45.00}
                    ]
                }
            ]
        }

    # =========================================================================
    # Resolvers with DataLoader-level Ownership Enforcement
    # =========================================================================

    def resolve_user(self, context: AuthContext, target_user_id: str) -> Dict[str, Any]:
        """Resolves root `user(id: $id)` query.
        Guarantees that context.user_id matches target_user_id unless caller is ADMIN.
        """
        self._enforce_auth(context)

        # IDOR Defense: strict ownership check
        if context.user_id != target_user_id and not context.is_admin:
            raise GraphQLForbiddenError(
                f"IDOR violation: User '{context.user_id}' is forbidden from querying user profile '{target_user_id}'."
            )

        user = self._users.get(target_user_id)
        if not user:
            return {}

        return dict(user)

    def resolve_orders(self, context: AuthContext, parent_user_id: str) -> List[Dict[str, Any]]:
        """Resolves nested `user { orders }` field.
        Verifies ownership at DataLoader/resolver level, preventing nested traversal leak.
        """
        self._enforce_auth(context)

        # IDOR Defense: verify parent ownership against authenticated context
        if context.user_id != parent_user_id and not context.is_admin:
            raise GraphQLForbiddenError(
                f"IDOR violation: User '{context.user_id}' cannot access nested orders for '{parent_user_id}'."
            )

        orders = self._orders.get(parent_user_id, [])
        return [dict(ord) for ord in orders]

    def resolve_order_items(self, context: AuthContext, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Resolves nested `user { orders { items } }` field.
        Validates order owner matches auth context.
        """
        self._enforce_auth(context)

        order_owner_id = order.get("user_id")
        if order_owner_id != context.user_id and not context.is_admin:
            raise GraphQLForbiddenError(
                f"IDOR violation: User '{context.user_id}' cannot inspect items of order belonging to '{order_owner_id}'."
            )

        return list(order.get("items", []))

    def execute_user_orders_query(
        self,
        context: AuthContext,
        target_user_id: str,
        include_items: bool = True
    ) -> Dict[str, Any]:
        """Simulates full nested query: user(id: $id) { orders { items { price } } }."""
        self._enforce_auth_and_rate_limit(context)
        user = self.resolve_user(context, target_user_id)
        if not user:
            return {"user": None}

        orders = self.resolve_orders(context, target_user_id)
        if include_items:
            for ord in orders:
                ord["items"] = self.resolve_order_items(context, ord)

        user["orders"] = orders
        return {"user": user}

    def _enforce_auth(self, context: AuthContext) -> None:
        """Validates session authentication."""
        if not context or not context.is_authenticated or not context.user_id:
            raise GraphQLUnauthorizedError("Authentication required to execute protected GraphQL query.")

    def _enforce_auth_and_rate_limit(self, context: AuthContext) -> None:
        """Validates session authentication and tracks query rate limit."""
        self._enforce_auth(context)
        client_key = f"{context.user_id}:{context.client_ip}"
        self.rate_limiter.check_rate_limit(client_key)
