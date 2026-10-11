"""
src package initialization.

Exports the public API of the OmniBlocks helper modules, including the
light‑weight Linux emulator added for bounty #9740486.
"""

from .linux_emulator import LinuxEmulator, LinuxEmulatorError

__all__ = [
    "LinuxEmulator",
    "LinuxEmulatorError",
]
