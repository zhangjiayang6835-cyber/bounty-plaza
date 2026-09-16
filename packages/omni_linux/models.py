"""Data models and core definitions for OmniBlocks Linux Emulator."""

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Dict, Optional


class CpuRegister(str, Enum):
    """CPU Register identifiers for virtual execution."""

    R0 = "r0"
    R1 = "r1"
    R2 = "r2"
    R3 = "r3"
    R4 = "r4"
    R5 = "r5"
    R6 = "r6"
    R7 = "r7"
    IP = "ip"
    SP = "sp"
    FLAGS = "flags"


class CpuFlag(IntEnum):
    """CPU Condition Flags bitmask."""

    ZERO = 1
    CARRY = 2
    SIGN = 4
    OVERFLOW = 8


class ProcessState(str, Enum):
    """Process execution state enumeration."""

    RUNNING = "running"
    SLEEPING = "sleeping"
    STOPPED = "stopped"
    ZOMBIE = "zombie"
    TERMINATED = "terminated"


class FileType(str, Enum):
    """Virtual filesystem node type."""

    REGULAR = "regular"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    CHARACTER_DEVICE = "char_device"
    BLOCK_DEVICE = "block_device"
    FIFO = "fifo"
    SOCKET = "socket"


class SyscallNumber(IntEnum):
    """POSIX Linux x86_64 standard syscall numbers."""

    SYS_READ = 0
    SYS_WRITE = 1
    SYS_OPEN = 2
    SYS_CLOSE = 3
    SYS_STAT = 4
    SYS_FSTAT = 5
    SYS_LSEEK = 8
    SYS_MMAP = 9
    SYS_BRK = 12
    SYS_IOCTL = 16
    SYS_PIPE = 22
    SYS_DUP = 32
    SYS_DUP2 = 33
    SYS_GETPID = 39
    SYS_FORK = 57
    SYS_EXECVE = 59
    SYS_EXIT = 60
    SYS_WAIT4 = 61
    SYS_KILL = 62
    SYS_UNAME = 63
    SYS_GETCWD = 79
    SYS_CHDIR = 80
    SYS_MKDIR = 83
    SYS_RMDIR = 84
    SYS_UNLINK = 87
    SYS_GETUID = 102
    SYS_GETPPID = 110


class Errno(IntEnum):
    """Standard POSIX error codes."""

    SUCCESS = 0
    EPERM = 1
    ENOENT = 2
    ESRCH = 3
    EINTR = 4
    EIO = 5
    EBADF = 9
    EAGAIN = 11
    ENOMEM = 12
    EACCES = 13
    EFAULT = 14
    EEXIST = 17
    ENOTDIR = 20
    EISDIR = 21
    EINVAL = 22
    EMFILE = 24
    ERANGE = 34
    ENOSYS = 38
    ENOTEMPTY = 39


@dataclass
class CpuState:
    """Virtual CPU execution register state and runtime tracking."""

    registers: Dict[str, int] = field(default_factory=dict)
    flags: int = 0
    instruction_counter: int = 0
    halted: bool = False
    cycles: int = 0

    def __post_init__(self) -> None:
        if not self.registers:
            for reg in CpuRegister:
                self.registers[reg.value] = 0


@dataclass
class MemorySegment:
    """Isolated memory segment for virtual machine processes."""

    name: str
    start_address: int
    size: int
    permissions: str
    data: bytearray = field(default_factory=bytearray)

    def __post_init__(self) -> None:
        if len(self.data) < self.size:
            self.data = bytearray(self.size)


@dataclass
class VirtualInode:
    """Metadata and storage for filesystem nodes in virtual file system."""

    inode_number: int
    file_type: FileType
    mode: int
    uid: int
    gid: int
    size: int
    created_at: float
    modified_at: float
    content: bytearray = field(default_factory=bytearray)
    links_count: int = 1


@dataclass
class DirectoryEntry:
    """Directory entry linking path names to inode numbers."""

    name: str
    inode_number: int
    file_type: FileType


@dataclass
class FileDescriptor:
    """Process file descriptor handle."""

    fd_number: int
    inode_number: int
    mode: str
    offset: int = 0
    is_open: bool = True


@dataclass
class ProcessControlBlock:
    """Process Control Block (PCB) tracking process lifecycle and state."""

    pid: int
    ppid: int
    state: ProcessState
    name: str
    cwd: str = "/"
    uid: int = 0
    gid: int = 0
    fd_table: Dict[int, FileDescriptor] = field(default_factory=dict)
    memory_limit: int = 67108864
    allocated_memory: int = 0
    cpu_ticks: int = 0
    exit_code: Optional[int] = None


@dataclass
class UtsName:
    """Kernel system information structure matching POSIX utsname."""

    sysname: str = "Linux"
    nodename: str = "omniblocks-vm"
    release: str = "6.8.0-omniblocks"
    version: str = "#1 SMP PREEMPT_DYNAMIC OmniBlocks 2026"
    machine: str = "x86_64"


@dataclass
class BountySettlement:
    """Bounty financial breakdown computed according to REWARD_POLICY.md."""

    reward_usd: float
    platform_coins: float
    contributor_ratio: float
    contributor_coins: float
    redemption_rate_usd: float
    contributor_payout_usd: float
    platform_fee_usd: float
