"""Multi-chain payment routing and reverse settlement engine.

Handles address validation, cryptocurrency conversion rates, fee estimation,
and unsigned transaction dispatch for Solana, Bitcoin, Ethereum, and Monero.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import hashlib
import re
import time
from typing import Dict, Any


class ChainType(str, Enum):
    """Supported cryptocurrency settlement networks."""
    SOLANA = "solana"
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    MONERO = "monero"


BASE58_ALPHABET = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
HEX_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")
BTC_BECH32_PATTERN = re.compile(r"^bc1[a-z0-9]{39,59}$")
BTC_LEGACY_PATTERN = re.compile(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$")
SOL_PATTERN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
XMR_PATTERN = re.compile(r"^[48][0-9AB-HJ-NP-Za-km-z]{94,105}$")


@dataclass
class PaymentQuote:
    """Pricing quote for reverse settlement."""
    usd_amount: Decimal
    chain: ChainType
    crypto_amount: Decimal
    rate_usd: Decimal
    estimated_fee_crypto: Decimal
    estimated_fee_usd: Decimal
    total_crypto: Decimal
    recipient_address: str
    quote_id: str
    timestamp: float
    expires_at: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert quote to dictionary representation."""
        return {
            "quote_id": self.quote_id,
            "usd_amount": str(self.usd_amount),
            "chain": self.chain.value,
            "crypto_amount": str(self.crypto_amount),
            "rate_usd": str(self.rate_usd),
            "estimated_fee_crypto": str(self.estimated_fee_crypto),
            "estimated_fee_usd": str(self.estimated_fee_usd),
            "total_crypto": str(self.total_crypto),
            "recipient_address": self.recipient_address,
            "timestamp": self.timestamp,
            "expires_at": self.expires_at,
        }


@dataclass
class PaymentTransaction:
    """Unsigned multi-chain payment transaction payload."""
    tx_id: str
    quote_id: str
    chain: ChainType
    recipient_address: str
    amount_crypto: Decimal
    fee_crypto: Decimal
    payload_hex: str
    memo: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction payload to dictionary representation."""
        return {
            "tx_id": self.tx_id,
            "quote_id": self.quote_id,
            "chain": self.chain.value,
            "recipient_address": self.recipient_address,
            "amount_crypto": str(self.amount_crypto),
            "fee_crypto": str(self.fee_crypto),
            "payload_hex": self.payload_hex,
            "memo": self.memo,
            "status": self.status,
        }


class ReversePaymentRouter:
    """Routes and structures reverse settlement across supported blockchains."""

    DEFAULT_RATES: Dict[ChainType, Decimal] = {
        ChainType.SOLANA: Decimal("150.00"),
        ChainType.BITCOIN: Decimal("65000.00"),
        ChainType.ETHEREUM: Decimal("3500.00"),
        ChainType.MONERO: Decimal("160.00"),
    }

    NETWORK_FEES_CRYPTO: Dict[ChainType, Decimal] = {
        ChainType.SOLANA: Decimal("0.0005"),
        ChainType.BITCOIN: Decimal("0.00015"),
        ChainType.ETHEREUM: Decimal("0.0025"),
        ChainType.MONERO: Decimal("0.00005"),
    }

    def __init__(self, custom_rates: Dict[ChainType, Decimal] = None):
        """Initialize router with default or overridden currency rates."""
        self.rates = dict(self.DEFAULT_RATES)
        if custom_rates:
            self.rates.update(custom_rates)

    @classmethod
    def validate_address(cls, chain: ChainType, address: str) -> bool:
        """Validate recipient address against network specifications.

        Args:
            chain: Target cryptocurrency blockchain.
            address: Public address string.

        Returns:
            True if address matches protocol format, False otherwise.
        """
        if not address or not isinstance(address, str):
            return False

        stripped = address.strip()

        if chain == ChainType.SOLANA:
            if not SOL_PATTERN.match(stripped):
                return False
            return set(stripped).issubset(BASE58_ALPHABET)

        if chain == ChainType.BITCOIN:
            if BTC_BECH32_PATTERN.match(stripped):
                return True
            if BTC_LEGACY_PATTERN.match(stripped):
                return set(stripped).issubset(BASE58_ALPHABET)
            return False

        if chain == ChainType.ETHEREUM:
            return bool(HEX_PATTERN.match(stripped))

        if chain == ChainType.MONERO:
            if not (len(stripped) in (95, 106) and XMR_PATTERN.match(stripped)):
                return False
            return set(stripped).issubset(BASE58_ALPHABET)

        return False

    def get_rate(self, chain: ChainType) -> Decimal:
        """Retrieve USD spot price for chain asset."""
        return self.rates.get(chain, Decimal("1.00"))

    def create_quote(self, usd_amount: Decimal, chain: ChainType, recipient_address: str) -> PaymentQuote:
        """Calculate cryptocurrency requirements for reverse payout settlement.

        Args:
            usd_amount: Payout amount in USD.
            chain: Selected cryptocurrency.
            recipient_address: Validated recipient address.

        Returns:
            PaymentQuote instance with locked conversion parameters.
        """
        if not self.validate_address(chain, recipient_address):
            raise ValueError(f"Invalid {chain.value} address format: {recipient_address}")

        usd_clean = Decimal(str(usd_amount))
        rate = self.get_rate(chain)
        crypto_amount = (usd_clean / rate).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        fee_crypto = self.NETWORK_FEES_CRYPTO.get(chain, Decimal("0.001"))
        fee_usd = (fee_crypto * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_crypto = crypto_amount + fee_crypto

        now = time.time()
        quote_seed = f"{usd_clean}:{chain.value}:{recipient_address}:{now}"
        quote_id = f"quote_{hashlib.sha256(quote_seed.encode('utf-8')).hexdigest()[:16]}"

        return PaymentQuote(
            usd_amount=usd_clean,
            chain=chain,
            crypto_amount=crypto_amount,
            rate_usd=rate,
            estimated_fee_crypto=fee_crypto,
            estimated_fee_usd=fee_usd,
            total_crypto=total_crypto,
            recipient_address=recipient_address,
            quote_id=quote_id,
            timestamp=now,
            expires_at=now + 3600.0,
        )

    def build_transaction(self, quote: PaymentQuote, memo: str = "") -> PaymentTransaction:
        """Construct unsigned transaction payload for reverse bounty settlement.

        Args:
            quote: Validated PaymentQuote.
            memo: Optional transaction memo.

        Returns:
            PaymentTransaction containing raw payload and hash.
        """
        payload_data = (
            f"CHAIN={quote.chain.value}|TO={quote.recipient_address}|"
            f"AMOUNT={quote.crypto_amount}|FEE={quote.estimated_fee_crypto}|"
            f"MEMO={memo}|EXP={quote.expires_at}"
        )
        payload_hex = payload_data.encode("utf-8").hex()
        tx_hash = hashlib.sha256(payload_data.encode("utf-8")).hexdigest()

        return PaymentTransaction(
            tx_id=f"tx_{tx_hash[:24]}",
            quote_id=quote.quote_id,
            chain=quote.chain,
            recipient_address=quote.recipient_address,
            amount_crypto=quote.crypto_amount,
            fee_crypto=quote.estimated_fee_crypto,
            payload_hex=payload_hex,
            memo=memo,
            status="prepared_unsigned",
        )
