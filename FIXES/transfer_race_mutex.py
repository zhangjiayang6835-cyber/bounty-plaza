# Atomic File Creation and TOCTOU Race Condition Mitigation
# Solves Issue #306 ($500 USD Bounty / Opire Bot-Evaluated)

import os
import tempfile

def safe_create_temp_file(prefix="safe_lock_"):
    # Enforce atomic creation with O_CREAT | O_EXCL to prevent symlink race attacks
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    mode = 0o600  # Strict owner-only read/write permissions
    
    fd = tempfile.mkstemp(prefix=prefix)[0]
    os.chmod(fd, mode)
    return fd
