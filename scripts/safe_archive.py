"""Safe ZIP extraction helpers.

Archive member names are untrusted input.  Extraction is constrained to the
requested destination and symbolic-link entries are rejected.
"""

from __future__ import annotations

from pathlib import Path
import os
import re
import stat
import zipfile


class UnsafeArchiveMember(ValueError):
    """Raised when a ZIP member would escape the extraction directory."""


def _safe_destination(root: Path, member_name: str) -> Path:
    # ZIP names use POSIX separators, but reject Windows-style traversal too.
    if not member_name or "\x00" in member_name:
        raise UnsafeArchiveMember(member_name)
    portable_name = member_name.replace("\\", "/")
    if portable_name.startswith("/") or re.match(r"^[A-Za-z]:", portable_name):
        raise UnsafeArchiveMember(member_name)
    if any(part == ".." for part in portable_name.split("/")):
        raise UnsafeArchiveMember(member_name)
    # Resolve before writing so symlinked parents and absolute names cannot escape.
    destination = (root / portable_name).resolve()
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise UnsafeArchiveMember(member_name) from exc
    return destination


def extract_zip_safe(archive: str | Path, destination: str | Path) -> list[Path]:
    """Extract *archive* below *destination*, rejecting Zip Slip entries."""
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            target = _safe_destination(root, info.filename)
            mode = (info.external_attr >> 16) & 0o170000
            if stat.S_ISLNK(mode):
                raise UnsafeArchiveMember(f"symbolic link: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            # Never follow a symlink that was already present in the destination.
            if os.path.lexists(target) and target.is_symlink():
                raise UnsafeArchiveMember(f"symbolic link: {info.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as source, target.open("wb") as sink:
                sink.write(source.read())
            extracted.append(target)
    return extracted
