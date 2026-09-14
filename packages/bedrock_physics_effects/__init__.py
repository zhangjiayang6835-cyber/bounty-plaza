"""Bedrock physics and 1-tick potion effect simulation module.

Provides high-precision physics simulation, velocity preservation,
dynamic fall damage dampening, and absorption shield mitigation for
Minecraft Bedrock Edition.
"""

from packages.bedrock_physics_effects.physics_engine import (
    DamageResult,
    PotionEffect,
    PlayerPhysicsConfig,
    BedrockPlayerPhysics,
    Vector3,
)
from packages.bedrock_physics_effects.verifier import (
    BedrockPhysicsVerifier,
    VerificationReport,
)

__all__ = [
    "Vector3",
    "PotionEffect",
    "DamageResult",
    "PlayerPhysicsConfig",
    "BedrockPlayerPhysics",
    "BedrockPhysicsVerifier",
    "VerificationReport",
]
