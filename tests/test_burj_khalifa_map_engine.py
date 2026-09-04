"""Unit tests for Burj Khalifa 163-Floor Multi-Z Map Generation Engine.
Resolves Issue #643: [BOUNTY] [$1,500,000] [AGENTIC] / [Opire] Build the Burj Khalifa ingame.
Upstream Reference: Iamgoofball/-tg-station#150.
"""

import pytest
from scripts.burj_khalifa_map_engine import (
    BurjKhalifaMapEngine,
    BurjFloor,
    FloorTier,
)


@pytest.fixture
def map_engine():
    return BurjKhalifaMapEngine()


def test_total_163_z_levels_coverage(map_engine):
    assert len(map_engine.floors) == 163
    assert map_engine.TOTAL_HABITABLE_FLOORS == 154
    assert map_engine.TOTAL_SPIRE_LEVELS == 9
    assert map_engine.TOTAL_Z_LEVELS == 163

    # Lowest and highest floor checks
    assert 1 in map_engine.floors
    assert 163 in map_engine.floors
    assert map_engine.floors[1].tier == FloorTier.CONCOURSE_HOTEL
    assert map_engine.floors[163].tier == FloorTier.SPIRE_PINNACLE


def test_floor_categorization_and_amenities(map_engine):
    # Armani Hotel floor
    f1 = map_engine.floors[1]
    assert "Armani Hotel" in f1.name
    assert "Grand Ballroom" in f1.amenities

    # Mechanical Plant M1
    f10 = map_engine.floors[10]
    assert f10.tier == FloorTier.MECHANICAL_1
    assert "Substation Generators" in f10.amenities

    # At The Top Observatory
    f124 = map_engine.floors[124]
    assert f124.tier == FloorTier.OBSERVATORY
    assert f124.has_sky_deck is True
    assert "360 High-Power Telescopes" in f124.amenities

    # Spire level
    f160 = map_engine.floors[160]
    assert f160.tier == FloorTier.SPIRE_PINNACLE
    assert "Aircraft Beacon" in f160.amenities


def test_architectural_tapering(map_engine):
    # Lower floors are wider (32x32)
    assert map_engine.floors[20].width == 32
    assert map_engine.floors[20].height == 32

    # Mid floors taper (28x28, 24x24)
    assert map_engine.floors[60].width == 28
    assert map_engine.floors[100].width == 24

    # Upper residential/lounge taper (20x20)
    assert map_engine.floors[140].width == 20

    # Spire levels are narrow (14x14)
    assert map_engine.floors[160].width == 14
    assert map_engine.floors[160].height == 14


def test_express_elevator_transit_physics(map_engine):
    # Express trip from Ground (Z1) to At The Top (Z124)
    transit = map_engine.calculate_elevator_transit_time(start_z=1, dest_z=124)
    assert transit["floors_traversed"] == 123
    assert transit["distance_meters"] > 600.0  # > 600 meters vertical climb
    assert transit["velocity_mps"] == 10.0
    assert transit["transit_seconds"] > 60.0
    assert transit["status"] == "TRANSIT_COMPLETE"

    # Trip to same floor
    stay = map_engine.calculate_elevator_transit_time(start_z=50, dest_z=50)
    assert stay["floors_traversed"] == 0
    assert stay["transit_seconds"] == 0.0
    assert stay["status"] == "ARRIVED"


def test_tower_connectivity_validation(map_engine):
    report = map_engine.validate_complete_tower_connectivity()
    assert report["is_valid"] is True
    assert report["total_floors_verified"] == 163
    assert report["highest_z_level"] == 163
    assert len(report["missing_levels"]) == 0
    assert len(report["unconnected_elevators"]) == 0
    assert report["status"] == "TOWER_VALIDATED_COMPLIANT"


def test_dmm_floor_tilemap_generation(map_engine):
    floor_dmm = map_engine.generate_dmm_floor_tilemap(z=124)
    assert "BURJ KHALIFA Z-LEVEL 124" in floor_dmm
    assert "At The Top Public Observatory" in floor_dmm
    assert "W" in floor_dmm  # Glass wall perimeter
    assert "E" in floor_dmm  # Elevator core
    assert "D" in floor_dmm  # Sky Deck


def test_dreammaker_export_syntax(map_engine):
    dm = map_engine.export_dreammaker_code()
    assert "/area/burj_khalifa" in dm
    assert "/area/burj_khalifa/concourse" in dm
    assert "/area/burj_khalifa/observatory" in dm
    assert "/obj/machinery/elevator/burj_express" in dm
    assert "var/max_z = 163" in dm
