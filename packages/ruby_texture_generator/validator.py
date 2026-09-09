"""Validation module ensuring mathematical and visual fidelity of generated Ruby textures."""

import io
from dataclasses import dataclass
from typing import List, Tuple, Union
from PIL import Image


@dataclass
class ValidationResult:
    """Dataclass encapsulating verification outcomes and diagnostic messages."""

    valid: bool
    dimensions_ok: bool
    alpha_preserved: bool
    handle_preserved: bool
    ruby_hue_shifted: bool
    specular_highlight_ok: bool
    errors: List[str]


def _check_pixel(
    dp: Tuple[int, int, int, int],
    rp: Tuple[int, int, int, int],
    coord: Tuple[int, int],
    errors: List[str]
) -> Tuple[bool, bool, bool, bool]:
    """Inspect a single diamond and ruby pixel pair for visual integrity.

    :param dp: Source diamond RGBA pixel.
    :param rp: Candidate ruby RGBA pixel.
    :param coord: Tuple of (x, y) coordinates.
    :param errors: Mutable list collecting diagnostic error messages.
    :return: Tuple of four booleans (alpha_ok, handle_ok, ruby_ok, highlight_ok).
    """
    alpha_ok = dp[3] == rp[3]
    if not alpha_ok:
        errors.append(f"Alpha mismatch at {coord}: {dp[3]} vs {rp[3]}")

    is_wood = dp[0] > dp[1] + 15 and dp[0] > dp[2] + 20 and dp[3] > 0
    handle_ok = not (is_wood and dp != rp)
    if not handle_ok:
        errors.append(f"Wood handle corrupted at {coord}: {dp} vs {rp}")

    is_diamond = dp[2] > dp[0] + 15 and dp[1] > dp[0] + 10 and dp[3] > 0
    ruby_ok = True
    highlight_ok = True

    if is_diamond:
        ruby_ok = rp[0] > rp[1] and rp[0] > rp[2]
        if not ruby_ok:
            errors.append(f"Ruby pixel lacks red dominance at {coord}: {rp}")

        is_highlight = dp[0] >= 150 and dp[1] >= 240 and dp[2] >= 240
        if is_highlight:
            highlight_ok = rp[1] >= 170 and rp[2] >= 180
            if not highlight_ok:
                errors.append(f"Specular highlight lacked peach gleam at {coord}: {rp}")

    return alpha_ok, handle_ok, ruby_ok, highlight_ok


def validate_ruby_texture(
    diamond_source: Union[Image.Image, bytes],
    ruby_candidate: Union[Image.Image, bytes]
) -> ValidationResult:
    """Validate a generated Ruby texture against its Diamond original.

    :param diamond_source: Original diamond texture (Image or PNG bytes).
    :param ruby_candidate: Generated ruby texture (Image or PNG bytes).
    :return: ValidationResult with verification status and diagnostics.
    """
    errors: List[str] = []

    if isinstance(diamond_source, (bytes, bytearray)):
        dia_img = Image.open(io.BytesIO(diamond_source)).convert("RGBA")
    else:
        dia_img = diamond_source.convert("RGBA")

    if isinstance(ruby_candidate, (bytes, bytearray)):
        ruby_img = Image.open(io.BytesIO(ruby_candidate)).convert("RGBA")
    else:
        ruby_img = ruby_candidate.convert("RGBA")

    dimensions_ok = bool(ruby_img.size == (16, 16))
    if not dimensions_ok:
        errors.append(f"Invalid dimensions: expected (16, 16), got {ruby_img.size}")

    flags = {"alpha": True, "handle": True, "ruby": True, "highlight": True}

    w, h = dia_img.size
    for y in range(h):
        for x in range(w):
            res = _check_pixel(
                dia_img.getpixel((x, y)),
                ruby_img.getpixel((x, y)),
                (x, y),
                errors
            )
            flags["alpha"] = flags["alpha"] and res[0]
            flags["handle"] = flags["handle"] and res[1]
            flags["ruby"] = flags["ruby"] and res[2]
            flags["highlight"] = flags["highlight"] and res[3]

    valid = dimensions_ok and all(flags.values()) and not errors

    return ValidationResult(
        valid=valid,
        dimensions_ok=dimensions_ok,
        alpha_preserved=flags["alpha"],
        handle_preserved=flags["handle"],
        ruby_hue_shifted=flags["ruby"],
        specular_highlight_ok=flags["highlight"],
        errors=errors,
    )
