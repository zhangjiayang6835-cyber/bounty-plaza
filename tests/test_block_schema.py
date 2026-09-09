# tests/test_block_schema.py
import json
import os

def test_compressed_basalt_schema():
    bp_path = os.path.join(os.path.dirname(__file__), "..", "BP", "blocks", "compressed_basalt.json")
    with open(bp_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    desc = data["minecraft:block"]["description"]
    assert "sound" not in desc, "sound property is prohibited inside description under format_version 1.26.30"
    assert desc["identifier"] == "custom:compressed_basalt"

def test_rp_sound_definition():
    rp_path = os.path.join(os.path.dirname(__file__), "..", "RP", "blocks.json")
    with open(rp_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "custom:compressed_basalt" in data
    assert data["custom:compressed_basalt"]["sound"] == "stone"
