"""Unit tests for SS13 Atmospherics Subsystem: Sparse Quadtrees (Issue #618).
Validates spatial decomposition, quadtree subdivision, homogenous node merging,
wall insertion, hull breach vacuum decompression, and DreamMaker patch syntax.
"""

import pytest
from scripts.ss13_sparse_quadtree_atmos import (
    GasMixture,
    QuadtreeBoundingBox,
    QuadtreeNode,
    SparseAtmosphericsQuadtree,
    IDEAL_GAS_CONSTANT_R,
    ONE_ATMOSPHERE_KPA,
    ROOM_TEMP_KELVIN,
)


def test_ideal_gas_law_calculation():
    # 100 moles in standard 2500L tile at 293.15 K
    gas = GasMixture(
        oxygen_mols=21.0,
        nitrogen_mols=79.0,
        volume_liters=2500.0,
        temperature_k=ROOM_TEMP_KELVIN,
    )
    # P = (n * R * T) / V_m3 = (100 * 8.314 * 293.15) / 2.5 = 243724.91 Pa = 97.49 kPa ~ 1 atm
    p = gas.pressure_kpa
    assert 90.0 < p < 105.0


def test_quadtree_subdivision_and_merge():
    bounds = QuadtreeBoundingBox(0, 0, 4)
    gas = GasMixture(volume_liters=2500.0 * 16)
    node = QuadtreeNode(bounds, gas)
    assert node.is_leaf is True
    assert node.count_leaves() == 1

    # Subdivide into 4 nodes of size 2
    success = node.subdivide()
    assert success is True
    assert node.is_leaf is False
    assert node.count_leaves() == 4

    # All children are homogenous, try merge
    merged = node.try_merge()
    assert merged is True
    assert node.is_leaf is True
    assert node.count_leaves() == 1


def test_sparse_quadtree_compression_efficiency():
    # 32x32 area has 1,024 naive cells. Initially, it's 1 single root quadtree node!
    tree = SparseAtmosphericsQuadtree(grid_size=32)
    assert tree.root.count_leaves() == 1

    # Add a wall at (15, 15) which requires single-tile precision
    tree.insert_wall(15, 15)
    leaf = tree.find_leaf(15, 15)
    assert leaf is not None
    assert leaf.has_structural_wall is True
    assert leaf.bounds.size == 1

    # Count leaves: 32 -> 16 -> 8 -> 4 -> 2 -> 1 subdivisions along the path
    # Even with subdivision, the total leaf count should be far less than 1,024
    leaf_count = tree.root.count_leaves()
    assert leaf_count < 100
    compression_pct = (1.0 - (leaf_count / 1024.0)) * 100.0
    assert compression_pct > 90.0  # Over 90% memory and compute reduction


def test_hull_breach_and_atmospheric_tick():
    tree = SparseAtmosphericsQuadtree(grid_size=16)  # 256 tiles
    # Hull breach at (5, 5)
    tree.trigger_hull_breach(5, 5)
    breach_node = tree.find_leaf(5, 5)
    assert breach_node is not None
    assert breach_node.gas.oxygen_mols == 0.0
    assert breach_node.gas.temperature_k == 2.7

    # Run atmospheric diffusion tick
    tick_res = tree.simulate_atmospheric_tick(delta_s=2.0)
    assert tick_res["status"] == "TICK_COMPLETED"
    assert tick_res["naive_cells_replaced"] == 256
    assert tick_res["compression_ratio_pct"] > 70.0


def test_bounding_box_intersection():
    b1 = QuadtreeBoundingBox(0, 0, 4)
    b2 = QuadtreeBoundingBox(2, 2, 4)
    b3 = QuadtreeBoundingBox(10, 10, 4)

    assert b1.intersects(b2) is True
    assert b1.intersects(b3) is False
    assert b1.contains(3, 3) is True
    assert b1.contains(4, 4) is False


def test_dreammaker_export():
    tree = SparseAtmosphericsQuadtree(grid_size=16)
    patch = tree.export_dreammaker_quadtree_patch()
    assert "/datum/quadtree_node" in patch
    assert "/datum/controller/subsystem/air/proc/process_sparse_quadtrees" in patch
    assert "Subdivide()" in patch
