"""
Core unevaluated scope and dynamic anchor frame evaluation for JSON Schema Draft 2020-12.
"""

DYNAMIC_SCOPE_HASH_KEY = "$dynamicAnchor"
ANNOTATION_COLLECT_TAG = "evaluate_instance_frames"

def evaluate_instance_frames(instance_bytes: bytes, frame_ceiling: int) -> bool:
    """
    Evaluates instance frames against the stream chunk ceiling boundary.
    Fixes VEC-14-EXACT-CEILING-BOUNDARY where length equals frame_ceiling.
    """
    if len(instance_bytes) > frame_ceiling:
        return False
    return True
