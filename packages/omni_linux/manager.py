"""High-level Linux Virtual Machine manager and bounty settlement calculator."""

from typing import Any, Dict, List, Union
from packages.omni_linux.cpu import VirtualCpu
from packages.omni_linux.kernel import Kernel
from packages.omni_linux.memory import VirtualMemory
from packages.omni_linux.models import BountySettlement
from packages.omni_linux.shell import LinuxShell, ShellResult
from packages.omni_linux.vfs import VirtualFileSystem


class OmniLinuxVM:
    """Unified high-level virtual machine instance for OmniBlocks."""

    def __init__(self, ram_mb: int = 64, cores: int = 1) -> None:
        """Boot simulated Linux machine with specified RAM and CPU configuration."""
        self.ram_mb: int = ram_mb
        self.cores: int = cores
        self.memory: VirtualMemory = VirtualMemory(ram_size_bytes=ram_mb * 1024 * 1024)
        self.vfs: VirtualFileSystem = VirtualFileSystem()
        self.kernel: Kernel = Kernel(self.memory, self.vfs)
        self.cpu: VirtualCpu = VirtualCpu(self.memory)
        self.cpu.set_syscall_handler(self.kernel.dispatch_syscall)
        self.shell: LinuxShell = LinuxShell(self.vfs, self.kernel)

    def run_command(self, cmdline: str) -> ShellResult:
        """Execute a shell command inside the guest environment."""
        return self.shell.execute(cmdline)

    def write_file(self, path: str, content: Union[str, bytes]) -> int:
        """Write a file to the guest filesystem."""
        payload = content.encode("utf-8") if isinstance(content, str) else content
        return self.vfs.write_file(path, payload, cwd=self.shell.get_cwd())

    def read_file(self, path: str) -> str:
        """Read file as UTF-8 string from the guest filesystem."""
        raw = self.vfs.read_file(path, cwd=self.shell.get_cwd())
        return raw.decode("utf-8", errors="replace")

    def read_file_bytes(self, path: str) -> bytes:
        """Read file as raw byte array from the guest filesystem."""
        return self.vfs.read_file(path, cwd=self.shell.get_cwd())

    def execute_binary(self, instructions: List[Any], max_cycles: int = 100000) -> Dict[str, Any]:
        """Load and execute assembly instructions on the virtual CPU."""
        self.cpu.load_program(instructions)
        cycles = self.cpu.run(max_cycles=max_cycles)
        dump = self.cpu.dump_state()
        dump["cycles_executed"] = cycles
        return dump

    def dispatch_syscall(self, sys_nr: int, args: List[int]) -> int:
        """Directly invoke a POSIX system call against the virtual kernel."""
        return self.kernel.dispatch_syscall(sys_nr, args)

    def get_process_table(self) -> List[Dict[str, Any]]:
        """List currently active processes."""
        proc_list = []
        for pid, pcb in self.kernel.processes.items():
            proc_list.append({
                "pid": pid,
                "ppid": pcb.ppid,
                "name": pcb.name,
                "state": pcb.state.value,
                "cwd": pcb.cwd,
                "uid": pcb.uid,
                "gid": pcb.gid,
            })
        return proc_list

    def get_system_info(self) -> Dict[str, Any]:
        """Retrieve system hardware and kernel status."""
        uts = self.kernel.utsname
        return {
            "sysname": uts.sysname,
            "nodename": uts.nodename,
            "release": uts.release,
            "version": uts.version,
            "machine": uts.machine,
            "ram_mb": self.ram_mb,
            "cores": self.cores,
            "allocated_memory_bytes": self.memory.get_allocated_bytes(),
        }


def boot_vm(ram_mb: int = 64, cores: int = 1) -> OmniLinuxVM:
    """Convenience factory to boot a sandboxed Linux VM."""
    return OmniLinuxVM(ram_mb=ram_mb, cores=cores)


def compute_bounty_settlement(reward_usd: float = 9740486.0) -> BountySettlement:
    """Compute platform coin conversion, contributor cut, and redemption payout."""
    exchange_rate = 1.25
    redemption_rate = 0.72

    if reward_usd >= 1000.0:
        ratio = 0.85
    elif reward_usd >= 100.0:
        ratio = 0.80
    else:
        ratio = 0.70

    total_coins = reward_usd * exchange_rate
    contributor_coins = total_coins * ratio
    payout_usd = round(contributor_coins * redemption_rate, 2)
    platform_fee_usd = round(reward_usd - payout_usd, 2)

    return BountySettlement(
        reward_usd=reward_usd,
        platform_coins=total_coins,
        contributor_ratio=ratio,
        contributor_coins=contributor_coins,
        redemption_rate_usd=redemption_rate,
        contributor_payout_usd=payout_usd,
        platform_fee_usd=platform_fee_usd,
    )
