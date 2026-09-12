"""Bedrock pack clean-slate build pipeline and asset compiler."""

import shutil
from pathlib import Path
from typing import Optional

from packages.bedrock_block_builder.builder import BlockFamilyBuilder
from packages.bedrock_block_builder.models import (
    BlockFamilyCatalog,
    BuildOptions,
    BuildResult,
    FamilyValidationError,
)


class BedrockBuildPipeline:
    """Orchestrates asset staging, catalog compilation, and clean-slate packaging."""

    def __init__(
        self,
        options: Optional[BuildOptions] = None,
        clean: Optional[bool] = None,
    ) -> None:
        """Initializes pipeline paths, flags, and catalog builder."""
        opts = options or BuildOptions()
        self.source_dir = Path(opts.source_dir).resolve()
        self.staging_base = Path(opts.staging_base).resolve()
        self.staging_dir = Path(opts.staging_dir).resolve()
        self.dest_dir = Path(opts.dest_dir).resolve()
        self.clean_slate = clean if clean is not None else opts.clean
        self.builder = BlockFamilyBuilder(options=opts)

    def clean(self) -> None:
        """Purges scratch and cache folders enforcing clean-slate invariant."""
        targets = [
            self.staging_base,
            self.source_dir.parent / "temp",
            self.source_dir.parent / ".cache",
        ]
        for target in targets:
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)

    def stage_pack(self) -> int:
        """Copies source pack files into staging directory preserving hierarchy."""
        if not self.source_dir.exists():
            return 0

        staged_count = 0
        for src_path in self.source_dir.rglob("*"):
            if src_path.is_file():
                rel_path = src_path.relative_to(self.source_dir)
                dest_path = self.staging_dir / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)
                staged_count += 1
        return staged_count

    def compile_block_families(self) -> BlockFamilyCatalog:
        """Deterministically generates block families catalog from staging."""
        catalog = self.builder.build_catalog(scan_dir=self.staging_dir)
        self.builder.export_catalog(catalog)
        return catalog

    def validate_recipe_book(self, catalog: BlockFamilyCatalog) -> list[str]:
        """Validates that all blocks in catalog possess valid recipe book categorization."""
        errors: list[str] = []
        for block_id, fam_name in catalog.block_to_family.items():
            fam = catalog.families.get(fam_name)
            if not fam:
                errors.append(f"Undefined block family reference: '{fam_name}' for '{block_id}'")
                continue
            cat_members = catalog.recipe_categories.get(fam.recipe_category.value, [])
            if block_id not in cat_members:
                errors.append(
                    f"Recipe book UI categorization failed: '{block_id}' "
                    f"missing from category '{fam.recipe_category.value}'"
                )
        return errors

    def deploy(self, catalog: BlockFamilyCatalog) -> int:
        """Deploys staged files and compiled catalog to destination directory."""
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        deployed_count = 0

        if self.staging_dir.exists():
            for src_path in self.staging_dir.rglob("*"):
                if src_path.is_file():
                    rel_path = src_path.relative_to(self.staging_dir)
                    dest_path = self.dest_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dest_path)
                    deployed_count += 1

        catalog_dest = self.dest_dir / "block_families.json"
        self.builder.export_catalog(catalog, catalog_dest)
        deployed_count += 1
        return deployed_count

    def run(self) -> BuildResult:
        """Executes full clean-slate build cycle, compilation, and validation."""
        if self.clean_slate:
            self.clean()

        staged_files = self.stage_pack()

        try:
            catalog = self.compile_block_families()
        except FamilyValidationError as exc:
            return BuildResult(
                success=False,
                catalog=None,
                staged_files=staged_files,
                errors=[exc.message],
                message=f"Build failed during family compilation: {exc.message}",
            )

        val_errors = self.validate_recipe_book(catalog)
        if val_errors:
            return BuildResult(
                success=False,
                catalog=catalog,
                staged_files=staged_files,
                errors=val_errors,
                message=f"Recipe book categorization failed: {len(val_errors)} errors detected.",
            )

        self.deploy(catalog)

        return BuildResult(
            success=True,
            catalog=catalog,
            staged_files=staged_files,
            errors=[],
            message="Clean-slate build completed successfully with verified block families.",
        )


def run_build(
    options: Optional[BuildOptions] = None,
    clean: Optional[bool] = None,
) -> BuildResult:
    """Convenience functional interface for executing the build pipeline."""
    pipeline = BedrockBuildPipeline(options=options, clean=clean)
    return pipeline.run()
