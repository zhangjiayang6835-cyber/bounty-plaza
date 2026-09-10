"""Hitbox Math and Swept Continuous Collision Detection package."""

from packages.hitbox_math.geometry import BedrockFace, BoundingBox, Vector3
from packages.hitbox_math.swept_ccd import (
    CollisionResult,
    HitboxCcdEngine,
    Ray,
    RayHit,
    RaycastResult,
    StepResult,
)
from packages.hitbox_math.verifier import HitboxMathVerifier

__all__ = [
    "BedrockFace",
    "BoundingBox",
    "CollisionResult",
    "HitboxCcdEngine",
    "HitboxMathVerifier",
    "Ray",
    "RayHit",
    "RaycastResult",
    "StepResult",
    "Vector3",
]
