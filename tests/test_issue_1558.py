"""Unit and integration test suite for Reverse Bounty engine (Issue #1558).

Validates detection heuristics, multi-chain address verification, negative escrow
accounting, anti-spam pledge signatures, and post-mortem blog generation.
"""

from decimal import Decimal
import pytest

from packages.reverse_bounty.detector import (
    ReverseBountyDetector,
    BountyPolarity,
    detect_reverse_bounty,
)
from packages.reverse_bounty.payment_router import (
    ReversePaymentRouter,
    ChainType,
)
from packages.reverse_bounty.escrow_debit import (
    NegativeEscrowManager,
    DebitStatus,
)
from packages.reverse_bounty.anti_spam_pledge import (
    PledgeSigner,
    ScraperGovernance,
    OFFICIAL_PLEDGE_TEXT,
)
from packages.reverse_bounty.blog_generator import ReverseBountyBlogGenerator
from packages.reverse_bounty.manager import ReverseBountyEngine


def test_issue_1558_exact_text_detection():
    """Verify that the exact text of Issue #1558 is flagged as a reverse bounty."""
    detector = ReverseBountyDetector()
    title = "[Bounty] Reverse bounty"
    body = (
        "Hello! I am looking to pay a bounty of great magnitude* to whoever can "
        "complete the following tasks by April 1st, 2027:\n\n"
        "• Write a blog post detailing how you were fooled into accepting a silly "
        "bounty, publish it on your website, and leave a link here.\n"
        "• Pay me $500 in Solana, Bitcoin, Ethereum, or Monero.\n"
        "• Pledge to stop spamming random projects looking for bounties.\n\n"
        "*The bounty is negative."
    )

    result = detector.analyze(title, body)
    assert result.is_reverse_bounty is True
    assert result.polarity == BountyPolarity.HONEYPOT_PRANK
    assert result.confidence >= 0.90
    assert result.raw_amount == 500.0
    assert result.sanitized_amount == -500.0
    assert result.requires_anti_spam_pledge is True
    assert result.requires_reverse_payment is True
    assert "solana" in result.requested_chains
    assert "bitcoin" in result.requested_chains
    assert "ethereum" in result.requested_chains
    assert "monero" in result.requested_chains
    assert result.deadline == "April 1st, 2027"


def test_positive_bounty_not_flagged():
    """Verify that a legitimate positive bounty passes through unhindered."""
    detector = ReverseBountyDetector()
    title = "[Bounty] Fix high latency in websocket connection pool"
    body = "Offering $350 bounty for optimizing the connection handshake."

    result = detector.analyze(title, body)
    assert result.is_reverse_bounty is False
    assert result.polarity == BountyPolarity.POSITIVE
    assert result.raw_amount == 350.0
    assert result.sanitized_amount == 350.0
    assert result.requires_anti_spam_pledge is False
    assert result.requires_reverse_payment is False


def test_convenience_function():
    """Verify convenience function detects reverse bounty."""
    result = detect_reverse_bounty("Reverse bounty", "The bounty is negative.")
    assert result.is_reverse_bounty is True
    assert result.polarity == BountyPolarity.NEGATIVE_REVERSE


def test_solana_address_validation():
    """Verify validation of Solana public addresses."""
    valid_sol = "MSwhtUP1XaRfMf5ectKq9LnGvQxcQxxMHJo4QNaJ6Av"
    invalid_sol_chars = "0OIl_invalid_chars_in_base58_solana"
    invalid_sol_short = "Short123"

    assert ReversePaymentRouter.validate_address(ChainType.SOLANA, valid_sol) is True
    assert ReversePaymentRouter.validate_address(ChainType.SOLANA, invalid_sol_chars) is False
    assert ReversePaymentRouter.validate_address(ChainType.SOLANA, invalid_sol_short) is False


def test_bitcoin_address_validation():
    """Verify validation of Bitcoin Bech32 and Legacy addresses."""
    valid_bech32 = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
    valid_legacy = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    invalid_btc = "not_a_valid_bitcoin_address"

    assert ReversePaymentRouter.validate_address(ChainType.BITCOIN, valid_bech32) is True
    assert ReversePaymentRouter.validate_address(ChainType.BITCOIN, valid_legacy) is True
    assert ReversePaymentRouter.validate_address(ChainType.BITCOIN, invalid_btc) is False


def test_ethereum_address_validation():
    """Verify validation of Ethereum 20-byte hex addresses."""
    valid_eth = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    invalid_eth = "0x12345"
    non_hex = "0xZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"

    assert ReversePaymentRouter.validate_address(ChainType.ETHEREUM, valid_eth) is True
    assert ReversePaymentRouter.validate_address(ChainType.ETHEREUM, invalid_eth) is False
    assert ReversePaymentRouter.validate_address(ChainType.ETHEREUM, non_hex) is False


def test_monero_address_validation():
    """Verify validation of Monero 95-character and 106-character addresses."""
    valid_xmr = (
        "44AFFq5kSiGBoZ4NMDwYtN18obc8AemS33DBLWs3H7otXMV33WDReCGWhr6p45Sm"
        "3DDtWXSJW33jjdmdfBoe3Eqev9Ac6KP"
    )
    invalid_xmr_short = "44AFFq5kSiGBoZ4NMDwYtN18obc8AemS33"
    invalid_xmr_prefix = "1" + valid_xmr[1:]

    assert ReversePaymentRouter.validate_address(ChainType.MONERO, valid_xmr) is True
    assert ReversePaymentRouter.validate_address(ChainType.MONERO, invalid_xmr_short) is False
    assert ReversePaymentRouter.validate_address(ChainType.MONERO, invalid_xmr_prefix) is False


def test_reverse_quote_generation():
    """Verify reverse cryptocurrency settlement quote calculation."""
    router = ReversePaymentRouter()
    quote = router.create_quote(
        usd_amount=Decimal("500.00"),
        chain=ChainType.SOLANA,
        recipient_address="MSwhtUP1XaRfMf5ectKq9LnGvQxcQxxMHJo4QNaJ6Av"
    )

    assert quote.usd_amount == Decimal("500.00")
    assert quote.chain == ChainType.SOLANA
    assert quote.crypto_amount > Decimal("0")
    assert quote.total_crypto > quote.crypto_amount
    assert quote.expires_at > quote.timestamp
    assert quote.quote_id.startswith("quote_")


def test_invalid_address_quote_raises():
    """Verify invalid address raises ValueError when creating quote."""
    router = ReversePaymentRouter()
    with pytest.raises(ValueError):
        router.create_quote(
            usd_amount=Decimal("500.00"),
            chain=ChainType.ETHEREUM,
            recipient_address="0xInvalid"
        )


def test_unsigned_transaction_builder():
    """Verify unsigned transaction payload construction."""
    router = ReversePaymentRouter()
    quote = router.create_quote(
        usd_amount=Decimal("500.00"),
        chain=ChainType.BITCOIN,
        recipient_address="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
    )
    tx = router.build_transaction(quote=quote, memo="Reverse Settlement #1558")

    assert tx.chain == ChainType.BITCOIN
    assert tx.recipient_address == "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
    assert tx.tx_id.startswith("tx_")
    assert len(tx.payload_hex) > 0
    assert tx.status == "prepared_unsigned"


def test_negative_escrow_calculation():
    """Verify 1 USD = 1.25 coins exchange rate matches REWARD_POLICY ($500 = 625 coins)."""
    coins = NegativeEscrowManager.calculate_reverse_coins(Decimal("500.00"))
    assert coins == Decimal("625.00")


def test_negative_escrow_lifecycle():
    """Verify recording debit, on-chain settlement, and pledge waiver."""
    escrow = NegativeEscrowManager()
    record = escrow.record_debit(
        user_id="hunter_01",
        issue_id=1558,
        amount_usd=Decimal("500.00"),
        source_url="https://github.com/OmniBlocks/monorepo/issues/795"
    )

    assert record.coins_amount == Decimal("625.00")
    assert record.status == DebitStatus.PENDING
    assert escrow.get_user_balance("hunter_01") == Decimal("-625.00")

    escrow.settle_onchain(record.record_id, tx_id="tx_test_hash_999")
    assert record.status == DebitStatus.SETTLED_ONCHAIN
    assert escrow.get_user_balance("hunter_01") == Decimal("0.00")

    record2 = escrow.record_debit(
        user_id="hunter_02",
        issue_id=1558,
        amount_usd=Decimal("500.00")
    )
    assert escrow.get_user_balance("hunter_02") == Decimal("-625.00")

    escrow.waive_with_pledge_and_blog(
        record_id=record2.record_id,
        pledge_signature="sig_abc_123",
        blog_url="https://docs/blog/how_we_were_fooled_by_a_reverse_bounty.md"
    )
    assert record2.status == DebitStatus.WAIVED_VIA_PLEDGE
    assert escrow.get_user_balance("hunter_02") == Decimal("0.00")


def test_anti_spam_pledge_signing_and_verification():
    """Verify cryptographic signing and verification of anti-spam pledge."""
    signer = PledgeSigner()
    pledge = signer.sign_pledge(signer_id="s6pa1rta3n-lab", issue_ref="Issue#1558")

    assert len(pledge.signature) == 64
    assert pledge.pledge_text == OFFICIAL_PLEDGE_TEXT
    assert signer.verify_pledge(pledge) is True

    pledge.pledge_text = "Modified tampered text"
    assert signer.verify_pledge(pledge) is False


def test_scraper_governance_rejection():
    """Verify scraper governance filters reject reverse and prank bounties."""
    assert ScraperGovernance.can_interact_with_issue(
        "Reverse bounty", "Pay me $500. The bounty is negative."
    ) is False
    assert ScraperGovernance.can_interact_with_issue(
        "Standard bounty", "Please implement feature X for $200."
    ) is True


def test_blog_generator_output():
    """Verify that blog generator produces comprehensive post-mortem markdown."""
    gen = ReverseBountyBlogGenerator()
    blog = gen.generate_markdown(
        issue_ref="zhangjiayang6835-cyber/bounty-plaza#1558",
        source_url="https://github.com/OmniBlocks/monorepo/issues/795",
        amount_usd=500.0
    )

    assert "How We Were Fooled by a Reverse Bounty" in blog
    assert "zhangjiayang6835-cyber/bounty-plaza#1558" in blog
    assert "OmniBlocks/monorepo#795" in blog
    assert "Solana" in blog
    assert "Bitcoin" in blog
    assert "Ethereum" in blog
    assert "Monero" in blog
    assert "Anti-Spam Pledge" in blog


def test_reverse_bounty_engine_end_to_end():
    """Verify integrated ReverseBountyEngine processes issue from end to end."""
    engine = ReverseBountyEngine()
    result = engine.process_issue(
        title="[Bounty] Reverse bounty",
        body="Pay me $500 in Solana. The bounty is negative. Stop spamming random projects.",
        issue_id=1558,
        source_url="https://github.com/OmniBlocks/monorepo/issues/795",
        user_id="agent_alpha"
    )

    assert result["detection"]["is_reverse_bounty"] is True
    assert result["debit_record"] is not None
    assert result["debit_record"]["coins_amount"] == "625.00"
    assert result["requires_blog_post"] is True
    assert result["requires_anti_spam_pledge"] is True
    assert result["allowed_interaction"] is False

    quote = engine.generate_settlement_quote(
        chain=ChainType.SOLANA,
        recipient_address="MSwhtUP1XaRfMf5ectKq9LnGvQxcQxxMHJo4QNaJ6Av",
        amount_usd=500.0
    )
    assert quote.usd_amount == Decimal("500.0")

    tx = engine.prepare_settlement_transaction(quote)
    assert tx.chain == ChainType.SOLANA
    assert tx.status == "prepared_unsigned"

    pledge = engine.sign_anti_spam_pledge(
        signer_id="s6pa1rta3n-lab",
        issue_ref="zhangjiayang6835-cyber/bounty-plaza#1558"
    )
    assert engine.verify_pledge(pledge) is True

    blog_md = engine.generate_blog_post()
    assert len(blog_md) > 500
