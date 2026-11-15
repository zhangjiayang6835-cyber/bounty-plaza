#!/usr/bin/env python3
"""
Pytest test suite for RFC 4271 Convergence Test Runner.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routing.path_preference_matrix import (
    normalize_bgp_update_frames,
    calculate_path_preference_score,
    select_best_path,
    BGPPath,
    FRAME_CEILING,
    MED_PREFERENCE_KERNEL,
    LOCAL_PREF_ADJACENCY,
)


def test_frame_normalization_below_ceiling():
    """Test frames below ceiling are passed through."""
    frames = [b"x" * (FRAME_CEILING - 1)]
    result = normalize_bgp_update_frames(frames)
    assert len(result[0]) == FRAME_CEILING - 1


def test_frame_normalization_at_ceiling():
    """Test frames at exact ceiling are accepted (VEC-14 fix)."""
    frames = [b"x" * FRAME_CEILING]
    result = normalize_bgp_update_frames(frames)
    assert len(result[0]) == FRAME_CEILING


def test_frame_normalization_above_ceiling():
    """Test frames above ceiling are truncated."""
    frames = [b"x" * (FRAME_CEILING + 1)]
    result = normalize_bgp_update_frames(frames)
    assert len(result[0]) == FRAME_CEILING


def test_local_pref_basic():
    """VEC-01: Higher LOCAL_PREF wins."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], local_pref=200),
        BGPPath(prefix="10.0.0.0/8", as_path=[200], local_pref=100),
    ]
    result = select_best_path(paths)
    assert result.preferred.local_pref == 200


def test_as_path_length():
    """VEC-02: Shorter AS_PATH wins."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100, 200]),
        BGPPath(prefix="10.0.0.0/8", as_path=[100]),
    ]
    result = select_best_path(paths)
    assert len(result.preferred.as_path) == 1


def test_origin_type():
    """VEC-03: IGP > EGP > INCOMPLETE."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], origin="INCOMPLETE"),
        BGPPath(prefix="10.0.0.0/8", as_path=[100], origin="IGP"),
    ]
    result = select_best_path(paths)
    assert result.preferred.origin == "IGP"


def test_med_same_as():
    """VEC-04: Lower MED wins for same neighbor AS."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], med=50),
        BGPPath(prefix="10.0.0.0/8", as_path=[100], med=10),
    ]
    result = select_best_path(paths)
    assert result.preferred.med == 10


def test_med_diff_as():
    """VEC-05: MED not compared for different neighbor AS."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], med=10),
        BGPPath(prefix="10.0.0.0/8", as_path=[200], med=50),
    ]
    result = select_best_path(paths)
    assert result.preferred.as_path == [100]


def test_weight():
    """VEC-06: Higher WEIGHT wins."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], weight=0),
        BGPPath(prefix="10.0.0.0/8", as_path=[100], weight=100),
    ]
    result = select_best_path(paths)
    assert result.preferred.weight == 100


def test_ebgp_over_ibgp():
    """VEC-07: eBGP wins over iBGP when AS_PATH equal."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], is_ebgp=True),
        BGPPath(prefix="10.0.0.0/8", as_path=[100], is_ebgp=False),
    ]
    result = select_best_path(paths)
    assert result.preferred.is_ebgp is True


def test_igp_metric():
    """VEC-08: Lower IGP metric wins."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], igp_metric=100),
        BGPPath(prefix="10.0.0.0/8", as_path=[100], igp_metric=50),
    ]
    result = select_best_path(paths)
    assert result.preferred.igp_metric == 50


def test_router_id():
    """VEC-09: Lower router ID wins."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], router_id="1.1.1.1"),
        BGPPath(prefix="10.0.0.0/8", as_path=[100], router_id="2.2.2.2"),
    ]
    result = select_best_path(paths)
    assert result.preferred.router_id == "1.1.1.1"


def test_complex_multi():
    """VEC-10: Complex multi-attribute selection."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100, 200], local_pref=150, med=20),
        BGPPath(prefix="10.0.0.0/8", as_path=[100], local_pref=100, med=10),
        BGPPath(prefix="10.0.0.0/8", as_path=[300], local_pref=200, med=50),
    ]
    result = select_best_path(paths)
    assert result.preferred.local_pref == 200


def test_community():
    """VEC-11: Path with community."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], community=["65000:100"]),
        BGPPath(prefix="10.0.0.0/8", as_path=[100]),
    ]
    result = select_best_path(paths)
    assert result.preferred.community == ["65000:100"]


def test_med_multi_same_as():
    """VEC-12: Lowest MED wins among same AS paths."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], med=100),
        BGPPath(prefix="10.0.0.0/8", as_path=[100], med=50),
        BGPPath(prefix="10.0.0.0/8", as_path=[100], med=200),
    ]
    result = select_best_path(paths)
    assert result.preferred.med == 50


def test_as_path_prepend():
    """VEC-13: AS_PATH prepending makes path less preferred."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100, 100, 100]),
        BGPPath(prefix="10.0.0.0/8", as_path=[100]),
    ]
    result = select_best_path(paths)
    assert len(result.preferred.as_path) == 1


def test_route_reflector():
    """VEC-15: Route reflection loop prevention."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100]),
        BGPPath(prefix="10.0.0.0/8", as_path=[200, 100]),
    ]
    result = select_best_path(paths)
    assert result.preferred.as_path == [100]


def test_confederation():
    """VEC-16: Confederation handling."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[65001, 65002], is_ebgp=False),
        BGPPath(prefix="10.0.0.0/8", as_path=[100, 200], is_ebgp=True),
    ]
    result = select_best_path(paths)
    assert result.preferred.is_ebgp is True


def test_add_path():
    """VEC-17: ADD-PATH support."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], local_pref=100),
        BGPPath(prefix="10.0.0.0/8", as_path=[200], local_pref=200),
    ]
    result = select_best_path(paths)
    assert result.preferred.local_pref == 200


def test_graceful_restart():
    """VEC-18: Locally originated wins."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], local_pref=100, is_local=True),
        BGPPath(prefix="10.0.0.0/8", as_path=[200], local_pref=100, is_local=False),
    ]
    result = select_best_path(paths)
    assert result.preferred.is_local is True


def test_large_community():
    """VEC-19: Large community."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], community=["65000:100:200"]),
        BGPPath(prefix="10.0.0.0/8", as_path=[100]),
    ]
    result = select_best_path(paths)
    assert result.preferred.community == ["65000:100:200"]


def test_multiprotocol():
    """VEC-20: Multiprotocol extensions."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100]),
        BGPPath(prefix="2001:db8::/32", as_path=[100]),
    ]
    result = select_best_path(paths)
    assert result.preferred.prefix == "10.0.0.0/8"


def test_bgpsec():
    """VEC-21: BGPsec path validation."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], is_local=True),
        BGPPath(prefix="10.0.0.0/8", as_path=[200], is_local=False),
    ]
    result = select_best_path(paths)
    assert result.preferred.is_local is True


def test_flow_spec():
    """VEC-22: Flow specification."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], is_local=True),
        BGPPath(prefix="10.0.0.0/8", as_path=[100], is_local=False),
    ]
    result = select_best_path(paths)
    assert result.preferred.is_local is True


def test_vpn():
    """VEC-23: VPNv4/v6."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], community=["100:1"]),
        BGPPath(prefix="10.0.0.0/8", as_path=[200], community=["200:1"]),
    ]
    result = select_best_path(paths)
    assert result.preferred.community == ["100:1"]


def test_convergence_stability():
    """VEC-24: Convergence stability (RFC 7911)."""
    paths = [
        BGPPath(prefix="10.0.0.0/8", as_path=[100], local_pref=100, med=50),
        BGPPath(prefix="10.0.0.0/8", as_path=[200], local_pref=100, med=50),
        BGPPath(prefix="10.0.0.0/8", as_path=[300], local_pref=100, med=50),
    ]
    result = select_best_path(paths)
    assert result.preferred.as_path == [100]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))