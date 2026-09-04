"""Atomic Temporary File & TOCTOU Race Condition Defense.
Resolves Issue #61: Race Condition in /tmp File Handling (TOCTOU) ($150 USD).
Enforces O_CREAT | O_EXCL | O_NOFOLLOW atomic file creation, strict 0600 POSIX permissions,
and process effective UID ownership verification.
"""

import os
import stat
import tempfile
from contextlib import contextmanager
from typing import Generator, IO, Optional, Union


class TempFileSecurityError(OSError):
    """Raised when temporary file security invariants (ownership, permissions, symlinks) are violated."""
    pass


def secure_open_exclusive(
    filepath: str,
    mode: int = 0o600
) -> int:
    """Atomically create and open a file exclusively.
    Uses O_CREAT | O_EXCL | O_NOFOLLOW to eliminate TOCTOU symlink interception races.

    Args:
        filepath: Target filesystem path.
        mode: Permission bits (default 0o600: user read/write only).

    Returns:
        int: Low-level file descriptor.

    Raises:
        FileExistsError: If the target path already exists.
        TempFileSecurityError: If ownership or security checks fail.
    """
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    # Open with explicit strict file mode
    fd = os.open(filepath, flags, mode)

    try:
        st = os.fstat(fd)
        # Verify ownership matches current effective UID
        if st.st_uid != os.geteuid():
            os.close(fd)
            raise TempFileSecurityError(
                f"Ownership validation failed: File UID {st.st_uid} does not match current EUID {os.geteuid()}"
            )

        # Verify strict permissions (no group or others access)
        actual_mode = stat.S_IMODE(st.st_mode)
        if actual_mode & 0o077 != 0:
            os.close(fd)
            raise TempFileSecurityError(
                f"Insecure permissions detected: Mode {oct(actual_mode)} exposes file to other users"
            )

        return fd
    except Exception:
        if os.path.exists(filepath):
            try:
                os.unlink(filepath)
            except OSError:
                pass
        raise


@contextmanager
def safe_named_temp_file(
    prefix: str = "bounty_tmp_",
    suffix: str = ".dat",
    dir: Optional[str] = None,
    mode: int = 0o600
) -> Generator[str, None, None]:
    """Secure context manager for temporary files using mkstemp with 0600 permissions.
    Automatically cleans up file upon context exit.

    Yields:
        str: Absolute path to the securely created temporary file.
    """
    target_dir = dir or tempfile.gettempdir()
    fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=target_dir)

    try:
        # Enforce strict 0600 permission
        os.fchmod(fd, mode)
        st = os.fstat(fd)
        if st.st_uid != os.geteuid():
            raise TempFileSecurityError(f"Owner mismatch on temp file: {temp_path}")
        os.close(fd)
        yield temp_path
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def atomic_write_file(
    target_path: str,
    data: Union[str, bytes],
    mode: int = 0o600
) -> None:
    """Atomically write data to target path using a sibling temporary file + atomic rename.
    Guarantees no half-written files and eliminates TOCTOU replacement window.

    Args:
        target_path: Destination file path.
        data: String or bytes to write.
        mode: Target file permissions.
    """
    abs_target = os.path.abspath(target_path)
    parent_dir = os.path.dirname(abs_target)

    # Use sibling temp file in the same directory for atomic filesystem rename
    fd, temp_path = tempfile.mkstemp(prefix=".tmp_atomic_", dir=parent_dir)
    try:
        os.fchmod(fd, mode)
        with open(fd, "wb", closefd=True) as f:
            if isinstance(data, str):
                f.write(data.encode("utf-8"))
            else:
                f.write(data)
            f.flush()
            os.fsync(f.fileno())

        # Atomic replacement on POSIX
        os.replace(temp_path, abs_target)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise
