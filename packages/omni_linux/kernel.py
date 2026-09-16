"""POSIX Linux Kernel and System Call Dispatcher for OmniBlocks."""

import time
from typing import Dict, List, Optional
from packages.omni_linux.memory import VirtualMemory
from packages.omni_linux.models import (
    Errno,
    FileDescriptor,
    FileType,
    ProcessControlBlock,
    ProcessState,
    SyscallNumber,
    UtsName,
)
from packages.omni_linux.vfs import VirtualFileSystem


class Kernel:
    """Simulated Linux kernel managing processes, memory, and POSIX system calls."""

    def __init__(self, memory: VirtualMemory, vfs: VirtualFileSystem) -> None:
        """Initialize kernel subsystems and boot PID 1."""
        self.memory: VirtualMemory = memory
        self.vfs: VirtualFileSystem = vfs
        self.utsname: UtsName = UtsName()
        self.processes: Dict[int, ProcessControlBlock] = {}
        self.next_pid: int = 1
        self.current_pid: int = 1
        self.buffers: Dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
        self.pipes: Dict[int, bytearray] = {}
        self._boot_init_process()

    @property
    def stdout_buffer(self) -> bytearray:
        """Access process stdout output stream buffer."""
        return self.buffers["stdout"]

    @property
    def stderr_buffer(self) -> bytearray:
        """Access process stderr output stream buffer."""
        return self.buffers["stderr"]

    def _boot_init_process(self) -> None:
        """Create initial PID 1 system process with default stdio descriptors."""
        init_pcb = ProcessControlBlock(
            pid=1,
            ppid=0,
            state=ProcessState.RUNNING,
            name="systemd",
            cwd="/",
            uid=0,
            gid=0,
        )
        init_pcb.fd_table[0] = FileDescriptor(fd_number=0, inode_number=0, mode="r")
        init_pcb.fd_table[1] = FileDescriptor(fd_number=1, inode_number=0, mode="w")
        init_pcb.fd_table[2] = FileDescriptor(fd_number=2, inode_number=0, mode="w")
        self.processes[1] = init_pcb
        self.current_pid = 1

    def get_current_process(self) -> ProcessControlBlock:
        """Retrieve Process Control Block for active process."""
        if self.current_pid not in self.processes:
            raise RuntimeError(f"Active PID {self.current_pid} not found in process table")
        return self.processes[self.current_pid]

    def fork_process(self, name: Optional[str] = None) -> int:
        """Fork current process into a new child process."""
        parent = self.get_current_process()
        self.next_pid += 1
        new_pid = self.next_pid
        child = ProcessControlBlock(
            pid=new_pid,
            ppid=parent.pid,
            state=ProcessState.RUNNING,
            name=name if name else parent.name,
            cwd=parent.cwd,
            uid=parent.uid,
            gid=parent.gid,
            memory_limit=parent.memory_limit,
            allocated_memory=parent.allocated_memory,
        )
        for fd, desc in parent.fd_table.items():
            child.fd_table[fd] = FileDescriptor(
                fd_number=desc.fd_number,
                inode_number=desc.inode_number,
                mode=desc.mode,
                offset=desc.offset,
                is_open=desc.is_open,
            )
        self.processes[new_pid] = child
        return new_pid

    def dispatch_syscall(self, syscall_num: int, args: List[int]) -> int:
        """Route POSIX system call to appropriate kernel implementation."""
        handlers = {
            SyscallNumber.SYS_READ: self._sys_read,
            SyscallNumber.SYS_WRITE: self._sys_write,
            SyscallNumber.SYS_OPEN: self._sys_open,
            SyscallNumber.SYS_CLOSE: self._sys_close,
            SyscallNumber.SYS_STAT: self._sys_stat,
            SyscallNumber.SYS_BRK: self._sys_brk,
            SyscallNumber.SYS_GETPID: self._sys_getpid,
            SyscallNumber.SYS_GETPPID: self._sys_getppid,
            SyscallNumber.SYS_GETUID: self._sys_getuid,
            SyscallNumber.SYS_GETCWD: self._sys_getcwd,
            SyscallNumber.SYS_CHDIR: self._sys_chdir,
            SyscallNumber.SYS_MKDIR: self._sys_mkdir,
            SyscallNumber.SYS_RMDIR: self._sys_rmdir,
            SyscallNumber.SYS_UNLINK: self._sys_unlink,
            SyscallNumber.SYS_UNAME: self._sys_uname,
            SyscallNumber.SYS_EXIT: self._sys_exit,
            SyscallNumber.SYS_FORK: self._sys_fork,
            SyscallNumber.SYS_KILL: self._sys_kill,
        }
        handler = handlers.get(syscall_num)
        if handler is None:
            return -int(Errno.ENOSYS)
        try:
            return handler(args)
        except (KeyError, ValueError, OSError, MemoryError, PermissionError):
            return -int(Errno.EFAULT)

    def _sys_read(self, args: List[int]) -> int:
        """Handle sys_read(fd, buf, count)."""
        fd_num, buf_addr, count = args[0], args[1], args[2]
        proc = self.get_current_process()
        if fd_num not in proc.fd_table or not proc.fd_table[fd_num].is_open:
            return -int(Errno.EBADF)
        desc = proc.fd_table[fd_num]
        if "r" not in desc.mode and "+" not in desc.mode:
            return -int(Errno.EBADF)

        if desc.inode_number in self.pipes:
            pipe_buf = self.pipes[desc.inode_number]
            read_size = min(count, len(pipe_buf))
            chunk = bytes(pipe_buf[:read_size])
            del pipe_buf[:read_size]
            self.memory.write_bytes(buf_addr, chunk)
            return read_size

        if desc.inode_number not in self.vfs.inodes:
            return 0
        inode = self.vfs.get_inode(desc.inode_number)
        remaining = max(0, len(inode.content) - desc.offset)
        read_size = min(count, remaining)
        if read_size > 0:
            chunk = bytes(inode.content[desc.offset : desc.offset + read_size])
            self.memory.write_bytes(buf_addr, chunk)
            desc.offset += read_size
        return read_size

    def _sys_write(self, args: List[int]) -> int:
        """Handle sys_write(fd, buf, count)."""
        fd_num, buf_addr, count = args[0], args[1], args[2]
        proc = self.get_current_process()
        if fd_num not in proc.fd_table or not proc.fd_table[fd_num].is_open:
            return -int(Errno.EBADF)
        desc = proc.fd_table[fd_num]
        payload = self.memory.read_bytes(buf_addr, count)

        if fd_num == 1:
            self.stdout_buffer.extend(payload)
            return count
        if fd_num == 2:
            self.stderr_buffer.extend(payload)
            return count

        if desc.inode_number in self.pipes:
            self.pipes[desc.inode_number].extend(payload)
            return count

        if desc.inode_number not in self.vfs.inodes:
            return -int(Errno.EBADF)
        inode = self.vfs.get_inode(desc.inode_number)
        if inode.file_type == FileType.DIRECTORY:
            return -int(Errno.EISDIR)

        if desc.offset >= len(inode.content):
            inode.content.extend(payload)
        else:
            for i, b in enumerate(payload):
                pos = desc.offset + i
                if pos < len(inode.content):
                    inode.content[pos] = b
                else:
                    inode.content.append(b)
        desc.offset += len(payload)
        inode.size = len(inode.content)
        inode.modified_at = time.time()
        return count

    def _sys_open(self, args: List[int]) -> int:
        """Handle sys_open(pathname, flags, mode)."""
        path_addr, flags, mode = args[0], args[1], args[2]
        pathname = self.memory.read_cstring(path_addr)
        proc = self.get_current_process()
        norm_path = self.vfs.resolve_path(pathname, proc.cwd)

        ino = self.vfs.lookup_inode(norm_path)
        if ino is None:
            if flags & 0x40:
                file_mode = mode if mode else 0o644
                ino = self.vfs.create_file(norm_path, mode=file_mode, cwd=proc.cwd)
            else:
                return -int(Errno.ENOENT)

        new_fd = max(proc.fd_table.keys(), default=2) + 1
        access_mode = "w" if (flags & 0x01 or flags & 0x02) else "r"
        proc.fd_table[new_fd] = FileDescriptor(
            fd_number=new_fd,
            inode_number=ino,
            mode=access_mode,
        )
        return new_fd

    def _sys_close(self, args: List[int]) -> int:
        """Handle sys_close(fd)."""
        fd_num = args[0]
        proc = self.get_current_process()
        if fd_num not in proc.fd_table:
            return -int(Errno.EBADF)
        proc.fd_table[fd_num].is_open = False
        del proc.fd_table[fd_num]
        return 0

    def _sys_stat(self, args: List[int]) -> int:
        """Handle sys_stat(pathname, statbuf)."""
        path_addr, statbuf_addr = args[0], args[1]
        pathname = self.memory.read_cstring(path_addr)
        proc = self.get_current_process()
        try:
            inode = self.vfs.stat(pathname, proc.cwd)
            self.memory.write_u64(statbuf_addr, inode.inode_number)
            self.memory.write_u32(statbuf_addr + 8, inode.mode)
            self.memory.write_u32(statbuf_addr + 12, inode.uid)
            self.memory.write_u32(statbuf_addr + 16, inode.gid)
            self.memory.write_u64(statbuf_addr + 24, inode.size)
            return 0
        except FileNotFoundError:
            return -int(Errno.ENOENT)

    def _sys_brk(self, args: List[int]) -> int:
        """Handle sys_brk(new_brk)."""
        new_brk = args[0]
        return self.memory.brk(new_brk)

    def _sys_getpid(self, _args: List[int]) -> int:
        """Handle sys_getpid()."""
        return self.get_current_process().pid

    def _sys_getppid(self, _args: List[int]) -> int:
        """Handle sys_getppid()."""
        return self.get_current_process().ppid

    def _sys_getuid(self, _args: List[int]) -> int:
        """Handle sys_getuid()."""
        return self.get_current_process().uid

    def _sys_getcwd(self, args: List[int]) -> int:
        """Handle sys_getcwd(buf, size)."""
        buf_addr, size = args[0], args[1]
        proc = self.get_current_process()
        encoded = proc.cwd.encode("utf-8") + b"\x00"
        if len(encoded) > size:
            return -int(Errno.ERANGE)
        self.memory.write_bytes(buf_addr, encoded)
        return buf_addr

    def _sys_chdir(self, args: List[int]) -> int:
        """Handle sys_chdir(path)."""
        path_addr = args[0]
        pathname = self.memory.read_cstring(path_addr)
        proc = self.get_current_process()
        resolved = self.vfs.resolve_path(pathname, proc.cwd)
        if not self.vfs.is_dir(resolved):
            return -int(Errno.ENOTDIR) if self.vfs.exists(resolved) else -int(Errno.ENOENT)
        proc.cwd = resolved
        return 0

    def _sys_mkdir(self, args: List[int]) -> int:
        """Handle sys_mkdir(pathname, mode)."""
        path_addr, mode = args[0], args[1]
        pathname = self.memory.read_cstring(path_addr)
        proc = self.get_current_process()
        try:
            target_mode = mode if mode else 0o755
            self.vfs.mkdir(
                pathname,
                mode=target_mode,
                uid=proc.uid,
                gid=proc.gid,
                cwd=proc.cwd,
            )
            return 0
        except FileExistsError:
            return -int(Errno.EEXIST)
        except FileNotFoundError:
            return -int(Errno.ENOENT)

    def _sys_rmdir(self, args: List[int]) -> int:
        """Handle sys_rmdir(pathname)."""
        path_addr = args[0]
        pathname = self.memory.read_cstring(path_addr)
        proc = self.get_current_process()
        try:
            self.vfs.rmdir(pathname, cwd=proc.cwd)
            return 0
        except FileNotFoundError:
            return -int(Errno.ENOENT)
        except OSError:
            return -int(Errno.ENOTEMPTY)

    def _sys_unlink(self, args: List[int]) -> int:
        """Handle sys_unlink(pathname)."""
        path_addr = args[0]
        pathname = self.memory.read_cstring(path_addr)
        proc = self.get_current_process()
        try:
            self.vfs.unlink(pathname, cwd=proc.cwd)
            return 0
        except FileNotFoundError:
            return -int(Errno.ENOENT)
        except IsADirectoryError:
            return -int(Errno.EISDIR)

    def _sys_uname(self, args: List[int]) -> int:
        """Handle sys_uname(buf)."""
        buf_addr = args[0]
        fields = [
            self.utsname.sysname,
            self.utsname.nodename,
            self.utsname.release,
            self.utsname.version,
            self.utsname.machine,
        ]
        offset = 0
        for val in fields:
            chunk = val.encode("utf-8")[:64]
            padded = chunk + b"\x00" * (65 - len(chunk))
            self.memory.write_bytes(buf_addr + offset, padded)
            offset += 65
        return 0

    def _sys_exit(self, args: List[int]) -> int:
        """Handle sys_exit(status)."""
        status = args[0]
        proc = self.get_current_process()
        proc.state = ProcessState.TERMINATED
        proc.exit_code = status
        return status

    def _sys_fork(self, _args: List[int]) -> int:
        """Handle sys_fork()."""
        return self.fork_process()

    def _sys_kill(self, args: List[int]) -> int:
        """Handle sys_kill(pid, sig)."""
        target_pid, sig = args[0], args[1]
        if target_pid not in self.processes:
            return -int(Errno.ESRCH)
        target = self.processes[target_pid]
        if sig == 9:
            target.state = ProcessState.TERMINATED
            target.exit_code = 137
        elif sig == 15:
            target.state = ProcessState.TERMINATED
            target.exit_code = 143
        return 0
