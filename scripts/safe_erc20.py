#!/usr/bin/env python3
"""
safe_erc20.py — SafeERC20 wrapper for non-standard ERC-20 tokens.

A faithful Python port of OpenZeppelin's SafeERC20 (v4) helper, used to guard
every ERC-20 ``transfer`` / ``transferFrom`` / ``approve`` call.

Problem being fixed
-------------------
Standard ERC-20 returns a ``bool`` from ``transfer()``. Non-standard tokens
such as USDT return *no value at all*. Code that calls ``transfer()`` directly
and either ignores the return value or fails to handle missing return data can:

* revert the whole transaction during batch yield harvesting, or
* silently continue after a token refused the transfer.

Solution
--------
Wrap every token transfer in ``SafeERC20``. The wrapper:

* treats empty return data (USDT-style tokens) as success;
* honours a returned ``bool`` — ``false`` raises ``SafeERC20Error``;
* surfaces low-level call failures instead of hiding them.

Usage::

    from safe_erc20 import SafeERC20, safe_transfer, SafeERC20Error

    SafeERC20(usdt).safe_transfer(recipient, amount)  # raises on failure
    safe_transfer(usdt, recipient, amount)            # module-level shortcut
"""


class SafeERC20Error(Exception):
    """Raised when an ERC-20 operation fails or its return value is not honoured."""


def _decode_result(result, context):
    """
    Interpret the raw return value of an ERC-20 call.

    * ``None`` / empty data -> non-standard token (USDT-like): success.
    * truthy -> success.
    * falsy (``False`` / ``0``) -> the token refused the operation: failure.
    """
    if result is None or result == b"" or result == "":
        return
    if result is True or result == 1:
        return
    raise SafeERC20Error("ERC20 operation did not succeed: %s" % context)


class SafeERC20:
    """Wraps an ERC-20 token and exposes safe transfer helpers."""

    def __init__(self, token):
        self.token = token

    def safe_transfer(self, to, value):
        """Transfer ``value`` to ``to``, accepting non-standard tokens."""
        try:
            result = self.token.transfer(to, value)
        except Exception as exc:
            raise SafeERC20Error("low-level call failed: %s" % exc) from exc
        _decode_result(result, "transfer")

    def safe_transfer_from(self, sender, to, value):
        """Transfer ``value`` from ``sender`` to ``to`` via allowance."""
        try:
            result = self.token.transfer_from(sender, to, value)
        except Exception as exc:
            raise SafeERC20Error("low-level call failed: %s" % exc) from exc
        _decode_result(result, "transferFrom")

    def safe_approve(self, spender, value):
        """Approve ``spender`` for ``value``, accepting non-standard tokens."""
        try:
            result = self.token.approve(spender, value)
        except Exception as exc:
            raise SafeERC20Error("low-level call failed: %s" % exc) from exc
        _decode_result(result, "approve")

    def force_approve(self, spender, value):
        """Reset allowance to zero first (required by tokens like USDT)."""
        self.safe_approve(spender, 0)
        self.safe_approve(spender, value)


def safe_transfer(token, to, value):
    """Module-level helper mirroring ``SafeERC20.safeTransfer``."""
    return SafeERC20(token).safe_transfer(to, value)


def safe_transfer_from(token, sender, to, value):
    """Module-level helper mirroring ``SafeERC20.safeTransferFrom``."""
    return SafeERC20(token).safe_transfer_from(sender, to, value)


def safe_approve(token, spender, value):
    """Module-level helper mirroring ``SafeERC20.safeApprove``."""
    return SafeERC20(token).safe_approve(spender, value)


def force_approve(token, spender, value):
    """Module-level helper mirroring ``SafeERC20.forceApprove``."""
    return SafeERC20(token).force_approve(spender, value)


def verify_transfer_success(result, context="transfer"):
    """
    Verify a transfer hook's return value.

    Intended for callers that cannot use the object-oriented wrapper (e.g. an
    exchange withdrawal response). Empty/absent data is treated as success so
    non-standard hooks keep working; an explicit falsy value is a failure.
    """
    _decode_result(result, context)


def batch_safe_transfer(transfers):
    """
    Run a batch of ``(token, to, value)`` transfers (yield harvesting).

    A single failed transfer aborts the batch so the caller can revert the
    whole operation instead of silently losing funds.
    """
    for token, to, value in transfers:
        safe_transfer(token, to, value)