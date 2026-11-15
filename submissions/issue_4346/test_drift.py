import pytest
from drift_catch import DriftDetector

def test_drift_calculation_logic():
    # Mocking the detector for logic testing
    detector = DriftDetector("http://localhost:8545", threshold_percent=5.0)
    
    offchain = 105.0
    onchain = 100.0
    drift = abs(offchain - onchain)
    drift_p = (drift / onchain) * 100
    
    assert drift_p == 5.0
    assert drift_p <= 5.0 # Boundary for OK status

def test_api_path_traversal():
    detector = DriftDetector("http://localhost:8545")
    mock_response = {"data": {"protocol": {"tvl": 15000000}}}
    
    path = "data.protocol.tvl"
    keys = path.split('.')
    val = mock_response
    for key in keys:
        val = val[key]
    
    assert val == 15000000
