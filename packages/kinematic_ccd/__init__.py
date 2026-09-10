"""Kinematic Continuous Collision Detection package for Minecraft Bedrock.

Coordinates align with Bedrock standards:
+X = East, -X = West
+Y = Up,   -Y = Down
+Z = South, -Z = North
"""

from packages.kinematic_ccd.geometry import BedrockFace, BoundingBox, Vector3
from packages.kinematic_ccd.swept_ccd import (
    CollisionResult,
    Ray,
    RayHit,
    RaycastResult,
    StepResult,
    SweptAABBEngine,
)
from packages.kinematic_ccd.verifier import KinematicCcdVerifier

__all__ = [
    "BedrockFace",
    "BoundingBox",
    "CollisionResult",
    "KinematicCcdVerifier",
    "Ray",
    "RayHit",
    "RaycastResult",
    "StepResult",
    "SweptAABBEngine",
    "Vector3",
]
