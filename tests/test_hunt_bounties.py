"""Unit tests for scripts/hunt_bounties.py parsing and validation routines."""

from scripts.hunt_bounties import extract_amounts, is_real_money


def test_extract_amounts_standard_dollars():
    """Verify parsing of standard USD dollar formatting."""
    text = "Offering $500 for a fix to this issue"
    amounts = extract_amounts(text)
    assert 500 in amounts


def test_extract_amounts_decimal_tokens():
    """Verify decimal crypto amounts round accurately without truncation errors."""
    text = "Solver reward: 0.99 USDC, entry bond: 0.01 USDC"
    amounts = extract_amounts(text)
    assert 1 in amounts
    assert 99 not in amounts


def test_extract_amounts_with_commas():
    """Verify numbers formatted with thousand commas parse accurately."""
    text = "Large payout of $1,500.00 upon verified review"
    amounts = extract_amounts(text)
    assert 1500 in amounts


def test_extract_amounts_bounty_prefix_syntax():
    """Verify bounty label prefixed dollar amounts parse cleanly."""
    text = "Maintainer bounty: $250 for accepted submission"
    amounts = extract_amounts(text)
    assert 250 in amounts


def test_is_real_money_rejects_sub_threshold():
    """Verify sub-$25 bounties are rejected by filter."""
    item = {
        "title": "Fix deterministic card discovery",
        "body": "Solver reward: 0.99 USDC with verified signed quorum",
    }
    assert not is_real_money(item)


def test_is_real_money_accepts_valid_reward():
    """Verify bounties exceeding $25 threshold pass filter."""
    item = {
        "title": "Implement cross-chain settlement validator",
        "body": "Reward of 150 USDC held in smart contract escrow",
    }
    assert is_real_money(item)


def test_is_real_money_rejects_virtual_tokens_without_cash():
    """Verify purely gamified badges and points without cash are rejected."""
    item = {
        "title": "Earn reputation points",
        "body": "Submit this feature to earn 500 xp and community points",
    }
    assert not is_real_money(item)
