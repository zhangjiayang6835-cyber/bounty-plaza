import enum
import os
import shutil
import logging
from typing import Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class ShellType(enum.Enum):
    shell_bash = "bash"
    shell_zsh = "zsh"
    shell_sh = "sh"


class ShellDriverBase:
    def __init__(
        self,
        shell_abs_path: str,
        shell_env_vars: Optional[Dict[str, str]] = None,
        cache_dir_abs_path: str = "/tmp/cache",
    ) -> None:
        self.shell_abs_path = shell_abs_path
        self.shell_env_vars = shell_env_vars if shell_env_vars is not None else {}
        self.cache_dir_abs_path = cache_dir_abs_path
        self.shell_args: List[str] = [shell_abs_path]

    def get_type(self) -> ShellType:
        raise NotImplementedError

    def get_init_file_basename(self) -> str:
        raise NotImplementedError

    def get_init_file_abs_path(self) -> str:
        return f"{self.cache_dir_abs_path}/{self.get_type().value}/{self.get_init_file_basename()}"

    def get_source_builtin(self) -> str:
        return "source"

    def configure_interactive_shell(self, has_command: bool) -> None:
        pass


class ShellDriverBash(ShellDriverBase):
    def get_type(self) -> ShellType:
        return ShellType.shell_bash

    def get_init_file_basename(self) -> str:
        return ".bashrc"

    def get_source_builtin(self) -> str:
        return "source"

    def configure_interactive_shell(self, has_command: bool) -> None:
        self.shell_args.extend(["--init-file", self.get_init_file_abs_path()])


class ShellDriverZsh(ShellDriverBase):
    def get_type(self) -> ShellType:
        return ShellType.shell_zsh

    def get_init_file_basename(self) -> str:
        return ".zshrc"

    def get_source_builtin(self) -> str:
        return "source"

    def configure_interactive_shell(self, has_command: bool) -> None:
        self.shell_env_vars["ZDOTDIR"] = f"{self.cache_dir_abs_path}/zsh"


class ShellDriverSh(ShellDriverBase):
    """
    Drives any POSIX `sh` implementation (dash, busybox ash, bash in sh mode, etc.):
    strictly adheres to POSIX standards with no non-POSIX extensions.
    """

    def get_type(self) -> ShellType:
        return ShellType.shell_sh

    def get_init_file_basename(self) -> str:
        return ".shrc"

    def get_source_builtin(self) -> str:
        # POSIX sh has no `source` builtin: it uses `.` to source files
        return "."

    def configure_interactive_shell(self, has_command: bool) -> None:
        # POSIX sh has no `--init-file` flag:
        # an interactive sh reads the file named by the `ENV` environment variable
        self.shell_env_vars["ENV"] = self.get_init_file_abs_path()


def get_shell_driver(
    cache_dir_abs_path: str = "/tmp/cache",
    activate_venv: bool = True,
) -> ShellDriverBase:
    """
    Resolves the appropriate shell driver based on the SHELL environment variable.
    - If SHELL is not set: logs warning and falls back to /bin/sh with ShellDriverSh.
    - If SHELL basename is 'bash': returns ShellDriverBash.
    - If SHELL basename is 'zsh': returns ShellDriverZsh.
    - If SHELL basename is 'sh': returns ShellDriverSh.
    - Any other unknown shell raises ValueError.
    """
    var_shell = "SHELL"
    shell_abs_path: Optional[str] = os.environ.get(var_shell, None)
    shell_driver_type: Type[ShellDriverBase]

    if shell_abs_path is None:
        shell_abs_path = "/bin/sh"
        logger.warning(f"env var `{var_shell}` is not set - assuming [{shell_abs_path}] as default")
        shell_driver_type = ShellDriverSh
    else:
        basename = os.path.basename(shell_abs_path)
        if basename == ShellType.shell_bash.value:
            shell_driver_type = ShellDriverBash
        elif basename == ShellType.shell_zsh.value:
            shell_driver_type = ShellDriverZsh
        elif basename == ShellType.shell_sh.value:
            shell_driver_type = ShellDriverSh
        else:
            raise ValueError(f"Unknown shell: [{shell_abs_path}]")

    return shell_driver_type(
        shell_abs_path=shell_abs_path,
        shell_env_vars={},
        cache_dir_abs_path=cache_dir_abs_path,
    )
