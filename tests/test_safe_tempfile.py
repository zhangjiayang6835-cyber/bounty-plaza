import os
import stat
import pytest
from scripts.safe_tempfile import (
    secure_open_exclusive,
    safe_named_temp_file,
    atomic_write_file,
    TempFileSecurityError,
)


def test_secure_open_exclusive_creates_and_locks(tmp_path):
    target = str(tmp_path / "test_exclusive.lock")
    fd = secure_open_exclusive(target, mode=0o600)
    assert fd > 0

    # Verify mode is 0600
    st = os.fstat(fd)
    assert stat.S_IMODE(st.st_mode) == 0o600
    assert st.st_uid == os.geteuid()

    os.write(fd, b"locked\n")
    os.close(fd)

    # Calling secure_open_exclusive again on existing file must raise FileExistsError
    with pytest.raises(FileExistsError):
        secure_open_exclusive(target)


def test_safe_named_temp_file_lifecycle(tmp_path):
    temp_path_recorded = None
    with safe_named_temp_file(dir=str(tmp_path)) as temp_path:
        temp_path_recorded = temp_path
        assert os.path.exists(temp_path)
        st = os.stat(temp_path)
        assert stat.S_IMODE(st.st_mode) == 0o600
        assert st.st_uid == os.geteuid()
        with open(temp_path, "w") as f:
            f.write("temporary_token_payload")

    # File must be automatically unlinked after exiting context
    assert not os.path.exists(temp_path_recorded)


def test_atomic_write_file_replaces_cleanly(tmp_path):
    target = tmp_path / "config.json"
    target.write_text('{"initial": true}')

    atomic_write_file(str(target), '{"updated": true, "atomic": true}', mode=0o600)

    assert target.read_text() == '{"updated": true, "atomic": true}'
    st = os.stat(str(target))
    assert stat.S_IMODE(st.st_mode) == 0o600
