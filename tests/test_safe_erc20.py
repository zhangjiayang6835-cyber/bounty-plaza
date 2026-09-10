#!/usr/bin/env python3
"""
Unit tests for the SafeERC20 wrapper (scripts/safe_erc20.py).

Verifies that asset transfer hooks using SafeERC20 work with standard ERC-20
tokens *and* non-standard tokens such as USDT that do not return a boolean
value, and that failed transfers never go unnoticed.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from safe_erc20 import (  # noqa: E402
    SafeERC20,
    SafeERC20Error,
    batch_safe_transfer,
    force_approve,
    safe_approve,
    safe_transfer,
    safe_transfer_from,
    verify_transfer_success,
)

VAULT = "vault"


class StandardToken:
    """Standard ERC-20: transfer()/transferFrom()/approve() return a boolean."""

    def __init__(self, name="StandardToken", total=1_000_000):
        self.name = name
        self.balances = {VAULT: total}
        self.allowances = {}  # {owner: {spender: allowance}}
        self.ops = []

    def _sufficient(self, sender, value):
        return self.balances.get(sender, 0) >= value

    def transfer(self, to, value):
        if not self._sufficient(VAULT, value):
            return False
        self.balances[VAULT] -= value
        self.balances[to] = self.balances.get(to, 0) + value
        self.ops.append(("transfer", to, value))
        return True

    def transfer_from(self, sender, to, value):
        allowed = self.allowances.get(sender, {}).get("harvester", 0)
        if allowed < value or not self._sufficient(sender, value):
            return False
        self.allowances[sender]["harvester"] = allowed - value
        self.balances[sender] -= value
        self.balances[to] = self.balances.get(to, 0) + value
        self.ops.append(("transferFrom", sender, to, value))
        return True

    def approve(self, spender, value):
        self.allowances.setdefault(VAULT, {})[spender] = value
        self.ops.append(("approve", spender, value))
        return True


class NonStandardToken(StandardToken):
    """
    USDT-like token: transfer()/approve() return no value at all and the call
    reverts (raises) when the transfer cannot be fulfilled.
    """

    def __init__(self, name="Tether USD", total=1_000_000):
        super().__init__(name=name, total=total)

    def transfer(self, to, value):
        if not self._sufficient(VAULT, value):
            raise SafeERC20Error("%s: insufficient balance" % self.name)
        super().transfer(to, value)
        return None

    def transfer_from(self, sender, to, value):
        allowed = self.allowances.get(sender, {}).get("harvester", 0)
        if allowed < value or not self._sufficient(sender, value):
            raise SafeERC20Error("%s: insufficient allowance" % self.name)
        super().transfer_from(sender, to, value)
        return None

    def approve(self, spender, value):
        super().approve(spender, value)
        return None


class ExplodingToken:
    """Token whose low-level call always fails."""

    def transfer(self, to, value):
        raise SafeERC20Error("revert: execution reverted")


# ── safeTransfer ──

def test_safe_transfer_standard_token_success():
    token = StandardToken()
    safe_transfer(token, "alice", 500)
    assert token.balances[VAULT] == 1_000_000 - 500
    assert token.balances["alice"] == 500


def test_safe_transfer_nonstandard_token_success():
    usdt = NonStandardToken()
    safe_transfer(usdt, "alice", 500)
    assert usdt.balances[VAULT] == 1_000_000 - 500
    assert usdt.balances["alice"] == 500


def test_safe_transfer_reverts_when_token_returns_false():
    token = StandardToken()
    with pytest.raises(SafeERC20Error):
        safe_transfer(token, "alice", 1_000_001)
    assert token.balances[VAULT] == 1_000_000
    assert "alice" not in token.balances


def test_safe_transfer_surfaces_low_level_failure():
    with pytest.raises(SafeERC20Error):
        safe_transfer(ExplodingToken(), "alice", 1)


def test_safe_transfer_wrapper_rejects_false_return():
    token = StandardToken()
    wrapper = SafeERC20(token)
    with pytest.raises(SafeERC20Error):
        wrapper.safe_transfer("alice", 1_000_001)


# ── safeTransferFrom ──

def test_safe_transfer_from_nonstandard_token_success():
    usdt = NonStandardToken()
    safe_approve(usdt, "harvester", 500)
    safe_transfer_from(usdt, VAULT, "bob", 500)
    assert usdt.balances["bob"] == 500
    assert usdt.allowances[VAULT]["harvester"] == 0


def test_safe_transfer_from_rejects_false_return():
    token = StandardToken()
    with pytest.raises(SafeERC20Error):
        safe_transfer_from(token, VAULT, "bob", 100)  # no allowance set


def test_safe_transfer_from_rejects_insufficient_allowance_nonstandard():
    usdt = NonStandardToken()
    safe_approve(usdt, "harvester", 10)
    with pytest.raises(SafeERC20Error):
        safe_transfer_from(usdt, VAULT, "bob", 100)


# ── safeApprove / forceApprove ──

def test_safe_approve_nonstandard_token_success():
    usdt = NonStandardToken()
    safe_approve(usdt, "harvester", 1000)
    assert usdt.allowances[VAULT]["harvester"] == 1000


def test_force_approve_resets_allowance_to_zero_first():
    usdt = NonStandardToken()
    safe_approve(usdt, "harvester", 1000)
    force_approve(usdt, "harvester", 500)
    approvals = [op for op in usdt.ops if op[0] == "approve"]
    assert approvals[-2][2] == 0  # zeroed before re-approving
    assert usdt.allowances[VAULT]["harvester"] == 500


# ── batch yield harvesting (integration) ──

def test_batch_harvest_with_mixed_tokens():
    usdt = NonStandardToken()
    weth = StandardToken(name="WETH")
    alice = "alice"
    batch_safe_transfer([(usdt, alice, 100), (weth, alice, 200)])
    assert usdt.balances[alice] == 100
    assert weth.balances[alice] == 200


def test_batch_harvest_reverts_atomically_on_failure():
    usdt = NonStandardToken()
    weth = StandardToken(name="WETH")
    alice = "alice"
    with pytest.raises(SafeERC20Error):
        batch_safe_transfer([(usdt, alice, 100), (weth, alice, 999_999_999)])
    assert usdt.balances[alice] == 100
    assert alice not in weth.balances  # failed transfer must not have run


def test_verify_transfer_success_accepts_empty_return_data():
    verify_transfer_success(None)        # USDT-style: no return value
    verify_transfer_success(True)
    with pytest.raises(SafeERC20Error):
        verify_transfer_success(False)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))