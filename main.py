"""
Bounty Escrow and Payout Transaction Handler
Author: @Dungsky
"""

import os
import sys
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("bounty-bot")

# Regex patterns for strict cryptocurrency address validation
BTC_REGEX = re.compile(r"^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}$")
ETH_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")


class PayoutValidator:
    @staticmethod
    def validate_btc(address: str) -> bool:
        return bool(BTC_REGEX.match(address))

    @staticmethod
    def validate_eth(address: str) -> bool:
        return bool(ETH_REGEX.match(address))


def process_escrow_payout(platform: str, amount: float, address: str) -> bool:
    logger.info(f"Processing escrow payout of {amount} USDC via {platform}...")
    
    cleaned_address = address.strip()
    
    if platform.upper() == "BTC":
        if not PayoutValidator.validate_btc(cleaned_address):
            logger.error(f"Invalid Bitcoin address format: {cleaned_address}")
            return False
    elif platform.upper() == "ETH" or platform.upper() == "USDC":
        if not PayoutValidator.validate_eth(cleaned_address):
            logger.error(f"Invalid Ethereum/USDC address format: {cleaned_address}")
            return False
    else:
        logger.error(f"Unsupported payout platform: {platform}")
        return False

    logger.info(f"Payout address verified successfully for {platform}. Execution ready.")
    return True


def main():
    logger.info("Initializing Bounty Escrow Security Service...")
    
    # Default configuration parameters corresponding to issue requirements
    target_platform = os.getenv("BOUNTY_PLATFORM", "ETH")
    target_amount = float(os.getenv("BOUNTY_AMOUNT", "100.0"))
    target_address = os.getenv("BOUNTY_ADDRESS", "0xA5E6eB31868A85127B1ED82b8C760193356206ED")

    success = process_escrow_payout(target_platform, target_amount, target_address)
    if success:
        logger.info("Bounty transaction validation passed cleanly.")
        sys.exit(0)
    else:
        logger.critical("Bounty transaction validation failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
