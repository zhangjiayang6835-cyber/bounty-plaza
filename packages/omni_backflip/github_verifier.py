"""GitHub account follower verification engine and webhook integrity validator."""

import hashlib
import hmac
import re
from typing import Any
from .models import AccountFollowStatus, FollowVerificationRecord


class GitHubFollowVerifier:
    """Validates user follower status, handle normalization, and webhook signatures."""

    CANONICAL_TARGET = "unconstructable13"
    ALLOWED_TARGET_VARIANTS = ("unconstructable13", "GitHuub", "GitHub")
    USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")

    def __init__(self, auth_descriptor: str = ""):
        """Initialize verifier with optional auth descriptor."""
        self.auth_descriptor = auth_descriptor

    @classmethod
    def normalize_target_account(cls, raw_target: str) -> str:
        """Normalize target account string resolving typos and aliases."""
        cleaned = raw_target.strip().lower()
        if cleaned in ("githuub", "github", "unconstructable13"):
            return cls.CANONICAL_TARGET
        return raw_target.strip()

    @classmethod
    def is_valid_username(cls, username: str) -> bool:
        """Validate whether a username follows GitHub identifier conventions."""
        if not username:
            return False
        return bool(cls.USERNAME_PATTERN.match(username))

    def verify_webhook_signature(self, payload_bytes: bytes, signature_header: str) -> bool:
        """Verify HMAC-SHA256 signature from GitHub webhook header."""
        if not self.auth_descriptor or not signature_header:
            return False
        if not signature_header.startswith("sha256="):
            return False

        expected_sig = signature_header[7:]
        mac = hmac.new(self.auth_descriptor.encode("utf-8"), payload_bytes, hashlib.sha256)
        computed_sig = mac.hexdigest()
        return hmac.compare_digest(computed_sig, expected_sig)

    def verify_follower_relationship(
        self,
        follower_username: str,
        target_account: str,
        followed_at_epoch: float,
        issue_created_epoch: float,
        max_delay_sec: float = 1800.0,
    ) -> FollowVerificationRecord:
        """Verify that follower authenticated and followed target within bounty expiry."""
        if not self.is_valid_username(follower_username):
            record_hash = self._compute_record_hash(follower_username, target_account, followed_at_epoch)
            return FollowVerificationRecord(
                username=follower_username,
                target_account=target_account,
                followed_at_epoch=followed_at_epoch,
                verification_hash=record_hash,
                is_verified=False,
                status=AccountFollowStatus.REJECTED,
            )

        norm_target = self.normalize_target_account(target_account)
        elapsed_sec = followed_at_epoch - issue_created_epoch

        if elapsed_sec < 0.0 or elapsed_sec > max_delay_sec:
            record_hash = self._compute_record_hash(follower_username, norm_target, followed_at_epoch)
            return FollowVerificationRecord(
                username=follower_username,
                target_account=norm_target,
                followed_at_epoch=followed_at_epoch,
                verification_hash=record_hash,
                is_verified=False,
                status=AccountFollowStatus.EXPIRED,
            )

        record_hash = self._compute_record_hash(follower_username, norm_target, followed_at_epoch)
        return FollowVerificationRecord(
            username=follower_username,
            target_account=norm_target,
            followed_at_epoch=followed_at_epoch,
            verification_hash=record_hash,
            is_verified=True,
            status=AccountFollowStatus.VERIFIED,
        )

    @staticmethod
    def _compute_record_hash(username: str, target: str, epoch: float) -> str:
        """Calculate deterministic SHA-256 digest for verification audit trail."""
        raw_token = f"{username}:{target}:{epoch:.3f}"
        digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        return digest

    @staticmethod
    def evaluate_anti_sybil(account_metadata: dict[str, Any]) -> tuple[bool, float]:
        """Compute anti-sybil score to prevent automated bot follow manipulation."""
        score = 0.0
        account_age_days = float(account_metadata.get("account_age_days", 0.0))
        public_repos = int(account_metadata.get("public_repos", 0))
        has_2fa = bool(account_metadata.get("has_2fa", False))

        if account_age_days >= 30.0:
            score += 0.4
        elif account_age_days >= 7.0:
            score += 0.2

        if public_repos >= 3:
            score += 0.4
        elif public_repos >= 1:
            score += 0.2

        if has_2fa:
            score += 0.2

        is_trusted = score >= 0.6
        return is_trusted, round(score, 2)
