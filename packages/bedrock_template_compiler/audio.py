"""Sound definitions and audio compilation pipeline for Bedrock resource packs."""

import json
import os
from typing import Any, Dict, List, Optional, Set

VALID_SOUND_CATEGORIES: Set[str] = {
    "ambient",
    "block",
    "bottle",
    "bucket",
    "hostile",
    "music",
    "neutral",
    "player",
    "record",
    "ui",
    "weather",
}

AUDIO_EXTENSIONS: Set[str] = {".ogg", ".wav", ".fsb"}


def derive_sound_category(rel_path: str) -> str:
    """Infer sound category from relative path folder hierarchy.

    Args:
        rel_path: Relative path of the audio file.

    Returns:
        Standard Bedrock sound category identifier.
    """
    normalized = rel_path.replace("\\", "/").lower()
    parts = normalized.split("/")

    for part in parts:
        if part in VALID_SOUND_CATEGORIES:
            return part

    if "block" in normalized or "tile" in normalized:
        return "block"
    if "music" in normalized or "bgm" in normalized:
        return "music"
    if "entity" in normalized or "mob" in normalized or "monster" in normalized:
        return "hostile"
    if "ui" in normalized or "gui" in normalized:
        return "ui"

    return "player"


def normalize_sound_reference(rel_path: str) -> str:
    """Normalize file path to Bedrock sound definition reference path without extension.

    Args:
        rel_path: Path to the audio file.

    Returns:
        Forward-slash normalized sound path without audio file extension.
    """
    normalized = rel_path.replace("\\", "/")
    root, ext = os.path.splitext(normalized)
    if ext.lower() in AUDIO_EXTENSIONS:
        return root
    return normalized


def compile_sound_definitions(
    sounds_dir: str,
    existing_definitions_path: Optional[str] = None,
    default_category: str = "player",
) -> Dict[str, Any]:
    """Scan audio assets and generate comprehensive Bedrock sound_definitions.json structure.

    Args:
        sounds_dir: Directory containing audio assets.
        existing_definitions_path: Optional path to an existing sound_definitions.json file.
        default_category: Fallback category if one cannot be inferred.

    Returns:
        Dictionary conforming to Bedrock sound_definitions.json schema.
    """
    base_definitions: Dict[str, Any] = {
        "format_version": "1.20.0",
        "sound_definitions": {},
    }

    if existing_definitions_path and os.path.isfile(existing_definitions_path):
        try:
            with open(existing_definitions_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
                if isinstance(loaded, dict):
                    base_definitions["format_version"] = loaded.get("format_version", "1.20.0")
                    sound_defs = loaded.get("sound_definitions", {})
                    base_definitions["sound_definitions"] = dict(sound_defs)
        except (json.JSONDecodeError, OSError):
            pass

    if not os.path.isdir(sounds_dir):
        return base_definitions

    events_map: Dict[str, List[str]] = {}
    categories_map: Dict[str, str] = {}

    for root, _, files in os.walk(sounds_dir):
        for filename in sorted(files):
            _, ext = os.path.splitext(filename)
            if ext.lower() not in AUDIO_EXTENSIONS:
                continue

            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, sounds_dir)
            ref_path = normalize_sound_reference(os.path.join("sounds", rel_path))

            rel_no_ext = normalize_sound_reference(rel_path)
            event_id = rel_no_ext.replace("/", ".").replace("\\", ".")

            if event_id.endswith("1") or event_id.endswith("2") or event_id.endswith("3"):
                base_event = event_id.rstrip("0123456789_")
                if base_event:
                    event_id = base_event

            if event_id not in events_map:
                events_map[event_id] = []
                categories_map[event_id] = derive_sound_category(rel_path)

            events_map[event_id].append(ref_path)

    for event_name, sound_refs in events_map.items():
        if event_name not in base_definitions["sound_definitions"]:
            category = categories_map.get(event_name, default_category)
            if category not in VALID_SOUND_CATEGORIES:
                category = default_category

            base_definitions["sound_definitions"][event_name] = {
                "category": category,
                "sounds": sorted(list(set(sound_refs))),
            }
        else:
            existing_entry = base_definitions["sound_definitions"][event_name]
            if isinstance(existing_entry, dict):
                current_sounds = existing_entry.get("sounds", [])
                if isinstance(current_sounds, list):
                    merged_sounds = list(current_sounds)
                    for ref in sound_refs:
                        if ref not in merged_sounds:
                            merged_sounds.append(ref)
                    existing_entry["sounds"] = merged_sounds

    return base_definitions
