"""Unified orchestration gateway for OmniBlocks backflip verification and settlement."""

from decimal import Decimal
import time
from typing import Any, Optional
from .github_verifier import GitHubFollowVerifier
from .kinematics import BackflipKinematicsEngine
from .models import (
    BackflipAnalysis,
    FailureReason,
    FollowVerificationRecord,
    InertialReading,
    KinematicPose,
    SettlementReceipt,
)
from .settlement import QuadrillionSettlementEngine


class OmniBackflipGateway:
    """End-to-end coordinator integrating follow verification, kinematics, and settlement."""

    def __init__(self, auth_descriptor: str = ""):
        """Initialize orchestrator components with configuration."""
        self.verifier = GitHubFollowVerifier(auth_descriptor=auth_descriptor)
        self.kinematics = BackflipKinematicsEngine()
        self.settlement = QuadrillionSettlementEngine()

    def process_bounty_claim(
        self,
        follower_username: str,
        target_account: str,
        followed_at_epoch: float,
        issue_created_epoch: float,
        imu_readings: Optional[list[InertialReading]] = None,
        skeletal_poses: Optional[list[KinematicPose]] = None,
        agreed_payout_usd: Optional[Decimal] = None,
        recipient_evm: Optional[str] = None,
        recipient_stellar: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute complete validation pipeline and conditionally issue settlement."""
        follow_record: FollowVerificationRecord = self.verifier.verify_follower_relationship(
            follower_username=follower_username,
            target_account=target_account,
            followed_at_epoch=followed_at_epoch,
            issue_created_epoch=issue_created_epoch,
        )

        motion_result: Optional[BackflipAnalysis] = None
        if imu_readings is not None:
            motion_result = self.kinematics.analyze_inertial_telemetry(imu_readings)
        elif skeletal_poses is not None:
            motion_result = self.kinematics.analyze_skeletal_poses(skeletal_poses)

        rejection_reasons: list[str] = []

        if not follow_record.is_verified:
            rejection_reasons.append(FailureReason.UNVERIFIED_FOLLOWER.value)
            if follow_record.status.value == "EXPIRED":
                rejection_reasons.append(FailureReason.TEMPORAL_TIMEOUT.value)

        if motion_result is None or not motion_result.is_successful:
            if motion_result is not None:
                rejection_reasons.extend(motion_result.failure_reasons)
            else:
                rejection_reasons.append(FailureReason.INSUFFICIENT_ROTATION.value)

        evm_target = recipient_evm if recipient_evm else self.settlement.CANONICAL_EVM
        stellar_target = recipient_stellar if recipient_stellar else self.settlement.CANONICAL_STELLAR

        if not self.settlement.validate_evm_address(evm_target):
            rejection_reasons.append("INVALID_EVM_ADDRESS")

        if not self.settlement.validate_stellar_address(stellar_target):
            rejection_reasons.append("INVALID_STELLAR_ADDRESS")

        is_approved = len(rejection_reasons) == 0
        receipt: Optional[SettlementReceipt] = None
        settlement_calc: Optional[dict[str, Decimal]] = None

        if is_approved:
            settlement_calc = self.settlement.calculate_settlement(
                agreed_payout_usd=agreed_payout_usd
            )
            now_epoch = time.time()
            receipt = self.settlement.generate_receipt(
                settlement_data=settlement_calc,
                recipient_evm=evm_target,
                recipient_stellar=stellar_target,
                timestamp_epoch=now_epoch,
            )

        return {
            "is_approved": is_approved,
            "follow_record": follow_record,
            "motion_analysis": motion_result,
            "rejection_reasons": rejection_reasons,
            "settlement_breakdown": settlement_calc,
            "settlement_receipt": receipt,
        }
