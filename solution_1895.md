# Fix for Issue #1895: Add `ShellDriverSh`: use `/bin/sh` when `SHELL` is not set

## Problem
In minimal environments (such as Docker containers or stripped POSIX servers) where `bash` is not installed:
1. When `SHELL` is not set, `_get_shell_driver` attempted to assume `bash` via `shutil.which("bash")` and triggered an `AssertionError` when `bash` was absent.
2. When `SHELL=/bin/sh`, `_get_shell_driver` raised `ValueError` because only `ShellDriverBash` and `ShellDriverZsh` were supported.

## Solution
1. **Implemented `ShellDriverSh`**:
   - Inherits from `ShellDriverBase` and provides pure POSIX compliance with no non-POSIX extensions (no `source`, `[[ ]]`, arrays, etc.).
   - Returns `ShellType.shell_sh` with `get_init_file_basename() -> ".shrc"`.
   - Uses `.` instead of `source` via `get_source_builtin()`.
   - Configures interactive shells by exporting the init file path in the `ENV` environment variable, matching standard POSIX `sh` initialization.
2. **Updated `get_shell_driver`**:
   - Fallback: when `SHELL` is not set, safely defaults to `/bin/sh` with `ShellDriverSh`.
   - Recognition: when `SHELL` basename is `sh`, returns `ShellDriverSh`.
   - Preserved `ValueError` for other unknown shells (e.g. `fish`).
3. **Comprehensive Unit Test Suite**:
   - 9 hermetic unit tests covering fallback, basename detection, POSIX builtin resolution, `ENV` variable assignment, and unknown shell rejection.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
