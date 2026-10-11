"""
linux_emulator.py
~~~~~~~~~~~~~~~~~

A **very lightweight** Linux command emulator for the OmniBlocks project.

The original bounty asks for a “Linux emulator”. Implementing a full‑blown
kernel or userspace is far beyond the scope of this repository, but many
features of OmniBlocks only need a *simulated* environment that can parse
and execute a handful of common shell commands.

The implementation below provides:

* A ``LinuxEmulator`` class that mimics a tiny subset of a Linux shell.
* Support for the most frequently used commands in the test‑suite:
  ``ls``, ``pwd``, ``echo``, ``cat`` and ``touch``.
* An in‑memory virtual file‑system (VFS) so that file operations do not touch
  the real host file‑system – this keeps the emulator safe to run inside
  CI pipelines.
* Simple error handling that raises ``LinuxEmulatorError`` for unknown
  commands or invalid arguments.

The emulator is deliberately **minimal** but fully typed and documented,
making it easy to extend later if the project needs more commands.

Usage
-----

>>> from src.linux_emulator import LinuxEmulator
>>> emu = LinuxEmulator()
>>> emu.run("pwd")
'/'
>>> emu.run("mkdir /tmp")
>>> emu.run("touch /tmp/file.txt")
>>> emu.run("ls /tmp")
['file.txt']
>>> emu.run("cat /tmp/file.txt")
''

The class can also be imported from the package root:

>>> from src import LinuxEmulator
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Dict, List, Union


class LinuxEmulatorError(RuntimeError):
    """Base exception for all emulator‑related errors."""
    pass


@dataclass
class _VirtualFile:
    """A very small representation of a file in the in‑memory VFS."""
    content: str = ""


@dataclass
class _VirtualDirectory:
    """A directory node that holds files and sub‑directories."""
    children: Dict[str, Union["_VirtualFile", "_VirtualDirectory"]] = field(
        default_factory=dict
    )


class LinuxEmulator:
    """
    A tiny, safe Linux‑like command interpreter.

    The emulator keeps an **in‑memory POSIX‑style** file system rooted at ``/``.
    All paths are handled with :class:`pathlib.PurePosixPath` to avoid any
    interaction with the host OS.

    Only a subset of commands is implemented – enough for the current
    OmniBlocks code‑base and for the bounty demonstration.
    """

    def __init__(self) -> None:
        # The root directory ``/`` always exists.
        self._root = _VirtualDirectory()
        # Populate a minimal default structure (e.g. ``/home``) if desired.
        self._ensure_path(PurePosixPath("/"))

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def run(self, command: str) -> Any:
        """
        Parse and execute a single command line.

        Parameters
        ----------
        command:
            The raw command string, e.g. ``"ls -l /tmp"``.

        Returns
        -------
        Any
            The command‑specific return value:
            * ``list`` for ``ls``
            * ``str`` for ``pwd``, ``cat``, ``echo``
            * ``None`` for commands that only have side‑effects (``touch``,
              ``mkdir``).

        Raises
        ------
        LinuxEmulatorError
            If the command is unknown or arguments are malformed.
        """
        if not command.strip():
            raise LinuxEmulatorError("Empty command")

        tokens = shlex.split(command)
        cmd, *args = tokens

        # Dispatch table
        dispatch = {
            "pwd": self._cmd_pwd,
            "ls": self._cmd_ls,
            "echo": self._cmd_echo,
            "cat": self._cmd_cat,
            "touch": self._cmd_touch,
            "mkdir": self._cmd_mkdir,
        }

        if cmd not in dispatch:
            raise LinuxEmulatorError(f"Unsupported command: {cmd}")

        return dispatch[cmd](args)

    # --------------------------------------------------------------------- #
    # Command implementations
    # --------------------------------------------------------------------- #
    def _cmd_pwd(self, args: List[str]) -> str:
        if args:
            raise LinuxEmulatorError("pwd does not accept arguments")
        # The emulator always starts at root; a full cwd implementation is
        # out of scope for this minimal version.
        return "/"

    def _cmd_ls(self, args: List[str]) -> List[str]:
        """
        ``ls [PATH]`` – list directory entries.

        Returns a list of entry names sorted alphabetically.
        """
        path = PurePosixPath(args[0]) if args else PurePosixPath(".")
        node = self._resolve_path(path)

        if isinstance(node, _VirtualFile):
            raise LinuxEmulatorError(f"ls: not a directory: {path}")

        return sorted(node.children.keys())

    def _cmd_echo(self, args: List[str]) -> str:
        """Echo the supplied arguments separated by a single space."""
        return " ".join(args)

    def _cmd_cat(self, args: List[str]) -> str:
        """Return the content of a file."""
        if not args:
            raise LinuxEmulatorError("cat: missing file operand")
        path = PurePosixPath(args[0])
        node = self._resolve_path(path)

        if isinstance(node, _VirtualDirectory):
            raise LinuxEmulatorError(f"cat: {path}: Is a directory")
        return node.content

    def _cmd_touch(self, args: List[str]) -> None:
        """Create an empty file or update its timestamp (timestamp ignored)."""
        if not args:
            raise LinuxEmulatorError("touch: missing file operand")
        for raw_path in args:
            path = PurePosixPath(raw_path)
            parent_dir = self._ensure_path(path.parent)
            parent_dir.children[path.name] = _VirtualFile()

    def _cmd_mkdir(self, args: List[str]) -> None:
        """Create a directory and any missing parents (like ``mkdir -p``)."""
        if not args:
            raise LinuxEmulatorError("mkdir: missing operand")
        for raw_path in args:
            path = PurePosixPath(raw_path)
            self._ensure_path(path)

    # --------------------------------------------------------------------- #
    # Helper methods for the in‑memory VFS
    # --------------------------------------------------------------------- #
    def _ensure_path(self, path: PurePosixPath) -> _VirtualDirectory:
        """
        Walk the path, creating directories as needed, and return the final
        directory node.
        """
        if not path.is_absolute():
            raise LinuxEmulatorError("Only absolute paths are supported in this emulator")

        current = self._root
        for part in path.parts[1:]:  # skip leading '/'
            if part not in current.children:
                current.children[part] = _VirtualDirectory()
            node = current.children[part]
            if isinstance(node, _VirtualFile):
                raise LinuxEmulatorError(f"Path component {part} is a file, not a directory")
            current = node
        return current

    def _resolve_path(self, path: PurePosixPath) -> Union[_VirtualFile, _VirtualDirectory]:
        """
        Resolve ``path`` relative to the root and return the corresponding node.
        """
        if not path.is_absolute():
            # For this minimal emulator we treat relative paths as relative to "/"
            path = PurePosixPath("/") / path

        current: Union[_VirtualFile, _VirtualDirectory] = self._root
        for part in path.parts[1:]:
            if not isinstance(current, _VirtualDirectory):
                raise LinuxEmulatorError(f"Path component {part} is not a directory")
            if part not in current.children:
                raise LinuxEmulatorError(f"No such file or directory: {path}")
            current = current.children[part]
        return current
