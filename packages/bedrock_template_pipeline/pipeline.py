"""
Bedrock build pipeline orchestrator enforcing template expansion prior to deployment.
"""

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Union

from packages.bedrock_template_pipeline.expander import BedrockTemplateExpander
from packages.bedrock_template_pipeline.synchronizer import (
    DirectorySynchronizer,
    SyncStats,
)
from packages.bedrock_template_pipeline.validator import (
    BedrockPackValidator,
    ValidationReport,
)


@dataclass
class StagingStats:
    """Statistics recorded during staging and template expansion."""

    expanded_count: int = 0
    copied_count: int = 0


@dataclass
class BuildResult:
    """Consolidated summary of build pipeline execution."""

    success: bool
    staging: StagingStats
    validation: ValidationReport
    sync: SyncStats
    dest_dir: Path


class BedrockBuildPipeline:
    """Bedrock pack build and prebuild asset pipeline orchestrator."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        source_dir: Union[str, Path] = "packs/behavior_pack",
        staging_base: Union[str, Path] = "_temp",
        staging_dir: Optional[Union[str, Path]] = None,
        dest_dir: Union[str, Path] = "dist/behavior_pack",
        template_dir: Union[str, Path] = "templates",
        clean_slate: bool = True,
        default_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize build pipeline configuration and expander instance."""
        self.source_dir = Path(source_dir).resolve()
        self.staging_base = Path(staging_base).resolve()
        if staging_dir:
            self.staging_dir = Path(staging_dir).resolve()
        else:
            self.staging_dir = self.staging_base / "behavior_pack"
        self.dest_dir = Path(dest_dir).resolve()
        self.template_dir = Path(template_dir).resolve()
        self.clean_slate = clean_slate
        self.expander = BedrockTemplateExpander(
            template_dir=self.template_dir,
            default_context=default_context,
        )

    def clean(self) -> None:
        """Remove staging directory to enforce clean-slate invariant."""
        if self.staging_base.is_dir():
            shutil.rmtree(self.staging_base, ignore_errors=True)
        if self.staging_dir.is_dir():
            shutil.rmtree(self.staging_dir, ignore_errors=True)

    def stage_and_expand(self) -> StagingStats:
        """Expand templates into isolated staging directory prior to sync."""
        if not self.source_dir.is_dir():
            raise FileNotFoundError(f"Source pack directory not found: {self.source_dir}")

        self.staging_dir.mkdir(parents=True, exist_ok=True)
        expanded_count = 0
        copied_count = 0

        source_files: List[Path] = sorted(
            [p for p in self.source_dir.rglob("*") if p.is_file()]
        )

        for s_file in source_files:
            rel = s_file.relative_to(self.source_dir)
            target = self.staging_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)

            try:
                content = s_file.read_text(encoding="utf-8")
                is_text = True
            except UnicodeDecodeError:
                is_text = False
                content = ""

            if is_text and self.expander.is_template(content):
                expanded = self.expander.expand(content, str(rel))
                target.write_text(expanded, encoding="utf-8")
                expanded_count += 1
            else:
                shutil.copy2(s_file, target)
                copied_count += 1

        return StagingStats(expanded_count=expanded_count, copied_count=copied_count)

    def validate(self) -> ValidationReport:
        """Validate staged pack files prior to synchronization."""
        return BedrockPackValidator.validate_pack(self.staging_dir)

    def synchronize(self) -> SyncStats:
        """Synchronize validated staged pack files to destination."""
        return DirectorySynchronizer.synchronize(
            src_dir=self.staging_dir,
            dest_dir=self.dest_dir,
            clean=True,
        )

    def run(self) -> BuildResult:
        """Execute complete build pipeline workflow in deterministic order."""
        if self.clean_slate:
            self.clean()

        staging_stats = self.stage_and_expand()
        validation_report = self.validate()

        if not validation_report.valid:
            errors_str = "\n".join(validation_report.errors)
            raise ValueError(f"Pack validation failed in staging:\n{errors_str}")

        sync_stats = self.synchronize()

        return BuildResult(
            success=True,
            staging=staging_stats,
            validation=validation_report,
            sync=sync_stats,
            dest_dir=self.dest_dir,
        )
