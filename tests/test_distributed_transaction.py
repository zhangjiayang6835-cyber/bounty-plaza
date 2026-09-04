"""Unit and concurrency test suite for Distributed Transaction Race Condition Defense.
Resolves Issue #266: Race Condition in Distributed Transaction -> Double Spend ($180 USD).
Verifies:
1. Double-spend prevention under concurrent multithreaded debit requests.
2. Balance non-negativity invariant under heavy racing.
3. Optimistic Concurrency Control (OCC) version conflict handling.
4. Transaction rollback on insufficient balance.
"""

import concurrent.futures
import pytest
from scripts.distributed_transaction import (
    DistributedAccountStore,
    DoubleSpendError,
    InsufficientFundsError,
    OptimisticLockError,
    AccountNotFoundError,
)


@pytest.fixture
def store(tmp_path):
    db_file = str(tmp_path / "test_ledger.db")
    return DistributedAccountStore(db_path=db_file)


def test_create_and_get_account(store):
    acc = store.create_account("acc_alice", initial_balance=100.0)
    assert acc["account_id"] == "acc_alice"
    assert acc["balance"] == 100.0
    assert acc["version"] == 1

    fetched = store.get_account("acc_alice")
    assert fetched["balance"] == 100.0
    assert fetched["version"] == 1


def test_deposit(store):
    store.create_account("acc_bob", initial_balance=50.0)
    res = store.deposit("acc_bob", 25.5)
    assert res["new_balance"] == 75.5
    assert res["version"] == 2

    acc = store.get_account("acc_bob")
    assert acc["balance"] == 75.5


def test_pessimistic_debit_success(store):
    store.create_account("acc_charlie", initial_balance=200.0)
    res = store.debit_pessimistic("acc_charlie", 50.0)
    assert res["status"] == "SUCCESS"
    assert res["new_balance"] == 150.0
    assert res["version"] == 2

    acc = store.get_account("acc_charlie")
    assert acc["balance"] == 150.0


def test_pessimistic_debit_insufficient_funds(store):
    store.create_account("acc_david", initial_balance=30.0)
    with pytest.raises(InsufficientFundsError, match="Insufficient funds"):
        store.debit_pessimistic("acc_david", 50.0)

    acc = store.get_account("acc_david")
    assert acc["balance"] == 30.0  # Balance remains unchanged


def test_concurrent_double_spend_neutralized(store):
    """Critical Test: Concurrency race condition double spend attack.
    Account has $100.
    10 concurrent threads each attempt to debit $20 simultaneously (total $200 attempted).
    Exactly 5 debits must succeed, exactly 5 must fail with InsufficientFundsError.
    Final balance must be exactly $0.00 and NEVER negative.
    """
    account_id = "acc_victim_wallet"
    store.create_account(account_id, initial_balance=100.0)

    successes = 0
    failures = 0
    num_threads = 10
    debit_amount = 20.0

    def attempt_debit(idx):
        try:
            store.debit_pessimistic(account_id, debit_amount, tx_id=f"tx_race_{idx}")
            return True
        except InsufficientFundsError:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(attempt_debit, i) for i in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    successes = sum(1 for r in results if r is True)
    failures = sum(1 for r in results if r is False)

    assert successes == 5, f"Expected 5 successful debits, got {successes}"
    assert failures == 5, f"Expected 5 failed debits, got {failures}"

    final_acc = store.get_account(account_id)
    assert final_acc["balance"] == 0.0, f"Final balance should be 0.0, got {final_acc['balance']}"
    assert final_acc["balance"] >= 0.0, "Balance must never be negative (double spend prevented)"


def test_optimistic_concurrency_control(store):
    account_id = "acc_occ_user"
    store.create_account(account_id, initial_balance=100.0)

    # First OCC debit succeeds with initial version 1
    res1 = store.debit_optimistic(account_id, 30.0, expected_version=1)
    assert res1["new_balance"] == 70.0
    assert res1["version"] == 2

    # Attempting second OCC debit with stale version 1 must raise OptimisticLockError
    with pytest.raises(OptimisticLockError, match="Version mismatch"):
        store.debit_optimistic(account_id, 30.0, expected_version=1)

    # Debiting with updated version 2 succeeds
    res2 = store.debit_optimistic(account_id, 20.0, expected_version=2)
    assert res2["new_balance"] == 50.0
    assert res2["version"] == 3


def test_invalid_amounts_and_nonexistent_accounts(store):
    with pytest.raises(ValueError, match="strictly positive"):
        store.create_account("acc_inv", 10.0)
        store.debit_pessimistic("acc_inv", -10.0)

    with pytest.raises(AccountNotFoundError, match="not found"):
        store.debit_pessimistic("acc_nonexistent", 10.0)
