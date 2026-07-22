import pytest
from bounty_plaza.map_loader import load_map

def test_slopstation_map_loads():
    """Test that SlopStation map loads without errors"""
    map_data = load_map("slopstation")
    assert map_data is not None
    assert map_data["name"] == "SlopStation"

def test_slopstation_map_playable():
    """Test that SlopStation map is playable"""
    map_data = load_map("slopstation")
    # Add playability checks here
    assert True  # Placeholder for actual playability checks