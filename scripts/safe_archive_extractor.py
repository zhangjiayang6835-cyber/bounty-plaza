"""Safe Archive Extraction & Zip Slip Defense Engine.
Resolves Issue #292: Zip Slip -> Arbitrary File Write via Archive Extraction ($150 USD).

Implements:
1. Canonical path validation ensuring all extracted files reside strictly inside the target directory.
2. Proactive rejection of directory traversal sequences ('..', leading slashes, null bytes).
3. Symlink escape defenses preventing arbitrary symlink creation pointing outside target root.
4. Decompression quota checks to mitigate Zip Bomb denial-of-service vectors.
"""

import io
import os
import zipfile
from typing import List, Optional, Set, Union


class ArchiveSecurityError(ValueError):
    """Base exception for archive extraction security violations."""
    pass


class ZipSlipError(ArchiveSecurityError):
    """Raised when an archive member attempts directory traversal outside destination."""
    pass


class ZipBombError(ArchiveSecurityError):
    """Raised when an archive exceeds uncompressed size or compression ratio safety limits."""
    pass


class SafeArchiveExtractor:
    """Secure extraction manager defending against Zip Slip and archive-based RCE/file overwrite."""

    def __init__(
        self,
        max_total_uncompressed_bytes: int = 100 * 1024 * 1024,  # 100 MB max
        max_file_count: int = 10_000,
        max_compression_ratio: float = 100.0,
    ):
        self.max_total_uncompressed_bytes = max_total_uncompressed_bytes
        self.max_file_count = max_file_count
        self.max_compression_ratio = max_compression_ratio

    def validate_member_path(self, member_name: str, target_dir: str) -> str:
        """Validate and resolve member extraction path, enforcing destination boundaries.

        Args:
            member_name: The relative file path stored in the zip archive header.
            target_dir: The destination directory root.

        Returns:
            Resolved absolute canonical target file path.

        Raises:
            ZipSlipError: If path contains traversal sequences or escapes canonical target directory.
        """
        if not member_name:
            raise ZipSlipError("Archive member filename cannot be empty")

        if "\x00" in member_name:
            raise ZipSlipError("Null byte detected in archive member filename")

        # Normalize slashes
        normalized_name = member_name.replace("\\", "/")

        # Check for explicit traversal tokens
        path_parts = [p for p in normalized_name.split("/") if p]
        if ".." in path_parts or normalized_name.startswith("/"):
            raise ZipSlipError(
                f"Directory traversal sequence detected in member filename: '{member_name}'"
            )

        # Canonical path resolution
        canonical_target_dir = os.path.realpath(os.path.abspath(target_dir))
        candidate_path = os.path.abspath(os.path.join(canonical_target_dir, normalized_name))
        canonical_candidate_path = os.path.realpath(candidate_path)

        # Ensure destination path begins with target directory boundary
        expected_prefix = canonical_target_dir if canonical_target_dir.endswith(os.sep) else canonical_target_dir + os.sep
        if not (canonical_candidate_path == canonical_target_dir or canonical_candidate_path.startswith(expected_prefix)):
            raise ZipSlipError(
                f"Zip Slip detected: Extracted path '{canonical_candidate_path}' escapes target directory '{canonical_target_dir}'"
            )

        return candidate_path

    def extract(
        self,
        archive_file: Union[str, io.BytesIO, zipfile.ZipFile],
        target_dir: str,
        filter_extensions: Optional[Set[str]] = None,
    ) -> List[str]:
        """Safely extracts all archive members into target_dir.

        Args:
            archive_file: Path to zip file, file-like BytesIO object, or open ZipFile instance.
            target_dir: Destination directory.
            filter_extensions: Optional set of forbidden extensions.

        Returns:
            List of successfully extracted absolute file paths.
        """
        canonical_target_dir = os.path.realpath(os.path.abspath(target_dir))
        os.makedirs(canonical_target_dir, exist_ok=True)

        if isinstance(archive_file, zipfile.ZipFile):
            zf = archive_file
            should_close = False
        else:
            zf = zipfile.ZipFile(archive_file, "r")
            should_close = True

        extracted_files: List[str] = []
        try:
            infolist = zf.infolist()

            if len(infolist) > self.max_file_count:
                raise ZipBombError(
                    f"File count limit exceeded: {len(infolist)} files (max {self.max_file_count})"
                )

            total_uncompressed = 0
            for member in infolist:
                total_uncompressed += member.file_size
                if total_uncompressed > self.max_total_uncompressed_bytes:
                    raise ZipBombError(
                        f"Uncompressed archive size limit exceeded: {total_uncompressed} bytes "
                        f"(max {self.max_total_uncompressed_bytes})"
                    )

                if member.compress_size > 0:
                    ratio = member.file_size / member.compress_size
                    if ratio > self.max_compression_ratio:
                        raise ZipBombError(
                            f"Suspicious compression ratio {ratio:.1f} detected for '{member.filename}'"
                        )

            # Extract validated members
            for member in infolist:
                # Disallow symlinks to prevent symlink race traversal
                mode = member.external_attr >> 16
                if mode & 0o120000 == 0o120000:
                    raise ZipSlipError(f"Symlinks are prohibited in safe extraction mode: '{member.filename}'")

                dest_path = self.validate_member_path(member.filename, canonical_target_dir)

                if filter_extensions:
                    _, ext = os.path.splitext(dest_path)
                    if ext.lower() in filter_extensions:
                        continue

                if member.is_dir() or member.filename.endswith("/"):
                    os.makedirs(dest_path, exist_ok=True)
                    continue

                parent_dir = os.path.dirname(dest_path)
                os.makedirs(parent_dir, exist_ok=True)

                with zf.open(member) as source, open(dest_path, "wb") as target:
                    while chunk := source.read(65536):
                        target.write(chunk)

                extracted_files.append(dest_path)

            return extracted_files
        finally:
            if should_close:
                zf.close()
