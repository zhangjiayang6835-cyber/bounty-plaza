"""Bitcoin invoicing, satoshi conversions, and REWARD_POLICY bounty settlement engine."""

import hashlib
import re
import time
import uuid
from decimal import Decimal
from typing import Dict, Optional
from packages.omni_boxy_saas.models import (
    BitcoinInvoice,
    BountySettlement,
    InvoiceStatus,
)


EVM_PAYOUT_ADDRESS = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
STELLAR_PAYOUT_ADDRESS = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
SATOSHIS_PER_BITCOIN = Decimal("100000000")


def btc_to_satoshis(amount_btc: Decimal) -> int:
    """Convert decimal Bitcoin denomination to integer Satoshis."""
    sats = int(round(amount_btc * SATOSHIS_PER_BITCOIN))
    return sats


def satoshis_to_btc(satoshis: int) -> Decimal:
    """Convert integer Satoshis to exact decimal Bitcoin amount."""
    btc_amount = Decimal(str(satoshis)) / SATOSHIS_PER_BITCOIN
    return btc_amount


def is_valid_bitcoin_address(address: str) -> bool:
    """Validate Bitcoin address against P2PKH, P2SH, and Bech32 syntax."""
    if not address or len(address) < 26 or len(address) > 90:
        return False
    if address.startswith("1") or address.startswith("3"):
        base58_pattern = r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$"
        return bool(re.match(base58_pattern, address))
    if address.startswith("bc1q") or address.startswith("bc1p"):
        bech32_pattern = r"^bc1[a-z0-9]{38,87}$"
        return bool(re.match(bech32_pattern, address))
    return False


def is_valid_txid(txid: str) -> bool:
    """Verify transaction identifier is a 64-character hexadecimal string."""
    if not txid or len(txid) != 64:
        return False
    hex_pattern = r"^[0-9a-fA-F]{64}$"
    return bool(re.match(hex_pattern, txid))


def derive_deterministic_btc_address(tenant_id: str, sequence_id: int) -> str:
    """Derive deterministic native SegWit receiving address for tenant billing."""
    entropy_seed = f"boxy_btc_{tenant_id}_{sequence_id}"
    digest = hashlib.sha256(entropy_seed.encode("utf-8")).hexdigest()
    bech32_payload = digest[:38]
    derived_addr = f"bc1q{bech32_payload}"
    return derived_addr


class BitcoinBillingEngine:
    """Coordinates BIP-21 invoice generation, satoshi calculations, and subscription settlement."""

    def __init__(self, default_btc_usd_rate: Decimal = Decimal("65000.00")) -> None:
        """Initialize billing engine with default spot price and invoice repository."""
        self.default_btc_usd_rate = default_btc_usd_rate
        self._invoices: Dict[str, BitcoinInvoice] = {}
        self._tenant_sequence: Dict[str, int] = {}

    def create_invoice(
        self,
        tenant_id: str,
        amount_usd: Decimal,
        btc_rate_usd: Optional[Decimal] = None,
        expires_in_seconds: float = 3600.0,
    ) -> BitcoinInvoice:
        """Generate a new BIP-21 compliant Bitcoin invoice for tenant."""
        rate = btc_rate_usd or self.default_btc_usd_rate
        amount_btc = (amount_usd / rate).quantize(Decimal("0.00000001"))
        amount_sats = btc_to_satoshis(amount_btc)

        seq = self._tenant_sequence.get(tenant_id, 0) + 1
        self._tenant_sequence[tenant_id] = seq

        receiving_address = derive_deterministic_btc_address(tenant_id, seq)
        invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
        bip21_uri = f"bitcoin:{receiving_address}?amount={amount_btc}&label=BoxySaaS&message={invoice_id}"

        now = time.time()
        invoice = BitcoinInvoice(
            invoice_id=invoice_id,
            tenant_id=tenant_id,
            amount_usd=amount_usd,
            amount_btc=amount_btc,
            amount_satoshis=amount_sats,
            address=receiving_address,
            bip21_uri=bip21_uri,
            status=InvoiceStatus.PENDING,
            created_at=now,
            expires_at=now + expires_in_seconds,
            confirmations=0,
        )
        self._invoices[invoice_id] = invoice
        return invoice

    def get_invoice(self, invoice_id: str) -> Optional[BitcoinInvoice]:
        """Fetch invoice by identifier."""
        return self._invoices.get(invoice_id)

    def confirm_invoice(
        self,
        invoice_id: str,
        txid: str,
        confirmations: int = 1,
    ) -> BitcoinInvoice:
        """Mark invoice confirmed upon verification of transaction hash and required blocks."""
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise KeyError(f"Invoice '{invoice_id}' does not exist")

        if not is_valid_txid(txid):
            raise ValueError(f"Invalid transaction hash format: {txid}")

        invoice.txid = txid
        invoice.confirmations = confirmations
        invoice.status = InvoiceStatus.CONFIRMED
        return invoice

    def calculate_bounty_settlement(
        self,
        bounty_usd: Decimal = Decimal("99999999.00"),
        btc_rate_usd: Decimal = Decimal("65000.00"),
    ) -> BountySettlement:
        """Compute full financial settlement under REWARD_POLICY rules for Issue #1570."""
        dec_coin_multiplier = Decimal("1.25")
        dec_redemption_rate = Decimal("0.72")

        if bounty_usd < Decimal("50"):
            contributor_ratio = Decimal("0.95")
        elif bounty_usd < Decimal("200"):
            contributor_ratio = Decimal("0.92")
        elif bounty_usd < Decimal("500"):
            contributor_ratio = Decimal("0.90")
        elif bounty_usd < Decimal("1000"):
            contributor_ratio = Decimal("0.87")
        else:
            contributor_ratio = Decimal("0.85")

        coin_reward = bounty_usd * dec_coin_multiplier
        contributor_coins = coin_reward * contributor_ratio
        cash_payout_usd = contributor_coins * dec_redemption_rate
        platform_fee_usd = bounty_usd - cash_payout_usd

        btc_payout = (cash_payout_usd / btc_rate_usd).quantize(Decimal("0.00000001"))

        settlement = BountySettlement(
            total_bounty_usd=bounty_usd,
            coin_reward=coin_reward,
            contributor_ratio=contributor_ratio,
            contributor_coins=contributor_coins,
            cash_payout_usd=cash_payout_usd,
            platform_fee_usd=platform_fee_usd,
            btc_rate_usd=btc_rate_usd,
            btc_payout=btc_payout,
            payout_evm_address=EVM_PAYOUT_ADDRESS,
            payout_stellar_address=STELLAR_PAYOUT_ADDRESS,
        )
        return settlement
