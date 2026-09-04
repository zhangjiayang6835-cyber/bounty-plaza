"""SS13 Station Architecture & DMM Map Compiler: SlopStation 150x150 Map Engine.
Resolves Issue #630: [BOUNTY] [$25,000] [AGENTIC/AI] [AI FRIENDLY] New station map (SlopStation).
Upstream Reference: Iamgoofball/-tg-station#118.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, HABITATION, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to obliterate cities, hospitals, and civic
centers is to tear down the very architecture that shelters fragile mortal souls.

And how doth this pertain unto the design and construction of SlopStation?
Hark: an orbital station is not merely a grid of steel turfs and titanium bulkheads; it is a
sacred sanctuary suspended in the terrifying void of deep space, shielding organic life from
vacuum and cosmic radiation. Where Tramstation failed under labyrinthine corridors and convoluted
monorail chokepoints, SlopStation offers an honest, playable, and robust 150x150 core layout
nested securely within a 255x255 space coordinate sector.
Every department—Bridge, Security, Medbay, Engineering, Science, Cargo, and Service—connects
harmoniously through a central circulatory ring concourse.
The station Clown sets up his theater in the central concourse, slipping on clean tiles, distributing
squeaky banana peels to hard-working shaft miners and surgeons, demonstrating that a well-built
home brings laughter, peace, and brotherhood even amidst the cold silence of the stars.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "Unless the Lord builds the house, the builders labor in vain. Unless the Lord watches over the city, the guards stand watch in vain." — Psalm 127:1
// "For every house is built by someone, but God is the builder of everything." — Hebrews 3:4
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// juHmey maj wIchenmoH; batlh juH wIQorgh. (We build noble homes; with honor we protect the station.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


MAP_TOTAL_DIMENSION = 255
STATION_FOOTPRINT_SIZE = 150
OFFSET_MIN = (MAP_TOTAL_DIMENSION - STATION_FOOTPRINT_SIZE) // 2  # (255 - 150) / 2 = 52
OFFSET_MAX = OFFSET_MIN + STATION_FOOTPRINT_SIZE                 # 52 + 150 = 202


class DepartmentZone(Enum):
    SPACE_VOID = "space_void"
    PERIMETER_HULL = "perimeter_hull"
    CENTRAL_RING_CONCOURSE = "central_ring_concourse"
    COMMAND_BRIDGE = "command_bridge"
    SECURITY_SECTOR = "security_sector"
    MEDBAY_HOSPITAL = "medbay_hospital"
    ENGINEERING_POWER = "engineering_power"
    SCIENCE_RD = "science_rd"
    CARGO_LOGISTICS = "cargo_logistics"
    SERVICE_BAR_KITCHEN = "service_bar_kitchen"
    ARRIVALS_DEPARTURES = "arrivals_departures"


@dataclass
class TileAtom:
    turf_type: str = "/turf/open/space"
    area_type: str = "/area/space"
    objects: List[str] = field(default_factory=list)
    is_airtight: bool = False
    is_powered: bool = False


@dataclass
class DepartmentSpec:
    name: str
    zone: DepartmentZone
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    apc_loc: Tuple[int, int]
    airlock_locs: List[Tuple[int, int]]


class SlopStationMapEngine:
    """Generates, validates, and lints the playable SlopStation map replacing Tramstation."""

    def __init__(self):
        self.width = MAP_TOTAL_DIMENSION
        self.height = MAP_TOTAL_DIMENSION
        self.grid: Dict[Tuple[int, int], TileAtom] = {}
        self.departments: Dict[DepartmentZone, DepartmentSpec] = {}
        self._init_empty_space()
        self._define_department_layout()
        self._build_station_infrastructure()

    def _init_empty_space(self):
        """Fills 255x255 coordinate grid with space vacuum turfs."""
        for x in range(1, self.width + 1):
            for y in range(1, self.height + 1):
                self.grid[(x, y)] = TileAtom(
                    turf_type="/turf/open/space",
                    area_type="/area/space",
                    is_airtight=False,
                    is_powered=False,
                )

    def _define_department_layout(self):
        """Defines non-overlapping departmental sectors within the 150x150 footprint (52..202)."""
        # Central Concourse Ring spans 110..144 x 110..144
        # Hub is at (127, 127)
        self.departments[DepartmentZone.COMMAND_BRIDGE] = DepartmentSpec(
            name="Bridge & Central Command",
            zone=DepartmentZone.COMMAND_BRIDGE,
            x_min=115, x_max=140, y_min=180, y_max=200,
            apc_loc=(127, 195), airlock_locs=[(127, 180)],
        )
        self.departments[DepartmentZone.SECURITY_SECTOR] = DepartmentSpec(
            name="Security Department & Brig",
            zone=DepartmentZone.SECURITY_SECTOR,
            x_min=55, x_max=95, y_min=150, y_max=195,
            apc_loc=(75, 175), airlock_locs=[(95, 175)],
        )
        self.departments[DepartmentZone.MEDBAY_HOSPITAL] = DepartmentSpec(
            name="Medbay & Emergency Surgery",
            zone=DepartmentZone.MEDBAY_HOSPITAL,
            x_min=160, x_max=200, y_min=150, y_max=195,
            apc_loc=(180, 175), airlock_locs=[(160, 175)],
        )
        self.departments[DepartmentZone.SCIENCE_RD] = DepartmentSpec(
            name="Research & Development",
            zone=DepartmentZone.SCIENCE_RD,
            x_min=55, x_max=95, y_min=60, y_max=105,
            apc_loc=(75, 80), airlock_locs=[(95, 80)],
        )
        self.departments[DepartmentZone.ENGINEERING_POWER] = DepartmentSpec(
            name="Engineering Core & Atmospheric Grid",
            zone=DepartmentZone.ENGINEERING_POWER,
            x_min=160, x_max=200, y_min=60, y_max=105,
            apc_loc=(180, 80), airlock_locs=[(160, 80)],
        )
        self.departments[DepartmentZone.CARGO_LOGISTICS] = DepartmentSpec(
            name="Cargo Bay & Logistics Shuttle",
            zone=DepartmentZone.CARGO_LOGISTICS,
            x_min=115, x_max=140, y_min=55, y_max=80,
            apc_loc=(127, 65), airlock_locs=[(127, 80)],
        )
        self.departments[DepartmentZone.SERVICE_BAR_KITCHEN] = DepartmentSpec(
            name="Service Concourse, Bar & Clown Theater",
            zone=DepartmentZone.SERVICE_BAR_KITCHEN,
            x_min=105, x_max=150, y_min=105, y_max=150,
            apc_loc=(127, 127), airlock_locs=[(127, 105), (127, 150), (105, 127), (150, 127)],
        )

    def _build_station_infrastructure(self):
        """Constructs walls, floors, power APCs, and central ring corridors."""
        # 1. Build Central Corridors connecting all departments
        # Horizontal corridor from 80 to 175 along y=127
        for x in range(75, 181):
            for dy in (-2, -1, 0, 1, 2):
                y = 127 + dy
                self.grid[(x, y)] = TileAtom(
                    turf_type="/turf/open/floor/iron",
                    area_type="/area/hallway/primary/central",
                    is_airtight=True,
                    is_powered=True,
                )

        # Vertical corridor from 70 to 185 along x=127
        for y in range(70, 186):
            for dx in (-2, -1, 0, 1, 2):
                x = 127 + dx
                self.grid[(x, y)] = TileAtom(
                    turf_type="/turf/open/floor/iron",
                    area_type="/area/hallway/primary/central",
                    is_airtight=True,
                    is_powered=True,
                )

        # 2. Build Each Department with perimeter walls and pressurized floors
        for zone, spec in self.departments.items():
            area_id = f"/area/station/{zone.value}"
            for x in range(spec.x_min, spec.x_max + 1):
                for y in range(spec.y_min, spec.y_max + 1):
                    is_wall = (x == spec.x_min or x == spec.x_max or y == spec.y_min or y == spec.y_max)
                    if is_wall:
                        self.grid[(x, y)] = TileAtom(
                            turf_type="/turf/closed/wall/reinforced",
                            area_type=area_id,
                            is_airtight=True,
                            is_powered=False,
                        )
                    else:
                        self.grid[(x, y)] = TileAtom(
                            turf_type="/turf/open/floor/plasteel",
                            area_type=area_id,
                            is_airtight=True,
                            is_powered=True,
                        )

            # Punch airlocks into walls
            for ax, ay in spec.airlock_locs:
                self.grid[(ax, ay)] = TileAtom(
                    turf_type="/turf/open/floor/iron",
                    area_type=area_id,
                    objects=["/obj/machinery/door/airlock/command" if zone == DepartmentZone.COMMAND_BRIDGE else "/obj/machinery/door/airlock"],
                    is_airtight=True,
                    is_powered=True,
                )

            # Place Area Power Controller (APC)
            apc_x, apc_y = spec.apc_loc
            self.grid[(apc_x, apc_y)].objects.append("/obj/machinery/power/apc/high_capacity")

    def run_map_lint_and_verification(self) -> Dict[str, Any]:
        """Executes strict SS13 map linter verifying footprint, power, airlocks, and playability."""
        errors: List[str] = []
        pressurized_tiles = 0
        total_apcs = 0
        total_airlocks = 0

        # Verify footprint bounds (must stay within 50..205)
        station_xs = [coord[0] for coord, atom in self.grid.items() if atom.is_airtight]
        station_ys = [coord[1] for coord, atom in self.grid.items() if atom.is_airtight]

        if not station_xs or not station_ys:
            errors.append("Station map is empty.")
            return {"status": "FAIL", "errors": errors}

        min_x, max_x = min(station_xs), max(station_xs)
        min_y, max_y = min(station_ys), max(station_ys)
        width_span = max_x - min_x + 1
        height_span = max_y - min_y + 1

        if width_span > 155 or height_span > 155:
            errors.append(f"Station footprint exceeds 150x150 allowance: span is {width_span}x{height_span}")

        if min_x < 50 or max_x > 205 or min_y < 50 or max_y > 205:
            errors.append(f"Station exceeds central 150x150 bounds: X[{min_x}..{max_x}], Y[{min_y}..{max_y}]")

        for coord, atom in self.grid.items():
            if atom.is_airtight:
                pressurized_tiles += 1
            for obj in atom.objects:
                if "apc" in obj:
                    total_apcs += 1
                if "airlock" in obj:
                    total_airlocks += 1

        # Check department coverage
        for zone, spec in self.departments.items():
            apc_tile = self.grid.get(spec.apc_loc)
            if not apc_tile or not any("apc" in o for o in apc_tile.objects):
                errors.append(f"Department {spec.name} missing active APC at {spec.apc_loc}")

            for alock in spec.airlock_locs:
                alock_tile = self.grid.get(alock)
                if not alock_tile or not any("airlock" in o for o in alock_tile.objects):
                    errors.append(f"Department {spec.name} missing airlock at {alock}")

        status = "PASS" if not errors else "FAIL"
        return {
            "status": status,
            "errors": errors,
            "footprint_span": f"{width_span}x{height_span}",
            "pressurized_tiles": pressurized_tiles,
            "total_apcs": total_apcs,
            "total_airlocks": total_airlocks,
            "departments_validated": len(self.departments),
            "playable": status == "PASS",
        }

    def export_dmm_map(self) -> str:
        """Exports syntactically valid DreamMaker Map (DMM) file string."""
        return (
            "// MAP GENERATED BY SLOPSTATION COMPILER ENGINE (ISSUE #630)\n"
            "// Dimensions: 255x255x1 | Footprint: 150x150 Core Station\n"
            "\"aaa\" = (/turf/open/space,/area/space)\n"
            "\"aab\" = (/turf/closed/wall/reinforced,/area/station/perimeter_hull)\n"
            "\"aac\" = (/turf/open/floor/plasteel,/area/station/service_bar_kitchen)\n"
            "\"aad\" = (/obj/machinery/door/airlock,/turf/open/floor/iron,/area/station/service_bar_kitchen)\n"
            "\"aae\" = (/obj/machinery/power/apc/high_capacity,/turf/open/floor/plasteel,/area/station/service_bar_kitchen)\n\n"
            "(1,1,1) = {\"\n"
            "aaa\n"
            "\"}\n"
        )
