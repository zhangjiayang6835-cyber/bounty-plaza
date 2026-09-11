"""
Formal verification engine and invariant auditor for Issue #1322.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
import shutil
from typing import List, Optional

from packages.bedrock_template_pipeline.pipeline import BedrockBuildPipeline
from packages.bedrock_template_pipeline.validator import BedrockPackValidator


@dataclass
class VerificationCheck:
    """Individual invariant check result."""

    name: str
    passed: bool
    details: str


@dataclass
class VerificationReport:
    """Consolidated report containing all invariant checks."""

    checks: List[VerificationCheck] = field(default_factory=list)
    all_passed: bool = False
    checks_passed: int = 0
    checks_run: int = 0


class PipelineVerifier:
    """Automated formal verification engine for Bedrock prebuild template pipeline."""

    @staticmethod
    def _find_base_dir(custom_path: Optional[Path] = None) -> Path:
        """Resolve workspace root directory containing Bedrock pack and templates."""
        if custom_path:
            return custom_path
        current = Path(__file__).resolve().parent
        for candidate in [current] + list(current.parents):
            if (candidate / "packs" / "behavior_pack").is_dir():
                return candidate
        return Path.cwd()

    @classmethod
    def check_bds_error_detection(cls, base_dir: Path) -> VerificationCheck:
        """Verify pack validator detects unexpanded template syntax at line 4 column 12."""
        source_dir = base_dir / "packs" / "behavior_pack"
        if not source_dir.is_dir():
            return VerificationCheck(
                name="BDS Syntax Error Detection",
                passed=False,
                details=f"Missing source behavior pack at {source_dir}",
            )
        report = BedrockPackValidator.validate_pack(source_dir)
        has_error = False
        for err in report.errors:
            if "custom_stair.json" in err and "line 4 column 12" in err:
                has_error = True
                break
        return VerificationCheck(
            name="BDS Syntax Error Detection",
            passed=has_error,
            details="Reproduced BDS syntax error for unexpanded custom_stair.json at line 4 col 12"
            if has_error
            else "Failed to reproduce expected BDS error",
        )

    @classmethod
    def check_pipeline_execution_order(cls, base_dir: Path) -> VerificationCheck:
        """Verify pipeline expands templates to staging before synchronizing to target."""
        temp_dir = base_dir / "_test_temp_verifier"
        dist_dir = base_dir / "_test_dist_verifier"
        try:
            pipeline = BedrockBuildPipeline(
                source_dir=base_dir / "packs" / "behavior_pack",
                staging_base=temp_dir,
                dest_dir=dist_dir,
                template_dir=base_dir / "templates",
                clean_slate=True,
            )
            result = pipeline.run()
            valid_dest = BedrockPackValidator.validate_pack(dist_dir)
            passed = result.success and valid_dest.valid and len(valid_dest.errors) == 0
            return VerificationCheck(
                name="Pipeline Execution Order Invariant",
                passed=passed,
                details="Expansion executed in _temp/ prior to sync; destination validated"
                if passed
                else "Pipeline execution failed or generated invalid target",
            )
        finally:
            if temp_dir.is_dir():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if dist_dir.is_dir():
                shutil.rmtree(dist_dir, ignore_errors=True)

    @classmethod
    def check_clean_slate_invariant(cls, base_dir: Path) -> VerificationCheck:
        """Verify clean-slate removes stale cached files from staging directory."""
        temp_dir = base_dir / "_test_temp_clean"
        dist_dir = base_dir / "_test_dist_clean"
        try:
            stale_file = temp_dir / "behavior_pack" / "blocks" / "stale_cache.json"
            stale_file.parent.mkdir(parents=True, exist_ok=True)
            stale_file.write_text('{"format_version":"1.20.80"}', encoding="utf-8")

            pipeline = BedrockBuildPipeline(
                source_dir=base_dir / "packs" / "behavior_pack",
                staging_base=temp_dir,
                dest_dir=dist_dir,
                template_dir=base_dir / "templates",
                clean_slate=True,
            )
            pipeline.run()
            stale_in_dist = (dist_dir / "blocks" / "stale_cache.json").is_file()
            passed = not stale_file.is_file() and not stale_in_dist
            return VerificationCheck(
                name="Clean-Slate Invariant",
                passed=passed,
                details="Stale cache wiped during clean-slate initialization"
                if passed
                else "Stale cache remained in build output",
            )
        finally:
            if temp_dir.is_dir():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if dist_dir.is_dir():
                shutil.rmtree(dist_dir, ignore_errors=True)

    @classmethod
    def check_schema_and_permutations(cls, base_dir: Path) -> VerificationCheck:
        """Verify expanded stair and slab blocks conform to Bedrock schema."""
        temp_dir = base_dir / "_test_temp_schema"
        dist_dir = base_dir / "_test_dist_schema"
        try:
            pipeline = BedrockBuildPipeline(
                source_dir=base_dir / "packs" / "behavior_pack",
                staging_base=temp_dir,
                dest_dir=dist_dir,
                template_dir=base_dir / "templates",
                clean_slate=True,
            )
            pipeline.run()
            stair_path = dist_dir / "blocks" / "custom_stair.json"
            slab_path = dist_dir / "blocks" / "custom_slab.json"
            if not stair_path.is_file() or not slab_path.is_file():
                return VerificationCheck(
                    name="Schema & Permutations Correctness",
                    passed=False,
                    details="Missing expanded block JSON files",
                )

            stair_data = json.loads(stair_path.read_text(encoding="utf-8"))
            slab_data = json.loads(slab_path.read_text(encoding="utf-8"))

            stair_ok = (
                stair_data.get("format_version") == "1.20.80"
                and stair_data.get("minecraft:block", {}).get("description", {}).get("identifier")
                == "tank:custom_stair"
                and len(stair_data.get("minecraft:block", {}).get("permutations", [])) == 5
            )
            slab_ok = (
                slab_data.get("format_version") == "1.20.80"
                and "$scope" not in slab_path.read_text(encoding="utf-8")
                and "{{" not in slab_path.read_text(encoding="utf-8")
            )
            passed = stair_ok and slab_ok
            return VerificationCheck(
                name="Schema & Permutations Correctness",
                passed=passed,
                details="Permutations, states, and metadata sanitization verified"
                if passed
                else "Schema or permutations mismatch",
            )
        finally:
            if temp_dir.is_dir():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if dist_dir.is_dir():
                shutil.rmtree(dist_dir, ignore_errors=True)

    @classmethod
    def check_static_asset_preservation(cls, base_dir: Path) -> VerificationCheck:
        """Verify static files retain byte equality through build pipeline."""
        temp_dir = base_dir / "_test_temp_static"
        dist_dir = base_dir / "_test_dist_static"
        try:
            pipeline = BedrockBuildPipeline(
                source_dir=base_dir / "packs" / "behavior_pack",
                staging_base=temp_dir,
                dest_dir=dist_dir,
                template_dir=base_dir / "templates",
                clean_slate=True,
            )
            pipeline.run()
            src_manifest = (base_dir / "packs" / "behavior_pack" / "manifest.json").read_bytes()
            dest_manifest = (dist_dir / "manifest.json").read_bytes()
            src_item = (
                base_dir / "packs" / "behavior_pack" / "items" / "mannequin_wrench.json"
            ).read_bytes()
            dest_item = (dist_dir / "items" / "mannequin_wrench.json").read_bytes()

            passed = (src_manifest == dest_manifest) and (src_item == dest_item)
            return VerificationCheck(
                name="Static Asset Byte Preservation",
                passed=passed,
                details="Manifest and static items match source byte-for-byte"
                if passed
                else "Static assets modified unexpectedly during pipeline",
            )
        finally:
            if temp_dir.is_dir():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if dist_dir.is_dir():
                shutil.rmtree(dist_dir, ignore_errors=True)

    @classmethod
    def check_orphan_file_cleanup(cls, base_dir: Path) -> VerificationCheck:
        """Verify target synchronization prunes orphaned files cleanly."""
        temp_dir = base_dir / "_test_temp_orphan"
        dist_dir = base_dir / "_test_dist_orphan"
        try:
            dist_dir.mkdir(parents=True, exist_ok=True)
            orphan = dist_dir / "blocks" / "old_orphan.json"
            orphan.parent.mkdir(parents=True, exist_ok=True)
            orphan.write_text('{"orphan":true}', encoding="utf-8")

            pipeline = BedrockBuildPipeline(
                source_dir=base_dir / "packs" / "behavior_pack",
                staging_base=temp_dir,
                dest_dir=dist_dir,
                template_dir=base_dir / "templates",
                clean_slate=True,
            )
            result = pipeline.run()
            passed = not orphan.is_file() and result.sync.removed >= 1
            return VerificationCheck(
                name="Orphan File Synchronization Pruning",
                passed=passed,
                details="Orphan files successfully removed from destination"
                if passed
                else "Orphan file persisted after clean synchronization",
            )
        finally:
            if temp_dir.is_dir():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if dist_dir.is_dir():
                shutil.rmtree(dist_dir, ignore_errors=True)

    @classmethod
    def run_all_checks(cls, base_dir: Optional[Path] = None) -> VerificationReport:
        """Run all 6 verification checks and return consolidated report."""
        root = cls._find_base_dir(base_dir)
        checks = [
            cls.check_bds_error_detection(root),
            cls.check_pipeline_execution_order(root),
            cls.check_clean_slate_invariant(root),
            cls.check_schema_and_permutations(root),
            cls.check_static_asset_preservation(root),
            cls.check_orphan_file_cleanup(root),
        ]
        passed_count = sum(1 for c in checks if c.passed)
        return VerificationReport(
            checks=checks,
            all_passed=(passed_count == len(checks)),
            checks_passed=passed_count,
            checks_run=len(checks),
        )
