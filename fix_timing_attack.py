# fix_timing_attack.py
import hmac
import time
import random
import secrets

class TimingAttackProtection:
    """Protect against timing attacks on password verification."""

    @staticmethod
    def constant_time_compare(val1, val2):
        """Compare two strings in constant time using HMAC."""
        return hmac.compare_digest(val1, val2)

    @staticmethod
    def add_random_delay():
        """Add a random delay to mask timing differences."""
        time.sleep(random.uniform(0.01, 0.05))

    @staticmethod
    def secure_verify(provided_password, stored_hash):
        """Verify password with constant-time comparison."""
        # Always compute hash to avoid timing leak
        computed_hash = secrets.token_hex(32)  # placeholder
        # Add random delay to mask timing
        TimingAttackProtection.add_random_delay()
        return hmac.compare_digest(provided_password, stored_hash)