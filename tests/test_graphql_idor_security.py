"""Unit and security test suite for GraphQL Nested Query IDOR Defense.
Resolves Issue #278: IDOR in GraphQL Nested Query -> Mass Data Leak ($150 USD).
"""

import pytest
from scripts.graphql_idor_security import (
    AuthContext,
    SecureGraphQLService,
    GraphQLForbiddenError,
    GraphQLUnauthorizedError,
    GraphQLRateLimitError,
    RateLimiter,
)


@pytest.fixture
def service():
    return SecureGraphQLService()


def test_unauthenticated_query_rejected(service):
    anon_context = AuthContext(user_id=None, is_authenticated=False)
    with pytest.raises(GraphQLUnauthorizedError, match="Authentication required"):
        service.execute_user_orders_query(anon_context, "usr_101")


def test_authorized_user_can_query_own_nested_data(service):
    alice_ctx = AuthContext(user_id="usr_101", is_authenticated=True)
    res = service.execute_user_orders_query(alice_ctx, "usr_101")

    assert res["user"]["id"] == "usr_101"
    assert res["user"]["username"] == "alice"
    assert len(res["user"]["orders"]) == 1
    order = res["user"]["orders"][0]
    assert order["order_id"] == "ord_a1"
    assert order["total"] == 125.50
    assert order["items"][0]["product"] == "Hardware Key"


def test_idor_horizontal_privilege_escalation_blocked(service):
    """Alice attempts to query Bob's user profile and nested orders."""
    alice_ctx = AuthContext(user_id="usr_101", is_authenticated=True)
    with pytest.raises(GraphQLForbiddenError, match="IDOR violation"):
        service.execute_user_orders_query(alice_ctx, "usr_102")


def test_idor_nested_orders_direct_resolver_blocked(service):
    """Alice tries to call the orders resolver directly for Bob's ID."""
    alice_ctx = AuthContext(user_id="usr_101", is_authenticated=True)
    with pytest.raises(GraphQLForbiddenError, match="cannot access nested orders"):
        service.resolve_orders(alice_ctx, "usr_102")


def test_idor_nested_order_items_resolver_blocked(service):
    """Alice tries to inspect items belonging to Bob's order."""
    alice_ctx = AuthContext(user_id="usr_101", is_authenticated=True)
    bobs_order = {"order_id": "ord_b1", "user_id": "usr_102", "items": [{"item_id": "i1"}]}
    with pytest.raises(GraphQLForbiddenError, match="cannot inspect items of order belonging to"):
        service.resolve_order_items(alice_ctx, bobs_order)


def test_admin_privileged_access_allowed(service):
    admin_ctx = AuthContext(user_id="admin_01", roles={"ADMIN"}, is_authenticated=True)
    # Admin can view Bob's nested orders
    res = service.execute_user_orders_query(admin_ctx, "usr_102")
    assert res["user"]["id"] == "usr_102"
    assert len(res["user"]["orders"]) == 1
    assert res["user"]["orders"][0]["total"] == 890.00


def test_rate_limiter_blocks_enumeration_scrapes():
    strict_limiter = RateLimiter(max_requests=5, window_seconds=10.0)
    service = SecureGraphQLService(rate_limiter=strict_limiter)
    ctx = AuthContext(user_id="usr_101", is_authenticated=True)

    # 5 successful requests
    for _ in range(5):
        service.execute_user_orders_query(ctx, "usr_101")

    # 6th request triggers rate limit error
    with pytest.raises(GraphQLRateLimitError, match="Rate limit exceeded"):
        service.execute_user_orders_query(ctx, "usr_101")
