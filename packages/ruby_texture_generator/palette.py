"""Palette definition and color conversion mathematics for Jappa-style Ruby assets."""

import math
from typing import Tuple, List

DIAMOND_PALETTE: List[Tuple[int, int, int]] = [
    (188, 252, 252),
    (155, 244, 242),
    (95, 234, 201),
    (74, 237, 217),
    (45, 194, 191),
    (32, 139, 139),
    (25, 95, 95),
    (17, 57, 54),
]

RUBY_PALETTE: List[Tuple[int, int, int]] = [
    (255, 205, 218),
    (255, 185, 195),
    (247, 92, 116),
    (240, 73, 96),
    (196, 35, 60),
    (140, 19, 40),
    (84, 9, 23),
    (48, 5, 13),
]


def color_distance(
    c1: Tuple[int, int, int],
    c2: Tuple[int, int, int]
) -> float:
    """Compute weighted perceptual Euclidean distance between two RGB triplets.

    :param c1: First RGB color tuple.
    :param c2: Second RGB color tuple.
    :return: Weighted perceptual color distance.
    """
    dr = c1[0] - c2[0]
    dg = c1[1] - c2[1]
    db = c1[2] - c2[2]
    return math.sqrt(2 * (dr ** 2) + 4 * (dg ** 2) + 3 * (db ** 2))


def is_diamond_pixel(r: int, g: int, b: int, a: int) -> bool:
    """Determine whether an RGBA pixel belongs to the diamond mineral family.

    :param r: Red component (0-255).
    :param g: Green component (0-255).
    :param b: Blue component (0-255).
    :param a: Alpha component (0-255).
    :return: True if the pixel is diamond material.
    """
    if a < 10:
        return False
    if r > g + 15 and r > b + 20:
        return False

    cyan_dominant = (b > r + 15 and g > r + 10 and (g + b) > 65)
    bright_cyan = (b > 100 and g > 100 and r < 165 and (g + b) / 2 > r + 20)

    if cyan_dominant or bright_cyan:
        return True

    for dia in DIAMOND_PALETTE:
        if color_distance((r, g, b), dia) < 45.0:
            return True

    return False


def interpolate_ruby_ramp(lightness: float) -> Tuple[int, int, int]:
    """Calculate continuous hue-shifted Ruby RGB values from relative luminance.

    :param lightness: Normalized relative luminance (0.0 to 1.0).
    :return: Hue-shifted RGB color tuple.
    """
    clamped = max(0.0, min(1.0, lightness))

    if clamped >= 0.85:
        factor = (clamped - 0.85) / 0.15
        return (
            255,
            round(185 + factor * 70),
            round(195 + factor * 60),
        )

    if clamped >= 0.60:
        factor = (clamped - 0.60) / 0.25
        return (
            round(240 + factor * 15),
            round(73 + factor * 112),
            round(96 + factor * 99),
        )

    if clamped >= 0.40:
        factor = (clamped - 0.40) / 0.20
        return (
            round(196 + factor * 44),
            round(35 + factor * 38),
            round(60 + factor * 36),
        )

    if clamped >= 0.20:
        factor = (clamped - 0.20) / 0.20
        return (
            round(140 + factor * 56),
            round(19 + factor * 16),
            round(40 + factor * 20),
        )

    if clamped >= 0.10:
        factor = (clamped - 0.10) / 0.10
        return (
            round(84 + factor * 56),
            round(9 + factor * 10),
            round(23 + factor * 17),
        )

    factor = clamped / 0.10
    return (
        round(48 + factor * 36),
        round(5 + factor * 4),
        round(13 + factor * 10),
    )


def recolor_pixel(r: int, g: int, b: int, a: int) -> Tuple[int, int, int, int]:
    """Programmatically recolor a single RGBA pixel to authentic Jappa Ruby.

    :param r: Red channel value (0-255).
    :param g: Green channel value (0-255).
    :param b: Blue channel value (0-255).
    :param a: Alpha channel value (0-255).
    :return: Four-element tuple of recolored RGBA values.
    """
    if a < 10:
        return (r, g, b, a)

    if not is_diamond_pixel(r, g, b, a):
        return (r, g, b, a)

    min_dist = float("inf")
    best_match_idx = -1

    for idx, dia in enumerate(DIAMOND_PALETTE):
        dist = color_distance((r, g, b), dia)
        if dist < min_dist:
            min_dist = dist
            best_match_idx = idx

    if min_dist <= 18.0 and best_match_idx >= 0:
        rep = RUBY_PALETTE[best_match_idx]
        return (rep[0], rep[1], rep[2], a)

    relative_luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    ramp_color = interpolate_ruby_ramp(relative_luminance)
    return (ramp_color[0], ramp_color[1], ramp_color[2], a)
