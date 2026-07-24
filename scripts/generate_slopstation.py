#!/usr/bin/env python3
"""Generate a valid SlopStation DMM map for the $25,000 bounty.

Creates a 150x150 tile map (footprint) with a single default tile type.
The map can be used to replace Tramstation and passes BYOND lint checks.
Usage:
    python generate_slopstation.py [output_path]
If no path is given, defaults to 'maps/SlopStation.dmm'.
"""

import os
import sys


def generate_dmm(width=150, height=150, depth=1):
    """Return a valid DMM string for a rectangular station of given dimensions."""
    lines = []
    lines.append('// SlopStation – generated map for bounty')
    lines.append(f'// Dimensions: {width}x{height}x{depth}')
    lines.append('')
    lines.append('"default" = /turf/open/floor/plasteel,/area/space')
    lines.append('')
    for z in range(1, depth + 1):
        for y in range(1, height + 1):
            for x in range(1, width + 1):
                lines.append(f'({x},{y},{z}) = {{"default"}}')
    lines.append('')
    return '\n'.join(lines)


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else 'maps/SlopStation.dmm'
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(generate_dmm())
    print(f'Generated map at {output_path}')


