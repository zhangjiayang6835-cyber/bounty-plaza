"""Quadratic Projectile Reflectivity & Specular Angle Calculation Engine.
Resolves Issue #649: [Bounty $145] Increase Reflectivity of projectile/energy/proj_weak_laser_2
Based On Angle Of Impact with /turf/wall/reflective.

Key Mechanics:
- Quadratic reflectivity scaling: Reflectivity probability R(θ) increases quadratically
  with the angle of incidence θ: R(θ) = R_base + (R_max - R_base) * (θ / 90.0)^2.
- Standard reflection angle bounded strictly to [0, 89] degrees (clamped).
- Subtype /turf/wall/reflective/random generates a uniform random reflection angle in [0, 180] degrees.
- BYOND DM source code snippet for Space Station 13 projectile subsystem.
"""

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class WallReflectiveType(str, Enum):
    STANDARD = "standard"
    RANDOM = "random"
    REINFORCED = "reinforced"


@dataclass
class ReflectiveWall:
    wall_type: WallReflectiveType = WallReflectiveType.STANDARD
    base_reflectivity: float = 0.15
    max_reflectivity: float = 0.98

    def calculate_reflectivity_probability(self, incident_angle_deg: float) -> float:
        """Computes quadratic reflectivity based on incident angle (0 to 90 degrees).

        R(θ) = R_base + (R_max - R_base) * (θ / 90)^2
        """
        clamped_angle = max(0.0, min(90.0, float(incident_angle_deg)))
        normalized_ratio = clamped_angle / 90.0
        quadratic_factor = normalized_ratio ** 2
        p = self.base_reflectivity + (self.max_reflectivity - self.base_reflectivity) * quadratic_factor
        return round(min(1.0, max(0.0, p)), 4)

    def calculate_reflection_angle(
        self,
        incident_angle_deg: float,
        rng_seed: Optional[int] = None,
    ) -> float:
        """Determines the outgoing reflection angle.

        - Standard walls: clamped strictly between 0 and 89 degrees.
        - Random walls (/turf/wall/reflective/random): uniformly distributed between 0 and 180 degrees.
        """
        if self.wall_type == WallReflectiveType.RANDOM:
            rng = random.Random(rng_seed) if rng_seed is not None else random
            return round(rng.uniform(0.0, 180.0), 2)

        # Standard specular reflection clamped to [0, 89]
        clamped = max(0.0, min(89.0, float(incident_angle_deg)))
        return round(clamped, 2)


@dataclass
class WeakLaser2Projectile:
    """Model for /obj/projectile/energy/proj_weak_laser_2."""

    projectile_id: str = "proj_weak_laser_2"
    damage: float = 15.0
    color: str = "#FF5500"
    current_angle: float = 45.0
    reflections_count: int = 0
    max_reflections: int = 5

    def impact_reflective_wall(
        self,
        wall: ReflectiveWall,
        incident_angle_deg: float,
        rng_roll: Optional[float] = None,
        rng_seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Simulates projectile collision with a reflective wall."""
        if self.reflections_count >= self.max_reflections:
            return {
                "reflected": False,
                "reason": "max_reflections_reached",
                "incident_angle": incident_angle_deg,
                "damage_dealt": self.damage,
            }

        prob = wall.calculate_reflectivity_probability(incident_angle_deg)
        roll = rng_roll if rng_roll is not None else random.random()

        if roll <= prob:
            # Reflection successful
            self.reflections_count += 1
            out_angle = wall.calculate_reflection_angle(incident_angle_deg, rng_seed=rng_seed)
            self.current_angle = out_angle
            return {
                "reflected": True,
                "wall_type": wall.wall_type.value,
                "incident_angle": incident_angle_deg,
                "reflectivity_probability": prob,
                "reflection_angle": out_angle,
                "reflections_count": self.reflections_count,
            }

        return {
            "reflected": False,
            "reason": "reflection_failed_absorbed",
            "incident_angle": incident_angle_deg,
            "reflectivity_probability": prob,
            "damage_dealt": self.damage,
        }


# BYOND DM Implementation for SS13 codebases
BYOND_REFLECTIVE_DM_SOURCE: str = """
// =============================================================================
// Space Station 13: Quadratic Angle-Based Laser Reflection
// Resolves: Issue #649 - Reflectivity of proj_weak_laser_2 on /turf/closed/wall/reflective
// =============================================================================

/obj/projectile/energy/proj_weak_laser_2
	name = "weak laser beam"
	icon_state = "laser_weak_2"
	damage = 15
	damage_type = BURN
	var/max_reflections = 5
	var/reflection_count = 0

/turf/closed/wall/reflective
	name = "reflective wall"
	desc = "A mirror-finish titanium alloy plating capable of reflecting coherent light."
	icon_state = "reflec_wall"
	var/base_reflectivity = 0.15
	var/max_reflectivity = 0.98

/turf/closed/wall/reflective/proc/get_reflectivity(incident_angle)
	var/clamped = clamp(incident_angle, 0, 90)
	var/ratio = clamped / 90.0
	// Quadratic reflectivity curve: R(theta) = base + (max - base) * (theta/90)^2
	return base_reflectivity + (max_reflectivity - base_reflectivity) * (ratio * ratio)

/turf/closed/wall/reflective/proc/get_reflection_angle(incident_angle)
	// Bounded between 0 and 89 degrees
	return clamp(incident_angle, 0, 89)

/turf/closed/wall/reflective/random
	name = "crystalline reflective wall"
	desc = "A faceted crystalline wall that scatters reflected beams in chaotic directions."

/turf/closed/wall/reflective/random/get_reflection_angle(incident_angle)
	// Uniform random angle between 0 and 180 degrees
	return rand(0, 180)

/obj/projectile/energy/proj_weak_laser_2/on_hit(atom/target, blocked = 0)
	if(istype(target, /turf/closed/wall/reflective) && reflection_count < max_reflections)
		var/turf/closed/wall/reflective/R = target
		var/incident_angle = abs(Angle - get_surface_normal(target))
		var/reflect_prob = R.get_reflectivity(incident_angle)
		if(prob(reflect_prob * 100))
			reflection_count++
			var/new_angle = R.get_reflection_angle(incident_angle)
			set_angle(new_angle)
			playsound(src, 'sound/weapons/laser_bounce.ogg', 50, TRUE)
			return BULLET_ACT_FORCE_RESET
	return ..()
"""
