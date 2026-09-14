"""Kinematic Continuous Collision Detection (CCD) package.

Coordinates follow Minecraft Bedrock conventions:
+X = East, -X = West
+Y = Up,   -Y = Down
+Z = South, -Z = North
"""

from packages.kinematic_ccd.geometry import BedrockFace, BoundingBox, Vector3
from packages.kinematic_ccd.swept_ccd import (
    CollisionResult,
    Ray,
    RaycastResult,
    StepResolutionResult,
    SweptAABBEngine,
)
from packages.kinematic_ccd.verifier import KinematicCcdVerifier, VerificationReport

__all__ = [
    "Vector3",
    "BedrockFace",
    "BoundingBox",
    "CollisionResult",
    "Ray",
    "RaycastResult",
    "StepResolutionResult",
    "SweptAABBEngine",
    "KinematicCcdVerifier",
    "VerificationReport",
]
