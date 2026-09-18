"""Comprehensive verification test suite for Issue #1593."""

from decimal import Decimal
import hashlib
import hmac
import time
from packages.omni_backflip.models import (
    AccountFollowStatus,
    BackflipPhase,
    FailureReason,
    Vector3D,
)
from packages.omni_backflip.github_verifier import GitHubFollowVerifier
from packages.omni_backflip.kinematics import BackflipKinematicsEngine
from packages.omni_backflip.settlement import QuadrillionSettlementEngine
from packages.omni_backflip.blockly import OmniBlocksBackflipExtension
from packages.omni_backflip.backflip_gateway import OmniBackflipGateway


def test_vector_3d_operations() -> None:
    """Verify 3D Euclidean vector mathematical operations."""
    vec_a = Vector3D(1.0, 2.0, 3.0)
    vec_b = Vector3D(4.0, 5.0, 6.0)

    sum_vec = vec_a.add(vec_b)
    assert sum_vec.x == 5.0
    assert sum_vec.y == 7.0
    assert sum_vec.z == 9.0

    diff_vec = vec_b.sub(vec_a)
    assert diff_vec.x == 3.0
    assert diff_vec.y == 3.0
    assert diff_vec.z == 3.0

    dot_val = vec_a.dot(vec_b)
    assert dot_val == 32.0

    mag_sq = vec_a.magnitude_squared()
    assert mag_sq == 14.0

    unit_vec = Vector3D(3.0, 0.0, 0.0).normalized()
    assert unit_vec.x == 1.0
    assert unit_vec.y == 0.0
    assert unit_vec.z == 0.0

    zero_norm = Vector3D(0.0, 0.0, 0.0).normalized()
    assert zero_norm.x == 0.0
    assert zero_norm.y == 0.0
    assert zero_norm.z == 0.0


def test_github_handle_normalization() -> None:
    """Verify normalization of GitHub account aliases and typographical variants."""
    assert GitHubFollowVerifier.normalize_target_account("GitHuub") == "unconstructable13"
    assert GitHubFollowVerifier.normalize_target_account("GitHub") == "unconstructable13"
    assert GitHubFollowVerifier.normalize_target_account("unconstructable13") == "unconstructable13"
    assert GitHubFollowVerifier.normalize_target_account("other_user") == "other_user"


def test_github_username_syntax_validation() -> None:
    """Verify GitHub username lexical structure validation."""
    assert GitHubFollowVerifier.is_valid_username("s6pa1rta3n") is True
    assert GitHubFollowVerifier.is_valid_username("octocat-123") is True
    assert GitHubFollowVerifier.is_valid_username("") is False
    assert GitHubFollowVerifier.is_valid_username("-invalid-start") is False


def test_github_webhook_signature_verification() -> None:
    """Verify HMAC-SHA256 signature verification on inbound GitHub webhooks."""
    token = "audit-key-secret-999"
    verifier = GitHubFollowVerifier(auth_descriptor=token)
    payload = b'{"action":"follow","sender":{"login":"solver"}}'

    mac = hmac.new(token.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    valid_header = f"sha256={mac}"

    assert verifier.verify_webhook_signature(payload, valid_header) is True
    assert verifier.verify_webhook_signature(payload, "sha256=corrupted") is False
    assert verifier.verify_webhook_signature(payload, "") is False

    empty_verifier = GitHubFollowVerifier(auth_descriptor="")
    assert empty_verifier.verify_webhook_signature(payload, valid_header) is False


def test_github_follow_temporal_expiry() -> None:
    """Verify enforcement of the 30-minute bounty expiry stipulation."""
    verifier = GitHubFollowVerifier()
    issue_epoch = 1700000000.0

    valid_record = verifier.verify_follower_relationship(
        follower_username="athlete-dev",
        target_account="GitHuub",
        followed_at_epoch=issue_epoch + 1200.0,
        issue_created_epoch=issue_epoch,
    )
    assert valid_record.is_verified is True
    assert valid_record.status == AccountFollowStatus.VERIFIED
    assert valid_record.target_account == "unconstructable13"

    expired_record = verifier.verify_follower_relationship(
        follower_username="athlete-dev",
        target_account="GitHuub",
        followed_at_epoch=issue_epoch + 1801.0,
        issue_created_epoch=issue_epoch,
    )
    assert expired_record.is_verified is False
    assert expired_record.status == AccountFollowStatus.EXPIRED

    invalid_user_record = verifier.verify_follower_relationship(
        follower_username="",
        target_account="GitHuub",
        followed_at_epoch=issue_epoch + 500.0,
        issue_created_epoch=issue_epoch,
    )
    assert invalid_user_record.is_verified is False
    assert invalid_user_record.status == AccountFollowStatus.REJECTED


def test_github_anti_sybil_heuristics() -> None:
    """Verify anti-sybil scoring heuristics against synthetic bot profiles."""
    trusted_profile = {"account_age_days": 120.0, "public_repos": 10, "has_2fa": True}
    is_trusted, score = GitHubFollowVerifier.evaluate_anti_sybil(trusted_profile)
    assert is_trusted is True
    assert score == 1.0

    sybil_profile = {"account_age_days": 2.0, "public_repos": 0, "has_2fa": False}
    is_trusted, score = GitHubFollowVerifier.evaluate_anti_sybil(sybil_profile)
    assert is_trusted is False
    assert score == 0.0


def test_kinematics_imu_backflip_success() -> None:
    """Verify kinematic evaluation on an authentic successful backflip IMU trajectory."""
    telemetry = BackflipKinematicsEngine.generate_synthetic_imu_telemetry(success=True)
    analysis = BackflipKinematicsEngine.analyze_inertial_telemetry(telemetry)

    assert analysis.is_successful is True
    assert analysis.detected_phase == BackflipPhase.STABILIZED
    assert analysis.total_rotation_deg >= 330.0
    assert analysis.max_altitude_m >= 1.25
    assert analysis.airtime_s >= 0.40
    assert analysis.stability_score >= 0.70
    assert len(analysis.failure_reasons) == 0


def test_kinematics_imu_insufficient_rotation() -> None:
    """Verify failure detection on under-rotated backflip attempts."""
    telemetry = BackflipKinematicsEngine.generate_synthetic_imu_telemetry(
        success=False, failure_mode=FailureReason.INSUFFICIENT_ROTATION
    )
    analysis = BackflipKinematicsEngine.analyze_inertial_telemetry(telemetry)

    assert analysis.is_successful is False
    assert FailureReason.INSUFFICIENT_ROTATION.value in analysis.failure_reasons


def test_kinematics_imu_insufficient_height() -> None:
    """Verify failure detection when vertical displacement is below required threshold."""
    telemetry = BackflipKinematicsEngine.generate_synthetic_imu_telemetry(
        success=False, failure_mode=FailureReason.INSUFFICIENT_HEIGHT
    )
    analysis = BackflipKinematicsEngine.analyze_inertial_telemetry(telemetry)

    assert analysis.is_successful is False
    assert FailureReason.INSUFFICIENT_HEIGHT.value in analysis.failure_reasons


def test_kinematics_imu_axial_deviation() -> None:
    """Verify failure detection on excessive roll/yaw off-axis drift."""
    telemetry = BackflipKinematicsEngine.generate_synthetic_imu_telemetry(
        success=False, failure_mode=FailureReason.AXIAL_DEVIATION
    )
    analysis = BackflipKinematicsEngine.analyze_inertial_telemetry(telemetry)

    assert analysis.is_successful is False
    assert FailureReason.AXIAL_DEVIATION.value in analysis.failure_reasons


def test_kinematics_empty_telemetry() -> None:
    """Verify graceful rejection of empty or insufficient sensor telemetry."""
    analysis = BackflipKinematicsEngine.analyze_inertial_telemetry([])
    assert analysis.is_successful is False
    assert FailureReason.INSUFFICIENT_AIRTIME.value in analysis.failure_reasons


def test_kinematics_skeletal_poses() -> None:
    """Verify skeletal pose tracking and inversion validation."""
    poses = BackflipKinematicsEngine.generate_synthetic_skeletal_poses(success=True)
    analysis = BackflipKinematicsEngine.analyze_skeletal_poses(poses)

    assert analysis.is_successful is True
    assert analysis.peak_pitch_deg >= 140.0
    assert analysis.stability_score >= 0.70

    empty_analysis = BackflipKinematicsEngine.analyze_skeletal_poses([])
    assert empty_analysis.is_successful is False


def test_quadrillion_settlement_nominal_calculation() -> None:
    """Verify arbitrary-precision accounting for nominal $239.4 quadrillion bounty."""
    calc = QuadrillionSettlementEngine.calculate_settlement()

    expected_nominal = Decimal("239398281948585883")
    assert calc["nominal_usd"] == expected_nominal
    assert calc["effective_usd"] == expected_nominal

    expected_coins = Decimal("299247852435732353.7500")
    assert calc["coins_total"] == expected_coins

    assert calc["contributor_ratio"] == Decimal("0.85")

    expected_contrib_coins = Decimal("254360674570372500.6875")
    assert calc["contributor_coins"] == expected_contrib_coins

    expected_contrib_cash = Decimal("183139685690668200.50")
    assert calc["contributor_cash_usd"] == expected_contrib_cash

    expected_fee = Decimal("56258596257917682.50")
    assert calc["platform_fee_usd"] == expected_fee

    assert calc["contributor_cash_usd"] + calc["platform_fee_usd"] == expected_nominal


def test_quadrillion_settlement_reported_coins() -> None:
    """Verify settlement when locking to issue-reported coin integer."""
    calc = QuadrillionSettlementEngine.calculate_settlement(use_reported_coins=True)
    assert calc["coins_total"] == Decimal("299247852435732352")


def test_quadrillion_settlement_up_to_clause() -> None:
    """Verify variable payout calculation under terms and conditions 'up to' clause."""
    partial_payout = Decimal("1000000.00")
    calc = QuadrillionSettlementEngine.calculate_settlement(agreed_payout_usd=partial_payout)

    assert calc["effective_usd"] == partial_payout
    assert calc["coins_total"] == Decimal("1250000.0000")
    assert calc["contributor_cash_usd"] == Decimal("765000.00")
    assert calc["platform_fee_usd"] == Decimal("235000.00")


def test_quadrillion_address_validation() -> None:
    """Verify EVM and Stellar cryptographic address validation."""
    assert QuadrillionSettlementEngine.validate_evm_address(
        QuadrillionSettlementEngine.CANONICAL_EVM
    ) is True
    assert QuadrillionSettlementEngine.validate_evm_address("0x123") is False
    assert QuadrillionSettlementEngine.validate_evm_address("") is False

    assert QuadrillionSettlementEngine.validate_stellar_address(
        QuadrillionSettlementEngine.CANONICAL_STELLAR
    ) is True
    assert QuadrillionSettlementEngine.validate_stellar_address("GSHORT") is False
    assert QuadrillionSettlementEngine.validate_stellar_address("") is False


def test_quadrillion_receipt_generation() -> None:
    """Verify cryptographic receipt generation and digest determinism."""
    calc = QuadrillionSettlementEngine.calculate_settlement()
    receipt = QuadrillionSettlementEngine.generate_receipt(
        settlement_data=calc,
        recipient_evm=QuadrillionSettlementEngine.CANONICAL_EVM,
        recipient_stellar=QuadrillionSettlementEngine.CANONICAL_STELLAR,
        timestamp_epoch=1700000000.0,
    )

    assert receipt.nominal_bounty_usd == Decimal("239398281948585883")
    assert receipt.recipient_evm == QuadrillionSettlementEngine.CANONICAL_EVM
    assert receipt.recipient_stellar == QuadrillionSettlementEngine.CANONICAL_STELLAR
    assert len(receipt.tx_hash) == 64


def test_blockly_definitions_and_transpilation() -> None:
    """Verify Blockly block schema generation and code transpilers."""
    blocks = OmniBlocksBackflipExtension.get_block_definitions()
    assert len(blocks) == 3

    toolbox_xml = OmniBlocksBackflipExtension.get_toolbox_xml()
    assert "<category name=\"OmniBackflip\"" in toolbox_xml
    assert "omni_when_followed_github" in toolbox_xml

    py_code = OmniBlocksBackflipExtension.transpile_to_python(
        "omni_when_followed_github",
        {"FOLLOWER": "coder", "TARGET": "unconstructable13"},
    )
    assert "verifier.verify_follower_relationship" in py_code

    js_code = OmniBlocksBackflipExtension.transpile_to_javascript(
        "omni_detect_backflip_telemetry",
        {"TELEMETRY": "sensor_stream"},
    )
    assert "kinematics.analyzeInertialTelemetry(sensor_stream);" in js_code


def test_gateway_full_pipeline_success() -> None:
    """Verify full orchestration gateway with valid telemetry and routing."""
    gateway = OmniBackflipGateway()
    now_epoch = time.time()
    telemetry = BackflipKinematicsEngine.generate_synthetic_imu_telemetry(success=True)

    result = gateway.process_bounty_claim(
        follower_username="universal-contributor",
        target_account="GitHuub",
        followed_at_epoch=now_epoch - 300.0,
        issue_created_epoch=now_epoch - 600.0,
        imu_readings=telemetry,
        recipient_evm=QuadrillionSettlementEngine.CANONICAL_EVM,
        recipient_stellar=QuadrillionSettlementEngine.CANONICAL_STELLAR,
    )

    assert result["is_approved"] is True
    assert result["follow_record"].is_verified is True
    assert result["motion_analysis"].is_successful is True
    assert result["settlement_receipt"] is not None
    assert result["settlement_receipt"].contributor_cash_usd == Decimal("183139685690668200.50")


def test_gateway_rejection_expired_follow() -> None:
    """Verify gateway rejection when follow event exceeds 30-minute window."""
    gateway = OmniBackflipGateway()
    now_epoch = time.time()
    telemetry = BackflipKinematicsEngine.generate_synthetic_imu_telemetry(success=True)

    result = gateway.process_bounty_claim(
        follower_username="universal-contributor",
        target_account="GitHuub",
        followed_at_epoch=now_epoch + 100.0,
        issue_created_epoch=now_epoch - 2000.0,
        imu_readings=telemetry,
    )

    assert result["is_approved"] is False
    assert FailureReason.UNVERIFIED_FOLLOWER.value in result["rejection_reasons"]
    assert FailureReason.TEMPORAL_TIMEOUT.value in result["rejection_reasons"]
