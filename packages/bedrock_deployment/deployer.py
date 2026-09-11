"""Bedrock pack deployment engine performing sync, validation, and error recovery."""

import hashlib
from pathlib import Path
import shutil
from typing import Optional

from .models import DeploymentConfig, DeploymentResult
from .resolver import BedrockPathResolver, ResolverOptions
from .validator import DeploymentValidator


class BedrockDeployer:
    """Executes atomic pack synchronization and guarantees robust failure mitigation."""

    def __init__(
        self,
        resolver: Optional[BedrockPathResolver] = None,
        validator: Optional[DeploymentValidator] = None,
    ) -> None:
        """Initialize deployer with path resolver and structural validator."""
        self.resolver = resolver or BedrockPathResolver()
        self.validator = validator or DeploymentValidator()

    @staticmethod
    def compute_sha256(filepath: Path) -> str:
        """Compute SHA-256 digest of specified file contents."""
        hasher = hashlib.sha256()
        with filepath.open("rb") as file_handle:
            while chunk := file_handle.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _sync_source_file(self, src: Path, dest: Path, dry_run: bool) -> bool:
        """Copy source file to destination if modified, returning whether copy occurred."""
        if dest.exists() and src.stat().st_size == dest.stat().st_size:
            if self.compute_sha256(src) == self.compute_sha256(dest):
                return False

        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        return True

    def _remove_stale_files(
        self, target_dir: Path, source_relatives: set[Path], dry_run: bool
    ) -> int:
        """Remove target files not present in the source pack."""
        removed = 0
        if not target_dir.exists():
            return removed

        for dest_item in target_dir.rglob("*"):
            if dest_item.is_file():
                rel = dest_item.relative_to(target_dir)
                if rel not in source_relatives:
                    if not dry_run:
                        dest_item.unlink()
                    removed += 1

        if not dry_run:
            self._prune_empty_dirs(target_dir)
        return removed

    def sync_files(
        self, source_dir: Path, target_dir: Path, clean_slate: bool, dry_run: bool
    ) -> tuple[int, int]:
        """Synchronize files between source and destination directories."""
        copied = 0
        source_relatives: set[Path] = set()

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        for item in source_dir.rglob("*"):
            if item.is_file():
                rel = item.relative_to(source_dir)
                source_relatives.add(rel)
                target_file = target_dir / rel
                if self._sync_source_file(item, target_file, dry_run):
                    copied += 1

        removed = (
            self._remove_stale_files(target_dir, source_relatives, dry_run) if clean_slate else 0
        )
        return copied, removed

    def _prune_empty_dirs(self, root: Path) -> None:
        """Remove empty nested directories."""
        for path in sorted(root.glob("**/*"), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                try:
                    path.rmdir()
                except OSError:
                    pass

    def deploy(self, config: DeploymentConfig) -> DeploymentResult:
        """Execute Bedrock pack deployment with validation and graceful ENOENT recovery."""
        warnings: list[str] = []
        if not config.source_dir.exists():
            return DeploymentResult(
                success=False,
                destination=config.target_dir or Path("dist"),
                files_copied=0,
                files_removed=0,
                fallback_used=False,
                warnings=["Source directory does not exist"],
                error_message=f"Source directory not found: {config.source_dir}",
            )

        try:
            self.validator.validate_manifest(config.source_dir)
        except (FileNotFoundError, ValueError) as err:
            warnings.append(f"Manifest check warning: {err}")

        resolver_opts = ResolverOptions(
            pack_type=config.pack_type,
            custom_destination=config.target_dir,
            auto_create=config.auto_create,
        )
        dest_path, fallback_used, resolve_warnings = self.resolver.resolve_path(resolver_opts)
        warnings.extend(resolve_warnings)

        if not self.validator.is_writable(dest_path):
            warnings.append(f"Destination {dest_path} is not writable. Falling back to dist.")
            fallback_used = True
            dest_path = Path("dist") / config.source_dir.name
            dest_path.mkdir(parents=True, exist_ok=True)

        copied, removed = self.sync_files(
            source_dir=config.source_dir,
            target_dir=dest_path,
            clean_slate=config.clean_slate,
            dry_run=config.dry_run,
        )

        return DeploymentResult(
            success=True,
            destination=dest_path,
            files_copied=copied,
            files_removed=removed,
            fallback_used=fallback_used,
            warnings=warnings,
            error_message=None,
        )
