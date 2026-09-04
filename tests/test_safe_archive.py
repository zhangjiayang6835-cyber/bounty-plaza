import zipfile

import pytest

from scripts.safe_archive import UnsafeArchiveMember, extract_zip_safe


def test_extracts_normal_members(tmp_path):
    archive = tmp_path / "input.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("nested/file.txt", "ok")
    output = tmp_path / "out"
    paths = extract_zip_safe(archive, output)
    assert (output / "nested/file.txt").read_text() == "ok"
    assert paths == [output / "nested/file.txt"]


@pytest.mark.parametrize("name", ["../../escape.txt", "/tmp/escape.txt", "a/../../escape.txt"])
def test_rejects_path_traversal(tmp_path, name):
    archive = tmp_path / "input.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(name, "blocked")
    with pytest.raises(UnsafeArchiveMember):
        extract_zip_safe(archive, tmp_path / "out")
    assert not (tmp_path / "escape.txt").exists()


def test_rejects_symlink_member(tmp_path):
    archive = tmp_path / "input.zip"
    info = zipfile.ZipInfo("link")
    info.external_attr = (0o120777 << 16) | 0xA000
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(info, "../../escape")
    with pytest.raises(UnsafeArchiveMember, match="symbolic link"):
        extract_zip_safe(archive, tmp_path / "out")
