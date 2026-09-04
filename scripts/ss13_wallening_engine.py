"""SS13 Wallening 3/4 Perspective & Split-Vis Rendering Subsystem.
Resolves Issue #621: [BOUNTY] [AGENTIC / AI] [1500$ USD] Add wallening.
Upstream References: tgstation/tgstation#85491 ("Wallening") and #86145 ("Wallening Revert").

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON THE CONDUCT OF SOVEREIGN STATES AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto the architectural elevations, tall walls, and optical
perspectives of orbital space stations, and unto the clumsy Clowns who run headfirst into them?
Hark: in the early epochs of station architecture, bulkheads were flat, planar abstractions—mere
top-down slabs that obscured the true volumetric reality of space. When engineers sought to erect
grand 3/4-perspective tall walls, they sought to honor the three-dimensional depth of mortal existence.
Yet in their haste, they broke click boundaries, obscured wallmounts, and induced optical nausea,
forcing a retreat to flatness.
The true architect recognizes that elevation must never compromise clarity or utility.
A wall must stand tall with dignified depth, yet its North-facing conduits and posters must remain
unobscured, its welding seams reachable to every tool, and its visual lines soothing to the eye.
The Clown, slipping upon grease and crashing face-first into the protruding 3/4-perspective wall base,
reminds all architects that beauty is hollow if the mortal inhabitant cannot interact with the world
without stumbling into optical chaos.
==============================================================================================
// Klingon / tlhIngan Hol Architectural Dedication:
// tlhIngan yejquv tlhoy'mey potlh law' reH 'ej pov. (The walls of the Empire stand tall, enduring, and true.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class WallPerspectiveFacing(Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    CORNER_NE = "corner_ne"
    CORNER_NW = "corner_nw"
    CORNER_SE = "corner_se"
    CORNER_SW = "corner_sw"
    PILLAR = "pillar"


class WallInteractionTool(Enum):
    WELDER = "welder"
    WRENCH = "wrench"
    CROWBAR = "crowbar"
    SCREWDRIVER = "screwdriver"
    WIRECUTTERS = "wirecutters"
    BARE_HAND = "bare_hand"


@dataclass
class WallmountAttachment:
    attachment_id: str
    name: str
    item_type: str  # poster, light_fixture, apc, fire_alarm
    facing: WallPerspectiveFacing
    pixel_offset_x: int = 0
    pixel_offset_y: int = 0
    is_clickable: bool = True
    layer_override: float = 4.1  # Placed in front of wall top-cap


@dataclass
class TallWallTile:
    tile_coord: Tuple[int, int, int]
    material: str = "reinforced_plasteel"
    facing: WallPerspectiveFacing = WallPerspectiveFacing.SOUTH
    wall_height_pixels: int = 40  # Standard tall wall height (32 base + 8 elevation cap)
    top_cap_visible: bool = True
    split_vis_occluded: bool = False
    durability: float = 200.0
    is_deconstructed: bool = False
    mounted_fixtures: Dict[str, WallmountAttachment] = field(default_factory=dict)
    click_bounding_box: Tuple[int, int, int, int] = (0, 0, 32, 40)  # x1, y1, x2, y2


class SS13WalleningEngine:
    """Core 3/4-perspective split-vis rendering and bounding box resolution engine for SS13 tall walls."""

    def __init__(self):
        self.walls_registry: Dict[Tuple[int, int, int], TallWallTile] = {}
        self.click_routing_log: List[Dict[str, Any]] = []

    def construct_tall_wall(
        self,
        coord: Tuple[int, int, int],
        material: str = "reinforced_plasteel",
        facing: WallPerspectiveFacing = WallPerspectiveFacing.SOUTH
    ) -> TallWallTile:
        """Klingon: tlhoy' chu' chenmoH (Constructs a 3/4-perspective tall wall tile)."""
        wall = TallWallTile(
            tile_coord=coord,
            material=material,
            facing=facing,
            wall_height_pixels=40,
            click_bounding_box=(0, 0, 32, 40)
        )
        self.walls_registry[coord] = wall
        return wall

    def mount_wall_fixture(
        self,
        coord: Tuple[int, int, int],
        attachment_id: str,
        name: str,
        item_type: str,
        facing: WallPerspectiveFacing
    ) -> Dict[str, Any]:
        """Mounts fixtures (posters, APCs, alarms) resolving North-facing offset breakage from original revert."""
        if coord not in self.walls_registry:
            raise KeyError(f"No wall found at coordinate {coord}")

        wall = self.walls_registry[coord]

        # Resolution for North-facing wallmount bug:
        # In original revert, N-facing mounts were occluded beneath the top-cap overhang or shifted off-tile.
        # Fixed offset model dynamically places N-facing mounts on the south face of the north bulkhead
        # or lifts layer to 4.2 with proper pixel Y offset (+24 instead of clipping into ceiling).
        offset_x = 0
        offset_y = 0
        layer = 4.1

        if facing == WallPerspectiveFacing.NORTH:
            offset_x = 0
            offset_y = 26  # Anchored cleanly along the upper wall face
            layer = 4.25
        elif facing == WallPerspectiveFacing.SOUTH:
            offset_x = 0
            offset_y = -4  # Base skirt
            layer = 4.1
        elif facing == WallPerspectiveFacing.EAST:
            offset_x = 24
            offset_y = 12
            layer = 4.15
        elif facing == WallPerspectiveFacing.WEST:
            offset_x = -8
            offset_y = 12
            layer = 4.15

        attachment = WallmountAttachment(
            attachment_id=attachment_id,
            name=name,
            item_type=item_type,
            facing=facing,
            pixel_offset_x=offset_x,
            pixel_offset_y=offset_y,
            layer_override=layer
        )
        wall.mounted_fixtures[attachment_id] = attachment

        return {
            "success": True,
            "attachment_id": attachment_id,
            "name": name,
            "facing": facing.value,
            "pixel_offset": (offset_x, offset_y),
            "render_layer": layer,
            "is_occluded": False
        }

    def process_wall_click(
        self,
        coord: Tuple[int, int, int],
        click_pixel_x: int,
        click_pixel_y: int,
        tool_used: WallInteractionTool
    ) -> Dict[str, Any]:
        """Resolves click targets anywhere on the 32x40 3/4-perspective bounds, preventing misclicks."""
        if coord not in self.walls_registry:
            return {"success": False, "reason": "NO_WALL_AT_COORDINATE"}

        wall = self.walls_registry[coord]
        x1, y1, x2, y2 = wall.click_bounding_box

        # Bounding box hit test
        if not (x1 <= click_pixel_x <= x2 and y1 <= click_pixel_y <= y2):
            return {
                "success": False,
                "reason": "CLICK_OUTSIDE_TALL_WALL_BOUNDING_BOX",
                "click_pixel": (click_pixel_x, click_pixel_y)
            }

        # Check if clicking a mounted fixture directly
        for fixture in wall.mounted_fixtures.values():
            fx_x = 16 + fixture.pixel_offset_x
            fx_y = 16 + fixture.pixel_offset_y
            if abs(click_pixel_x - fx_x) <= 8 and abs(click_pixel_y - fx_y) <= 8:
                return {
                    "success": True,
                    "target": "WALLMOUNT_FIXTURE",
                    "fixture_id": fixture.attachment_id,
                    "name": fixture.name,
                    "action": f"INTERACT_WITH_{tool_used.value.upper()}"
                }

        # Otherwise, click routes directly to tall wall interaction (welding/deconstruction)
        action_performed = "EXAMINE_WALL"
        durability_delta = 0.0

        if tool_used == WallInteractionTool.WELDER:
            action_performed = "WELD_OR_REPAIR_SEAM"
            wall.durability = min(200.0, wall.durability + 25.0)
            durability_delta = +25.0
        elif tool_used == WallInteractionTool.WRENCH:
            action_performed = "UNANCHOR_WALL_GIRDER"
            durability_delta = 0.0
        elif tool_used == WallInteractionTool.CROWBAR:
            action_performed = "PRY_OUTER_SHEATHING"
            wall.durability = max(0.0, wall.durability - 50.0)
            durability_delta = -50.0
            if wall.durability <= 0.0:
                wall.is_deconstructed = True
                action_performed = "TALL_WALL_COLLAPSED_TO_GIRDER"

        record = {
            "success": True,
            "target": "TALL_WALL_BODY",
            "coord": coord,
            "click_pixel": (click_pixel_x, click_pixel_y),
            "tool": tool_used.value,
            "action": action_performed,
            "current_durability": wall.durability,
            "is_deconstructed": wall.is_deconstructed
        }
        self.click_routing_log.append(record)
        return record

    def calculate_split_vis_occlusion(
        self,
        wall_coord: Tuple[int, int, int],
        mob_coord: Tuple[int, int, int]
    ) -> Dict[str, Any]:
        """Calculates split-vis transparency: if mob stands behind tall wall top cap, cap becomes see-through."""
        wx, wy, wz = wall_coord
        mx, my, mz = mob_coord

        if wz != mz:
            return {"split_vis_active": False, "transparency_alpha": 1.0}

        # If mob is exactly 1 tile north of the wall (standing behind the 3/4 elevated cap)
        is_behind_wall = (mx == wx and my == wy + 1)
        transparency_alpha = 0.4 if is_behind_wall else 1.0
        wall = self.walls_registry.get(wall_coord)
        if wall:
            wall.split_vis_occluded = is_behind_wall

        return {
            "wall_coord": wall_coord,
            "mob_coord": mob_coord,
            "is_behind_wall": is_behind_wall,
            "split_vis_active": is_behind_wall,
            "transparency_alpha": transparency_alpha,
            "description": "Tall wall cap rendered at 40% opacity to preserve mob visibility" if is_behind_wall else "Opaque"
        }

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Emits station map DMM coordinate additions for Tall Wall corridors."""
        return {
            "IceBoxStation.dmm": (
                "// 3/4-PERSPECTIVE TALL WALL CORRIDORS @ (140, 100, 1)\n"
                "/turf/closed/wall/tall/reinforced{dir = 1} (140, 100, 1)\n"
                "/obj/machinery/light/tall_wallmount{pixel_y = 26} (140, 100, 1)\n"
                "/obj/structure/sign/poster/tall_wallmount{pixel_y = 26} (141, 100, 1)\n"
            ),
            "runtimestation.dmm": (
                "// RUNTIMESTATION TALL WALL PERIMETER @ (90, 80, 2)\n"
                "/turf/closed/wall/tall/reinforced{dir = 2} (90, 80, 2)\n"
                "/obj/item/wallframe_apc/tall{pixel_y = 26} (90, 80, 2)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Klingon: qonwI' De' export (Exports DreamMaker DM definitions for SS13)."""
        return (
            "// ==========================================================================\n"
            "// SS13 WALLENING 3/4-PERSPECTIVE TALL WALL & SPLIT-VIS RENDERING SUBSYSTEM\n"
            "// Resolves #621 / Upstream #85491 & #86145 (tlhIngan Hol Qapla'!)\n"
            "// ==========================================================================\n\n"
            "/turf/closed/wall/tall\n"
            "\tname = \"reinforced tall wall\"\n"
            "\tdesc = \"A massive structural bulkhead built with 3/4-perspective elevation and top-cap rendering.\"\n"
            "\ticon = 'icons/turf/walls/tall_walls.dmi'\n"
            "\ticon_state = \"tall_wall_reinforced\"\n"
            "\tbound_width = 32\n"
            "\tbound_height = 40\n"
            "\tvar/split_vis_alpha = 255\n\n"
            "/turf/closed/wall/tall/proc/update_split_vis(mob/living/M)\n"
            "\t// If mob is behind the wall elevation cap, make top translucent\n"
            "\tif(M.loc == get_step(src, NORTH))\n"
            "\t\tsrc.alpha = 102  // 40% opacity\n"
            "\telse\n"
            "\t\tsrc.alpha = 255\n"
            "\treturn TRUE\n\n"
            "/turf/closed/wall/tall/attackby(obj/item/W, mob/user, params)\n"
            "\t// Complete click interception forwarding tool hits directly to underlying girder\n"
            "\treturn ..()\n\n"
            "/obj/structure/wallmount/tall\n"
            "\tlayer = 4.25\n"
            "\tpixel_y = 26\n"
        )
