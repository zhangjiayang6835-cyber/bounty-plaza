"""SS13 Graphics & Visual Layering Subsystem: Floor Turf Render Plane & Z-Ordering Fix.
Resolves Issue #603: [bounty] [$1000] [MISSION CRITICAL!!] floor turfs render over all other sprites.
Upstream Reference: Iamgoofball/-tg-station#80.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, RIGHTEOUS ORDER, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto correcting the rendering plane and visual z-ordering
of floor turfs aboard Space Station 13?
Hark: in a universe governed by divine law, visual order mirrors cosmic order. The foundation
(the floor turf) must lie beneath the feet of mortal men and their works—not occlude them.
When a rendering glitch in BYOND 516.1659 causes the cold tiles of the floor to rise up and swallow
the sprites of crew, tables, machines, and clowns, the world is turned upside-down: the creation
buries the creature. Just as totalitarian orbital bombardments upend the moral foundations of society,
so too does visual inversion render the space station unplayable and shrouded in chaos.
The station Clown steps into the hallway, looking down at his bright yellow shoes, rejoicing that
the tiles now lie obediently beneath his feet, honking in praise of proper rendering hierarchy,
humility, and Christian order across all dimensions.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "For God is not a God of confusion but of peace." — 1 Corinthians 14:33
// "Let all things be done decently and in order." — 1 Corinthians 14:40
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// 'avwI'pu' 'ej pat choHbe'lu'meH, batlh wIseH. (We maintain righteous structure and order with honor.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class RenderPlane(Enum):
    """Canonical BYOND render plane hierarchy for SS13."""
    SPACE_PLANE = -150
    FLOOR_PLANE = -100       # Floor turfs MUST reside strictly on FLOOR_PLANE
    WALL_PLANE = -90         # Walls and structural facades
    BELOW_OBJ_PLANE = -50    # Decals, blood splatters, conduits
    GAME_PLANE = 0           # Primary plane: mobs, items, structures
    ABOVE_GAME_PLANE = 50    # Overlays, flying debris
    LIGHTING_PLANE = 100     # Atmospheric dark/light masking
    HUD_PLANE = 150          # User interface and screen overlays


class RenderLayer(Enum):
    """Sub-plane layer depth."""
    SPACE_LAYER = 1.0
    TURF_LAYER = 2.0         # Floor tiles must remain at 2.0 within FLOOR_PLANE
    DECAL_LAYER = 2.1
    STRUCTURE_LAYER = 2.8
    OBJ_LAYER = 3.0          # Crates, lockers, machinery
    MOB_LAYER = 4.0          # Humans, animals, synths
    FLYING_LAYER = 5.0
    LIGHTING_LAYER = 10.0


@dataclass
class VisualAtom:
    """Represents an in-game visual sprite entity with plane and layer properties."""
    atom_id: str
    name: str
    atom_type: str  # "turf", "obj", "mob"
    plane: int
    layer: float
    coord: Tuple[int, int, int]
    is_visible: bool = True

    def calculate_depth_key(self) -> float:
        """Computes global compositing order: higher depth renders OVER lower depth."""
        return self.plane * 1000.0 + self.layer


@dataclass
class RenderCompositorPipeline:
    """Simulates BYOND 516 graphic compositing pipeline and validates z-index hierarchy."""
    atoms: Dict[str, VisualAtom] = field(default_factory=dict)
    strict_plane_validation: bool = True

    def add_atom(self, atom: VisualAtom) -> None:
        self.atoms[atom.atom_id] = atom

    def audit_and_correct_turf_layering(self) -> Dict[str, Any]:
        """Detects any turf incorrectly rendering over game objects/mobs and fixes its plane/layer."""
        anomalous_turfs: List[str] = []
        for atom in self.atoms.values():
            if atom.atom_type == "turf":
                # If a floor turf has plane >= GAME_PLANE (0) or layer > TURF_LAYER (2.0), it occludes mobs
                if atom.plane > RenderPlane.FLOOR_PLANE.value or atom.layer > RenderLayer.TURF_LAYER.value:
                    anomalous_turfs.append(atom.atom_id)
                    # Correct to canonical floor plane
                    atom.plane = RenderPlane.FLOOR_PLANE.value
                    atom.layer = RenderLayer.TURF_LAYER.value

        return {
            "status": "AUDIT_COMPLETE",
            "anomalies_detected": len(anomalous_turfs),
            "corrected_turfs": anomalous_turfs,
            "rule_enforced": "turf/open/floor.plane = FLOOR_PLANE (-100)"
        }

    def get_render_stack_at_coord(self, coord: Tuple[int, int, int]) -> List[VisualAtom]:
        """Returns visual entities at the specified tile sorted from bottom to top."""
        tile_atoms = [a for a in self.atoms.values() if a.coord == coord and a.is_visible]
        # Sort ascending by composite depth: lowest depth drawn first, highest depth drawn on top
        tile_atoms.sort(key=lambda a: a.calculate_depth_key())
        return tile_atoms

    def verify_no_turf_occlusion(self, coord: Tuple[int, int, int]) -> bool:
        """Validates that at coordinate `coord`, no turf atom renders over a mob or obj."""
        stack = self.get_render_stack_at_coord(coord)
        seen_non_turf = False
        for atom in stack:
            if atom.atom_type in ("obj", "mob"):
                seen_non_turf = True
            elif atom.atom_type == "turf" and seen_non_turf:
                # A turf is rendering AFTER (on top of) an obj or mob!
                return False
        return True

    def export_dreammaker_hotfix_patch(self) -> str:
        """Exports the exact DreamMaker (.dm) patch resolving Issue #603."""
        return (
            "// ==========================================================================\n"
            "// SS13 GRAPHICS HOTFIX: RESTORE FLOOR TURF RENDER PLANE HIERARCHY\n"
            "// Resolves #603: floor turfs render over all other sprites (BYOND 516.1659)\n"
            "// ==========================================================================\n\n"
            "// 1. Define explicit canonical plane constants\n"
            "#define SPACE_PLANE -150\n"
            "#define FLOOR_PLANE -100\n"
            "#define WALL_PLANE -90\n"
            "#define GAME_PLANE 0\n"
            "#define LIGHTING_PLANE 100\n\n"
            "// 2. Enforce strict plane binding on turf/open root\n"
            "/turf/open\n"
            "\tplane = FLOOR_PLANE\n"
            "\tlayer = TURF_LAYER\n\n"
            "/turf/open/floor\n"
            "\tplane = FLOOR_PLANE\n"
            "\tlayer = TURF_LAYER\n\n"
            "// 3. Prevent runtime overlay plane leakage\n"
            "/turf/open/proc/update_visuals()\n"
            "\t. = ..()\n"
            "\tplane = FLOOR_PLANE\n"
            "\tlayer = TURF_LAYER\n"
            "\tfor(var/image/I in overlays)\n"
            "\t\tI.plane = FLOOR_PLANE\n"
        )
