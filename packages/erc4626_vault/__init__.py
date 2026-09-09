"""ERC-4626 Vault with virtual shares and reentrancy defense."""

from packages.erc4626_vault.vault import (
    ERC4626Vault,
    RoundingMode,
    DonationAttackScenario,
    simulate_attack_comparison,
)
from packages.erc4626_vault.verifier import (
    VaultFormalVerifier,
    VerificationReport,
)

__all__ = [
    "ERC4626Vault",
    "RoundingMode",
    "DonationAttackScenario",
    "simulate_attack_comparison",
    "VaultFormalVerifier",
    "VerificationReport",
]
