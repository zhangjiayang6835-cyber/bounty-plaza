"""Unit tests for SS13 Global Real-World Wardrobe Omnibus Subsystem.
Resolves Issue #613: [BOUNTY] [UNCLAIMED] [FREE DOWNLOAD] [OPEN] [READY FOR AGENT] [$250 USD] add a feature, any feature at all.
"""

import pytest
from scripts.ss13_clothing_omnibus import (
    REAL_WORLD_CLOTHING_CATALOG,
    ClothingLayer,
    WardrobeOmnibusSynthesizer,
)


def test_catalog_breadth_and_completeness():
    # Verify comprehensive real-world catalog spans across all layers and continents
    catalog_size = len(REAL_WORLD_CLOTHING_CATALOG)
    assert catalog_size >= 70

    layers_covered = {item["layer"] for item in REAL_WORLD_CLOTHING_CATALOG.values()}
    # Assert every clothing layer is represented in the real world catalog
    for layer in ClothingLayer:
        assert layer in layers_covered


def test_self_referential_feature_requirement():
    synth = WardrobeOmnibusSynthesizer()
    # Explicitly verifies the feature references itself
    ref_data = synth.reference_itself()
    assert ref_data["self_linked"] is True
    assert synth.self_reference is synth
    assert "WardrobeOmnibusSynthesizer points to WardrobeOmnibusSynthesizer" in ref_data["recursive_check"]


def test_synthesize_apparel_success():
    synth = WardrobeOmnibusSynthesizer(energy_level_kwh=100.0)
    # Synthesize traditional Japanese kimono
    res_kimono = synth.synthesize_apparel("kimono", custom_color="cerulean")
    assert res_kimono["status"] == "FABRICATED"
    assert res_kimono["garment"]["fabric"] == "chirimen silk"
    assert res_kimono["garment"]["origin"] == "Japan"
    assert res_kimono["remaining_energy_kwh"] == 97.5

    # Synthesize Scottish kilt
    res_kilt = synth.synthesize_apparel("kilt", custom_color="royal_stewart")
    assert res_kilt["status"] == "FABRICATED"
    assert res_kilt["garment"]["origin"] == "Scotland"

    assert len(synth.synthesized_history) == 2


def test_synthesize_invalid_item():
    synth = WardrobeOmnibusSynthesizer()
    with pytest.raises(KeyError, match="not in the real-world wardrobe catalog"):
        synth.synthesize_apparel("cyberpunk_hyperdrive_pants_nonexistent")


def test_insufficient_energy():
    synth = WardrobeOmnibusSynthesizer(energy_level_kwh=1.0)
    with pytest.raises(RuntimeError, match="Insufficient synthesizer energy"):
        synth.synthesize_apparel("t_shirt")


def test_search_by_layer():
    synth = WardrobeOmnibusSynthesizer()
    headwear = synth.search_by_layer(ClothingLayer.HEAD)
    assert len(headwear) >= 10
    keys = [item[0] for item in headwear]
    assert "fedora" in keys
    assert "top_hat" in keys
    assert "beret" in keys
    assert "turban" in keys


def test_dreammaker_export():
    synth = WardrobeOmnibusSynthesizer()
    dm = synth.export_dreammaker_definitions()
    assert "/obj/machinery/wardrobe_omnibus_synthesizer" in dm
    assert "/obj/item/clothing/under/real_world" in dm
