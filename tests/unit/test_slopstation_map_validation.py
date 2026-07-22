import pytest
from bounty_plaza.map_validator import validate_map

def test_slopstation_map_validation():
    """Test that SlopStation map meets validation criteria"""
    validation_result = validate_map("slopstation")
    assert validation_result["valid"] is True
    assert validation_result["errors"] == []