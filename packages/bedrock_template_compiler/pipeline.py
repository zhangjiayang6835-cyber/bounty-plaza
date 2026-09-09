"""Intermediate build pipeline with incremental compilation and source immutability."""

import hashlib
import json
import os
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple

from packages.bedrock_template_compiler.audio import compile_sound_definitions
from packages.bedrock_template_compiler.jsonte import JsonteCompiler, strip_json_comments
from packages.bedrock_template_compiler.models import BuildStats, CompilationResult


def calculate_file_hash(path: str) -> str:
    """Calculate SHA-256 hash of a file.

    Args:
        path: Path to target file.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def snapshot_directory_hashes(directory: str) -> Dict[str, str]:
    """Capture snapshot of all file hashes in a directory tree.

    Args:
        directory: Target directory path.

    Returns:
        Mapping of relative file paths to their SHA-256 digests.
    """
    snapshot: Dict[str, str] = {}
    if not os.path.isdir(directory):
        return snapshot

    for root, _, files in os.walk(directory):
        for filename in files:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, directory)
            snapshot[rel_path] = calculate_file_hash(full_path)
    return snapshot


def detect_template_dependencies(file_path: str) -> List[str]:
    """Inspect a template file and extract list of referenced $extend dependencies.

    Args:
        file_path: Path to template file.

    Returns:
        List of referenced template target paths or names.
    """
    dependencies: List[str] = []
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            raw = handle.read()
        clean = strip_json_comments(raw)
        data = json.loads(clean)
        if isinstance(data, dict):
            extend_val = data.get("$extend") or data.get("$template")
            if isinstance(extend_val, str):
                dependencies.append(extend_val)
            elif isinstance(extend_val, list):
                for item in extend_val:
                    if isinstance(item, str):
                        dependencies.append(item)
    except Exception:
        pass
    return dependencies


class BedrockBuildPipeline:
    """Intermediate build pipeline for Bedrock packs with incremental compilation."""

    def __init__(self, cache_file: Optional[str] = None) -> None:
        """Initialize pipeline with optional cache persistence.

        Args:
            cache_file: Optional path to save and load incremental cache data.
        """
        self.compiler = JsonteCompiler()
        self.cache_file = cache_file
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load persistent cache from disk if available."""
        if self.cache_file and os.path.isfile(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as handle:
                    self.cache = json.load(handle)
            except Exception:
                self.cache = {}

    def _save_cache(self) -> None:
        """Persist cache to disk if cache_file is configured."""
        if self.cache_file:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.cache_file)), exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as handle:
                    json.dump(self.cache, handle, indent=2)
            except Exception:
                pass

    def build_and_deploy(
        self,
        src_dir: str,
        dest_dir: str,
        force_rebuild: bool = False,
        global_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[BuildStats, List[CompilationResult]]:
        """Execute full intermediate build pipeline and deploy to destination.

        Args:
            src_dir: Source files directory.
            dest_dir: Destination game folder (e.g. com.mojang development pack).
            force_rebuild: If True, bypasses incremental cache.
            global_context: Optional global variables to inject into templates.

        Returns:
            Tuple of (BuildStats, list of CompilationResults).
        """
        start_time = time.time()
        stats = BuildStats()
        results: List[CompilationResult] = []

        if not os.path.isdir(src_dir):
            stats.duration_seconds = time.time() - start_time
            return stats, results

        pre_hashes = snapshot_directory_hashes(src_dir)
        os.makedirs(dest_dir, exist_ok=True)

        sounds_src_dir = os.path.join(src_dir, "sounds")
        has_sounds = os.path.isdir(sounds_src_dir)

        for root, _, files in os.walk(src_dir):
            for filename in sorted(files):
                stats.total_files += 1
                file_start = time.time()
                src_path = os.path.join(root, filename)
                rel_path = os.path.relpath(src_path, src_dir)

                target_rel_path = rel_path
                if filename.endswith(".jsonte"):
                    target_rel_path = rel_path[:-7] + ".json"

                dest_path = os.path.join(dest_dir, target_rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                current_hash = calculate_file_hash(src_path)
                cached_entry = self.cache.get(rel_path)

                is_clean = False
                if not force_rebuild and cached_entry and os.path.isfile(dest_path):
                    if cached_entry.get("hash") == current_hash:
                        deps_clean = True
                        for dep_rel in cached_entry.get("dependencies", []):
                            dep_full = os.path.join(src_dir, dep_rel)
                            if os.path.isfile(dep_full):
                                dep_hash = calculate_file_hash(dep_full)
                                if self.cache.get(dep_rel, {}).get("hash") != dep_hash:
                                    deps_clean = False
                                    break
                            else:
                                deps_clean = False
                                break
                        if deps_clean:
                            is_clean = True

                if is_clean:
                    stats.cached_files += 1
                    results.append(
                        CompilationResult(
                            source_path=src_path,
                            destination_path=dest_path,
                            success=True,
                            from_cache=True,
                            duration_ms=(time.time() - file_start) * 1000,
                        )
                    )
                    continue

                if filename.endswith(".jsonte") or (
                    filename.endswith(".json") and not filename.startswith("sound_definitions")
                ):
                    try:
                        with open(src_path, "r", encoding="utf-8") as handle:
                            content = handle.read()

                        is_template = (
                            filename.endswith(".jsonte")
                            or "$extend" in content
                            or "$template" in content
                            or "{{#" in content
                            or "{{" in content
                        )

                        if is_template:
                            compiled_json = self.compiler.compile_text(
                                content,
                                context=global_context,
                                base_dir=os.path.dirname(src_path),
                                file_path=src_path,
                            )
                            with open(dest_path, "w", encoding="utf-8") as out_handle:
                                out_handle.write(compiled_json)

                            stats.compiled_templates += 1
                            deps = detect_template_dependencies(src_path)
                            self.cache[rel_path] = {
                                "hash": current_hash,
                                "dependencies": deps,
                                "mtime": os.path.getmtime(src_path),
                            }
                            results.append(
                                CompilationResult(
                                    source_path=src_path,
                                    destination_path=dest_path,
                                    success=True,
                                    duration_ms=(time.time() - file_start) * 1000,
                                )
                            )
                        else:
                            shutil.copy2(src_path, dest_path)
                            stats.passthrough_files += 1
                            self.cache[rel_path] = {
                                "hash": current_hash,
                                "dependencies": [],
                                "mtime": os.path.getmtime(src_path),
                            }
                            results.append(
                                CompilationResult(
                                    source_path=src_path,
                                    destination_path=dest_path,
                                    success=True,
                                    duration_ms=(time.time() - file_start) * 1000,
                                )
                            )
                    except Exception as err:
                        stats.failed_files += 1
                        results.append(
                            CompilationResult(
                                source_path=src_path,
                                destination_path=dest_path,
                                success=False,
                                error=str(err),
                                duration_ms=(time.time() - file_start) * 1000,
                            )
                        )
                else:
                    shutil.copy2(src_path, dest_path)
                    stats.passthrough_files += 1
                    self.cache[rel_path] = {
                        "hash": current_hash,
                        "dependencies": [],
                        "mtime": os.path.getmtime(src_path),
                    }
                    results.append(
                        CompilationResult(
                            source_path=src_path,
                            destination_path=dest_path,
                            success=True,
                            duration_ms=(time.time() - file_start) * 1000,
                        )
                    )

        if has_sounds:
            audio_start = time.time()
            existing_def = os.path.join(src_dir, "sounds", "sound_definitions.json")
            compiled_sounds = compile_sound_definitions(
                sounds_dir=sounds_src_dir,
                existing_definitions_path=existing_def if os.path.isfile(existing_def) else None,
            )
            dest_sound_defs = os.path.join(dest_dir, "sounds", "sound_definitions.json")
            os.makedirs(os.path.dirname(dest_sound_defs), exist_ok=True)
            with open(dest_sound_defs, "w", encoding="utf-8") as sound_handle:
                json.dump(compiled_sounds, sound_handle, indent=2)

            stats.compiled_audio = len(compiled_sounds.get("sound_definitions", {}))
            results.append(
                CompilationResult(
                    source_path=sounds_src_dir,
                    destination_path=dest_sound_defs,
                    success=True,
                    duration_ms=(time.time() - audio_start) * 1000,
                )
            )

        post_hashes = snapshot_directory_hashes(src_dir)
        if pre_hashes != post_hashes:
            raise RuntimeError("Source directory was corrupted or modified during build pipeline execution!")

        self._save_cache()
        stats.duration_seconds = time.time() - start_time
        return stats, results
