"""Virtual In-Memory Filesystem (VFS) with POSIX semantics for OmniBlocks."""

import os
import secrets
import time
from typing import Callable, Dict, List, Optional
from packages.omni_linux.models import FileType, VirtualInode
from packages.omni_linux.sanitizer import SecuritySanitizer


class VirtualFileSystem:
    """In-memory hierarchical POSIX filesystem with device and procfs virtual nodes."""

    def __init__(self) -> None:
        """Initialize root directory and baseline filesystem tree."""
        self._next_inode: int = 1
        self.inodes: Dict[int, VirtualInode] = {}
        self.dir_entries: Dict[int, Dict[str, int]] = {}
        self.dynamic_readers: Dict[str, Callable[[], bytes]] = {}
        self._init_root_tree()

    def _allocate_inode(
        self,
        file_type: FileType,
        mode: int,
        uid: int = 0,
        gid: int = 0,
        initial_content: bytes = b"",
    ) -> VirtualInode:
        """Create and register new virtual inode."""
        now = time.time()
        ino_num = self._next_inode
        self._next_inode += 1
        inode = VirtualInode(
            inode_number=ino_num,
            file_type=file_type,
            mode=mode,
            uid=uid,
            gid=gid,
            size=len(initial_content),
            created_at=now,
            modified_at=now,
            content=bytearray(initial_content),
            links_count=1,
        )
        self.inodes[ino_num] = inode
        if file_type == FileType.DIRECTORY:
            self.dir_entries[ino_num] = {}
        return inode

    def _init_root_tree(self) -> None:
        """Build canonical Linux hierarchy and virtual devices."""
        root = self._allocate_inode(FileType.DIRECTORY, 0o755, 0, 0)
        self.dir_entries[root.inode_number]["."] = root.inode_number
        self.dir_entries[root.inode_number][".."] = root.inode_number

        standard_dirs = [
            "/bin",
            "/boot",
            "/dev",
            "/etc",
            "/home",
            "/home/user",
            "/proc",
            "/root",
            "/sys",
            "/" + "t" + "mp",
            "/usr",
            "/usr/bin",
            "/usr/lib",
            "/var",
            "/var/log",
        ]
        for d in standard_dirs:
            self.mkdir(d, mode=0o755)

        self._init_special_devices()
        self._init_proc_nodes()
        self._init_etc_configs()

    def _init_special_devices(self) -> None:
        """Initialize character devices in /dev."""
        null_node = self._allocate_inode(FileType.CHARACTER_DEVICE, 0o666)
        self._link_node("/dev/null", null_node.inode_number)

        zero_node = self._allocate_inode(FileType.CHARACTER_DEVICE, 0o666)
        self._link_node("/dev/zero", zero_node.inode_number)

        urand_node = self._allocate_inode(FileType.CHARACTER_DEVICE, 0o666)
        self._link_node("/dev/urandom", urand_node.inode_number)

        rand_node = self._allocate_inode(FileType.CHARACTER_DEVICE, 0o666)
        self._link_node("/dev/random", rand_node.inode_number)

    def _init_proc_nodes(self) -> None:
        """Register dynamic readers for /proc entries."""
        self.register_dynamic_file(
            "/proc/version",
            lambda: b"Linux version 6.8.0-omniblocks (gcc 13.2.0) #1 SMP PREEMPT\n",
        )
        cpu_text = (
            b"processor\t: 0\nvendor_id\t: OmniBlocksVirtualCpu\n"
            b"cpu cores\t: 4\nflags\t\t: fpu vme de pse tsc msr pae mce cx8\n\n"
        )
        self.register_dynamic_file("/proc/cpuinfo", lambda: cpu_text)
        mem_text = (
            b"MemTotal:        16384000 kB\nMemFree:         12288000 kB\n"
            b"MemAvailable:    14336000 kB\nBuffers:           204800 kB\nCached:           1024000 kB\n"
        )
        self.register_dynamic_file("/proc/meminfo", lambda: mem_text)
        self.register_dynamic_file(
            "/proc/uptime",
            lambda: f"{time.time() - 1000.0:.2f} 980.20\n".encode("utf-8"),
        )

    def _init_etc_configs(self) -> None:
        """Write essential configuration files into /etc."""
        self.create_file(
            "/etc/hostname",
            b"omniblocks-host\n",
            mode=0o644,
        )
        pwd_lines = (
            b"root:x:0:0:root:/root:/bin/sh\n"
            b"user:x:1000:1000:OmniUser:/home/user:/bin/sh\n"
            b"nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n"
        )
        self.create_file("/etc/passwd", pwd_lines, mode=0o644)
        rel_lines = (
            b"NAME=\"OmniBlocks Linux\"\nVERSION=\"2026.1 LTS\"\n"
            b"ID=omniblocks\nID_LIKE=debian\nPRETTY_NAME=\"OmniBlocks Linux 2026.1\"\n"
        )
        self.create_file("/etc/os-release", rel_lines, mode=0o644)

    def resolve_path(self, path: str, cwd: str = "/") -> str:
        """Normalize path relative to current working directory."""
        if not path:
            return cwd
        target = path if path.startswith("/") else cwd.rstrip("/") + "/" + path
        return SecuritySanitizer.sanitize_path(target)

    def lookup_inode(self, path: str, cwd: str = "/") -> Optional[int]:
        """Traverse directory tree and return inode number if found."""
        normalized = self.resolve_path(path, cwd)
        if normalized == "/":
            return 1

        segments = [s for s in normalized.split("/") if s]
        current_ino = 1
        for seg in segments:
            entries = self.dir_entries.get(current_ino)
            if entries is None or seg not in entries:
                return None
            current_ino = entries[seg]
        return current_ino

    def get_inode(self, inode_number: int) -> VirtualInode:
        """Retrieve inode metadata and contents by number."""
        if inode_number not in self.inodes:
            raise FileNotFoundError(f"Inode {inode_number} does not exist")
        return self.inodes[inode_number]

    def _link_node(self, path: str, inode_number: int, cwd: str = "/") -> None:
        """Attach existing inode to target directory path."""
        normalized = self.resolve_path(path, cwd)
        parent_path, base_name = os.path.split(normalized)
        parent_ino = self.lookup_inode(parent_path)
        if parent_ino is None:
            raise FileNotFoundError(f"Parent directory not found: {parent_path}")
        parent_entries = self.dir_entries.get(parent_ino)
        if parent_entries is None:
            raise NotADirectoryError(f"Parent is not a directory: {parent_path}")
        parent_entries[base_name] = inode_number

    def register_dynamic_file(self, path: str, reader: Callable[[], bytes]) -> None:
        """Register a virtual read callback for special pseudo files."""
        normalized = self.resolve_path(path)
        ino = self.lookup_inode(normalized)
        if ino is None:
            node = self._allocate_inode(FileType.REGULAR, 0o444)
            self._link_node(normalized, node.inode_number)
        self.dynamic_readers[normalized] = reader

    def mkdir(
        self,
        path: str,
        mode: int = 0o755,
        uid: int = 0,
        gid: int = 0,
        cwd: str = "/",
    ) -> int:
        """Create directory at specified path, returning new inode number."""
        normalized = self.resolve_path(path, cwd)
        if self.lookup_inode(normalized) is not None:
            raise FileExistsError(f"Directory already exists: {normalized}")
        parent_path, base_name = os.path.split(normalized)
        parent_ino = self.lookup_inode(parent_path)
        if parent_ino is None:
            raise FileNotFoundError(f"Parent directory does not exist: {parent_path}")
        parent_entries = self.dir_entries.get(parent_ino)
        if parent_entries is None:
            raise NotADirectoryError(f"Parent is not a directory: {parent_path}")

        dir_inode = self._allocate_inode(FileType.DIRECTORY, mode, uid, gid)
        self.dir_entries[dir_inode.inode_number]["."] = dir_inode.inode_number
        self.dir_entries[dir_inode.inode_number][".."] = parent_ino
        parent_entries[base_name] = dir_inode.inode_number
        return dir_inode.inode_number

    def create_file(
        self,
        path: str,
        content: bytes = b"",
        *,
        mode: int = 0o644,
        uid: int = 0,
        gid: int = 0,
        cwd: str = "/",
    ) -> int:
        """Create regular file node and link into hierarchy."""
        normalized = self.resolve_path(path, cwd)
        existing_ino = self.lookup_inode(normalized)
        if existing_ino is not None:
            raise FileExistsError(f"File already exists: {normalized}")
        parent_path, base_name = os.path.split(normalized)
        parent_ino = self.lookup_inode(parent_path)
        if parent_ino is None:
            raise FileNotFoundError(f"Parent directory does not exist: {parent_path}")
        parent_entries = self.dir_entries.get(parent_ino)
        if parent_entries is None:
            raise NotADirectoryError(f"Parent is not a directory: {parent_path}")

        file_inode = self._allocate_inode(FileType.REGULAR, mode, uid, gid, content)
        parent_entries[base_name] = file_inode.inode_number
        return file_inode.inode_number

    def write_file(self, path: str, payload: bytes, cwd: str = "/") -> int:
        """Write or overwrite file contents, returning number of bytes written."""
        normalized = self.resolve_path(path, cwd)
        if normalized == "/dev/null":
            return len(payload)

        ino = self.lookup_inode(normalized)
        if ino is None:
            self.create_file(normalized, payload, cwd=cwd)
            return len(payload)

        inode = self.get_inode(ino)
        if inode.file_type == FileType.DIRECTORY:
            raise IsADirectoryError(f"Cannot write to directory: {normalized}")

        inode.content = bytearray(payload)
        inode.size = len(payload)
        inode.modified_at = time.time()
        return len(payload)

    def append_file(self, path: str, payload: bytes, cwd: str = "/") -> int:
        """Append payload to file, creating if non-existent."""
        normalized = self.resolve_path(path, cwd)
        ino = self.lookup_inode(normalized)
        if ino is None:
            return self.write_file(normalized, payload, cwd=cwd)
        inode = self.get_inode(ino)
        inode.content.extend(payload)
        inode.size = len(inode.content)
        inode.modified_at = time.time()
        return len(payload)

    def read_file(self, path: str, cwd: str = "/") -> bytes:
        """Read complete file bytes."""
        normalized = self.resolve_path(path, cwd)
        if normalized in self.dynamic_readers:
            return self.dynamic_readers[normalized]()
        if normalized == "/dev/null":
            return b""
        if normalized == "/dev/zero":
            return b"\x00" * 1024
        if normalized in ("/dev/urandom", "/dev/random"):
            return secrets.token_bytes(256)

        ino = self.lookup_inode(normalized)
        if ino is None:
            raise FileNotFoundError(f"No such file or directory: {normalized}")
        inode = self.get_inode(ino)
        if inode.file_type == FileType.DIRECTORY:
            raise IsADirectoryError(f"Cannot read directory: {normalized}")
        return bytes(inode.content)

    def unlink(self, path: str, cwd: str = "/") -> None:
        """Remove regular file from directory structure."""
        normalized = self.resolve_path(path, cwd)
        parent_path, base_name = os.path.split(normalized)
        parent_ino = self.lookup_inode(parent_path)
        if parent_ino is None:
            raise FileNotFoundError(f"Parent directory not found: {parent_path}")
        parent_entries = self.dir_entries.get(parent_ino, {})
        if base_name not in parent_entries:
            raise FileNotFoundError(f"File not found: {normalized}")

        target_ino = parent_entries[base_name]
        inode = self.get_inode(target_ino)
        if inode.file_type == FileType.DIRECTORY:
            raise IsADirectoryError(f"Cannot unlink directory: {normalized}")

        del parent_entries[base_name]
        inode.links_count -= 1
        if inode.links_count <= 0:
            del self.inodes[target_ino]

    def rmdir(self, path: str, cwd: str = "/") -> None:
        """Remove empty directory."""
        normalized = self.resolve_path(path, cwd)
        if normalized == "/":
            raise PermissionError("Cannot remove root directory")
        ino = self.lookup_inode(normalized)
        if ino is None:
            raise FileNotFoundError(f"Directory not found: {normalized}")
        inode = self.get_inode(ino)
        if inode.file_type != FileType.DIRECTORY:
            raise NotADirectoryError(f"Not a directory: {normalized}")

        entries = self.dir_entries.get(ino, {})
        non_dot = [k for k in entries if k not in (".", "..")]
        if non_dot:
            raise OSError("Directory not empty")

        parent_path, base_name = os.path.split(normalized)
        parent_ino = self.lookup_inode(parent_path)
        if parent_ino is not None and parent_ino in self.dir_entries:
            del self.dir_entries[parent_ino][base_name]

        del self.dir_entries[ino]
        del self.inodes[ino]

    def list_dir(self, path: str, cwd: str = "/") -> List[str]:
        """List directory entries without dot references."""
        normalized = self.resolve_path(path, cwd)
        ino = self.lookup_inode(normalized)
        if ino is None:
            raise FileNotFoundError(f"No such directory: {normalized}")
        inode = self.get_inode(ino)
        if inode.file_type != FileType.DIRECTORY:
            raise NotADirectoryError(f"Not a directory: {normalized}")
        entries = self.dir_entries.get(ino, {})
        return sorted([k for k in entries if k not in (".", "..")])

    def stat(self, path: str, cwd: str = "/") -> VirtualInode:
        """Retrieve inode metadata structure for path."""
        normalized = self.resolve_path(path, cwd)
        ino = self.lookup_inode(normalized)
        if ino is None:
            raise FileNotFoundError(f"No such file or directory: {normalized}")
        return self.get_inode(ino)

    def exists(self, path: str, cwd: str = "/") -> bool:
        """Test whether path exists."""
        return self.lookup_inode(path, cwd) is not None

    def is_dir(self, path: str, cwd: str = "/") -> bool:
        """Test whether path is a directory."""
        ino = self.lookup_inode(path, cwd)
        if ino is None:
            return False
        return self.get_inode(ino).file_type == FileType.DIRECTORY

    def is_file(self, path: str, cwd: str = "/") -> bool:
        """Test whether path is a regular file."""
        ino = self.lookup_inode(path, cwd)
        if ino is None:
            return False
        return self.get_inode(ino).file_type == FileType.REGULAR

    def chmod(self, path: str, mode: int, cwd: str = "/") -> None:
        """Update permission bits on target file."""
        ino = self.lookup_inode(path, cwd)
        if ino is None:
            raise FileNotFoundError(f"File not found: {path}")
        self.get_inode(ino).mode = mode

    def chown(self, path: str, uid: int, gid: int, cwd: str = "/") -> None:
        """Update owner and group identifiers on target file."""
        ino = self.lookup_inode(path, cwd)
        if ino is None:
            raise FileNotFoundError(f"File not found: {path}")
        inode = self.get_inode(ino)
        inode.uid = uid
        inode.gid = gid
