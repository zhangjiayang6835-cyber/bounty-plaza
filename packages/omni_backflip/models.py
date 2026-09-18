"""Data models and immutable telemetry structures for OmniBackflip engine."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import math


class AccountFollowStatus(str, Enum):
    """Lifecycle status for target GitHub account follow verification."""

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    NOT_FOLLOWING = "NOT_FOLLOWING"


class BackflipPhase(str, Enum):
    """Biomechanics phases in a backflip trajectory."""

    PREPARATION = "PREPARATION"
    TAKEOFF = "TAKEOFF"
    INVERTED = "INVERTED"
    TUCK = "TUCK"
    EXTENSION = "EXTENSION"
    LANDING = "LANDING"
    STABILIZED = "STABILIZED"


class FailureReason(str, Enum):
    """Categorized failure conditions during motion analysis."""

    INSUFFICIENT_ROTATION = "INSUFFICIENT_ROTATION"
    INSUFFICIENT_HEIGHT = "INSUFFICIENT_HEIGHT"
    INSUFFICIENT_AIRTIME = "INSUFFICIENT_AIRTIME"
    NO_INVERSION = "NO_INVERSION"
    UNSTABLE_LANDING = "UNSTABLE_LANDING"
    AXIAL_DEVIATION = "AXIAL_DEVIATION"
    TEMPORAL_TIMEOUT = "TEMPORAL_TIMEOUT"
    UNVERIFIED_FOLLOWER = "UNVERIFIED_FOLLOWER"
    ZERO_SETTLEMENT = "ZERO_SETTLEMENT"


@dataclass(frozen=True)
class Vector3D:
    """Three-dimensional Euclidean vector with kinematic operations."""

    x: float
    y: float
    z: float

    def add(self, other: "Vector3D") -> "Vector3D":
        """Add two vectors component-wise."""
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def sub(self, other: "Vector3D") -> "Vector3D":
        """Subtract other vector from self."""
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def dot(self, other: "Vector3D") -> float:
        """Calculate vector dot product."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def magnitude_squared(self) -> float:
        """Calculate squared magnitude of the vector."""
        return self.x * self.x + self.y * self.y + self.z * self.z

    def magnitude(self) -> float:
        """Calculate Euclidean norm of the vector."""
        return math.sqrt(self.magnitude_squared())

    def normalized(self) -> "Vector3D":
        """Return unit vector along the same direction."""
        mag = self.magnitude()
        if mag == 0.0:
            return Vector3D(0.0, 0.0, 0.0)
        return Vector3D(self.x / mag, self.y / mag, self.z / mag)


@dataclass(frozen=True)
class InertialReading:
    """Inertial measurement unit (IMU) telemetry sample."""

    timestamp_ms: float
    pitch_deg: float
    roll_deg: float
    yaw_deg: float
    gyro_pitch_rate: float
    accel_vertical: float
    altitude_m: float


@dataclass(frozen=True)
class KinematicPose:
    """Body skeletal landmarks for biomechanical pose tracking."""

    timestamp_ms: float
    head: Vector3D
    torso: Vector3D
    pelvis: Vector3D
    left_ankle: Vector3D
    right_ankle: Vector3D


@dataclass
class FollowVerificationRecord:
    """Record of GitHub follower authentication and verification."""

    username: str
    target_account: str
    followed_at_epoch: float
    verification_hash: str
    is_verified: bool
    status: AccountFollowStatus


@dataclass
class BackflipAnalysis:
    """Aggregated biomechanical evaluation result for backflip execution."""

    is_successful: bool
    peak_pitch_deg: float
    total_rotation_deg: float
    max_altitude_m: float
    airtime_s: float
    stability_score: float
    detected_phase: BackflipPhase
    failure_reasons: list[str] = field(default_factory=list)


@dataclass
class SettlementReceipt:
    """Cryptographically referenced settlement receipt for quadrillion bounty."""

    nominal_bounty_usd: Decimal
    coins_total: Decimal
    contributor_ratio: Decimal
    contributor_coins: Decimal
    contributor_cash_usd: Decimal
    platform_fee_usd: Decimal
    recipient_evm: str
    recipient_stellar: str
    timestamp_epoch: float
    tx_hash: str
