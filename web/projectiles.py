# ... existing code ...

def calculate_reflection_angle(impact_angle):
    """
    Calculate the reflection angle based on a quadratic curve relative to the angle of impact.
    The minimum angle of reflection is 0 degrees and the maximum is 89 degrees.
    """
    # Quadratic curve calculation
    reflection_angle = impact_angle ** 2 / 90
    # Ensure the angle is within the valid range
    reflection_angle = max(0, min(89, reflection_angle))
    return reflection_angle

def reflect_projectile(projectile, surface):
    """
    Reflect the projectile based on the angle of impact and the type of surface.
    """
    if surface.type == "/turf/wall/reflective/random":
        # Random angle reflection for random reflective surfaces
        reflection_angle = random.uniform(0, 180)
    else:
        # Calculate the reflection angle based on the angle of impact
        impact_angle = calculate_impact_angle(projectile, surface)
        reflection_angle = calculate_reflection_angle(impact_angle)

    # Reflect the projectile
    # ... existing reflection logic ...

# ... existing code ...