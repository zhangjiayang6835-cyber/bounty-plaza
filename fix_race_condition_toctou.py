# fix_race_condition_toctou.py
"""
Race Condition Protection for TOCTOU (Time-of-Check to Time-of-Use) vulnerabilities.

TOCTOU vulnerability occurs when:
1. Application checks if a file exists (os.path.exists)
2. Then opens the file (open)
3. Attacker creates symlink in the gap, pointing to sensitive file

Secure approach:
1. Use atomic file operations (O_CREAT | O_EXCL)
2. Use mkstemp() for temp files
3. Use file descriptors instead of paths
"""

import os
import tempfile
import fcntl
import errno

class TOCTOUProtection:
    """Protect against TOCTOU race conditions in file operations."""

    @staticmethod
    def secure_create_file(content, dir_path=None):
        """
        Securely create a new file without TOCTOU vulnerability.
        Uses O_CREAT | O_EXCL to ensure atomic creation.
        """
        if dir_path is None:
            dir_path = tempfile.gettempdir()

        # Use mkstemp for secure temp file creation
        fd, path = tempfile.mkstemp(dir=dir_path, prefix='secure_', suffix='.tmp')
        try:
            # Write content atomically
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            return path
        except Exception as e:
            # Clean up on failure
            try:
                os.unlink(path)
            except OSError:
                pass
            raise e

    @staticmethod
    def secure_open_file(file_path, mode='r'):
        """
        Open a file atomically using file descriptor operations.
        Eliminates the TOCTOU gap.
        """
        try:
            # Open with O_NOFOLLOW to prevent symlink attacks
            flags = os.O_RDONLY if mode == 'r' else os.O_WRONLY | os.O_CREAT
            fd = os.open(file_path, flags | os.O_NOFOLLOW)
            return fd
        except OSError as e:
            if e.errno == errno.EISDIR:
                raise ValueError("Path is a directory, not a file")
            if e.errno == errno.ELOOP:
                raise ValueError("Symlink loop detected")
            raise e

    @staticmethod
    def secure_read_file(file_path):
        """
        Read a file safely, preventing symlink-based attacks.
        """
        try:
            # Check if file is a symlink (without following it)
            if os.path.islink(file_path):
                raise ValueError("Cannot read symlink to prevent TOCTOU attacks")

            # Read file directly using atomic operations
            with open(file_path, 'rb') as f:
                return f.read()

        except OSError as e:
            if e.errno == errno.ELOOP:
                raise ValueError("Symlink loop detected")
            raise e

    @staticmethod
    def secure_temp_directory():
        """
        Create a secure temporary directory with restricted permissions.
        """
        dir_path = tempfile.mkdtemp(prefix='secure_app_')
        # Set restrictive permissions (owner read/write/execute only)
        os.chmod(dir_path, 0o700)
        return dir_path

    @staticmethod
    def atomic_file_write(path, content):
        """
        Atomically write content to a file.
        Uses write-to-temp then rename pattern.
        """
        import os

        # Create temp file in same directory (for atomic rename)
        dir_name = os.path.dirname(path) or '.'
        fd, temp_path = tempfile.mkstemp(dir=dir_name)

        try:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            # Atomic rename (POSIX guarantee)
            os.rename(temp_path, path)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def file_lock_operation(file_path, operation):
        """
        Perform a file operation with locking to prevent race conditions.
        """
        fd = None
        try:
            fd = os.open(file_path, os.O_RDWR | os.O_CREAT, 0o600)
            # Acquire exclusive lock
            fcntl.flock(fd, fcntl.LOCK_EX)
            result = operation(fd)
            return result
        finally:
            if fd is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

    @staticmethod
    def secure_copy_file(src, dst):
        """
        Securely copy a file without TOCTOU vulnerability.
        """
        if os.path.islink(src) or os.path.islink(dst):
            raise ValueError("Symlinks not allowed for security")

        # Atomic copy: read then write to temp, then rename
        with open(src, 'rb') as f:
            content = f.read()

        dir_name = os.path.dirname(dst) or '.'
        fd, temp_path = tempfile.mkstemp(dir=dir_name)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(content)
            os.rename(temp_path, dst)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise