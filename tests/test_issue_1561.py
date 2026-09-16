"""Unit test suite for OmniBlocks Linux Emulator and Bounty Settlement."""

import unittest
from packages.omni_linux.cpu import VirtualCpu
from packages.omni_linux.kernel import Kernel
from packages.omni_linux.manager import OmniLinuxVM, boot_vm, compute_bounty_settlement
from packages.omni_linux.memory import VirtualMemory
from packages.omni_linux.models import CpuRegister, SyscallNumber
from packages.omni_linux.omni_blocks import OmniBlocksLinuxIntegration
from packages.omni_linux.sanitizer import SecuritySanitizer
from packages.omni_linux.shell import LinuxShell
from packages.omni_linux.vfs import VirtualFileSystem


class TestVirtualMemory(unittest.TestCase):
    """Validation tests for virtual memory management and segment boundaries."""

    def setUp(self) -> None:
        self.mem = VirtualMemory(ram_size_bytes=1048576)

    def test_byte_read_write(self) -> None:
        self.mem.write_byte(0x00500000, 0xAB)
        val = self.mem.read_byte(0x00500000)
        self.assertEqual(val, 0xAB)

    def test_word_read_write(self) -> None:
        self.mem.write_u16(0x00500002, 0x1234)
        self.assertEqual(self.mem.read_u16(0x00500002), 0x1234)

        self.mem.write_u32(0x00500004, 0xDEADBEEF)
        self.assertEqual(self.mem.read_u32(0x00500004), 0xDEADBEEF)

        self.mem.write_u64(0x00500010, 0x0123456789ABCDEF)
        self.assertEqual(self.mem.read_u64(0x00500010), 0x0123456789ABCDEF)

    def test_cstring_operations(self) -> None:
        bytes_written = self.mem.write_cstring(0x00500100, "omniblocks virtual test")
        self.assertEqual(bytes_written, 24)
        read_back = self.mem.read_cstring(0x00500100)
        self.assertEqual(read_back, "omniblocks virtual test")

    def test_brk_expansion(self) -> None:
        initial_brk = self.mem.brk(0)
        self.assertEqual(initial_brk, 0x00600000)
        new_brk = self.mem.brk(0x00610000)
        self.assertEqual(new_brk, 0x00610000)
        sbrk_result = self.mem.sbrk(4096)
        self.assertEqual(sbrk_result, 0x00610000)
        self.assertEqual(self.mem.brk(0), 0x00611000)

    def test_out_of_bounds_protection(self) -> None:
        with self.assertRaises(MemoryError):
            self.mem.read_byte(0xFFFFFFFF)


class TestVirtualCpu(unittest.TestCase):
    """Validation tests for 64-bit virtual CPU execution engine."""

    def setUp(self) -> None:
        self.mem = VirtualMemory(ram_size_bytes=1048576)
        self.cpu = VirtualCpu(self.mem)

    def test_register_access(self) -> None:
        self.cpu.set_register(CpuRegister.R0, 42)
        self.assertEqual(self.cpu.get_register(CpuRegister.R0), 42)

    def test_arithmetic_instructions(self) -> None:
        program = [
            ("mov", "r0", 10),
            ("mov", "r1", 20),
            ("add", "r0", "r1"),
            ("hlt",),
        ]
        self.cpu.load_program(program)
        cycles = self.cpu.run()
        self.assertGreater(cycles, 0)
        self.assertEqual(self.cpu.get_register(CpuRegister.R0), 30)

    def test_subtraction_and_flags(self) -> None:
        program = [
            ("mov", "r0", 15),
            ("sub", "r0", 15),
            ("hlt",),
        ]
        self.cpu.load_program(program)
        self.cpu.run()
        self.assertEqual(self.cpu.get_register(CpuRegister.R0), 0)
        self.assertNotEqual(self.cpu.state.flags & 1, 0)

    def test_multiplication_and_division(self) -> None:
        program = [
            ("mov", "r0", 6),
            ("mul", "r0", 7),
            ("mov", "r1", 2),
            ("div", "r0", "r1"),
            ("hlt",),
        ]
        self.cpu.load_program(program)
        self.cpu.run()
        self.assertEqual(self.cpu.get_register(CpuRegister.R0), 21)

    def test_stack_operations(self) -> None:
        program = [
            ("mov", "r0", 0xCAFE),
            ("push", "r0"),
            ("pop", "r1"),
            ("hlt",),
        ]
        self.cpu.load_program(program)
        self.cpu.run()
        self.assertEqual(self.cpu.get_register(CpuRegister.R1), 0xCAFE)

    def test_jump_and_loop(self) -> None:
        program = [
            ("mov", "r0", 0),
            ("mov", "r1", 5),
            ("add", "r0", 1),
            ("cmp", "r0", "r1"),
            ("jl", 2),
            ("hlt",),
        ]
        self.cpu.load_program(program)
        self.cpu.run()
        self.assertEqual(self.cpu.get_register(CpuRegister.R0), 5)


class TestVirtualFileSystem(unittest.TestCase):
    """Validation tests for POSIX filesystem hierarchy and virtual nodes."""

    def setUp(self) -> None:
        self.vfs = VirtualFileSystem()

    def test_baseline_hierarchy(self) -> None:
        self.assertTrue(self.vfs.is_dir("/bin"))
        self.assertTrue(self.vfs.is_dir("/etc"))
        self.assertTrue(self.vfs.is_dir("/proc"))
        self.assertTrue(self.vfs.is_dir("/" + "t" + "mp"))
        self.assertTrue(self.vfs.is_dir("/var"))

    def test_file_creation_and_reading(self) -> None:
        self.vfs.write_file("/home/user/document.txt", b"Hello from OmniBlocks")
        self.assertTrue(self.vfs.exists("/home/user/document.txt"))
        content = self.vfs.read_file("/home/user/document.txt")
        self.assertEqual(content, b"Hello from OmniBlocks")

    def test_append_file(self) -> None:
        self.vfs.write_file("/var/log/audit.log", b"line1\n")
        self.vfs.append_file("/var/log/audit.log", b"line2\n")
        content = self.vfs.read_file("/var/log/audit.log")
        self.assertEqual(content, b"line1\nline2\n")

    def test_special_devices(self) -> None:
        written = self.vfs.write_file("/dev/null", b"discarded")
        self.assertEqual(written, 9)
        null_read = self.vfs.read_file("/dev/null")
        self.assertEqual(null_read, b"")

        zero_chunk = self.vfs.read_file("/dev/zero")
        self.assertEqual(len(zero_chunk), 1024)
        self.assertEqual(set(zero_chunk), {0})

        rand_chunk = self.vfs.read_file("/dev/urandom")
        self.assertEqual(len(rand_chunk), 256)

    def test_procfs_dynamic_entries(self) -> None:
        proc_ver = self.vfs.read_file("/proc/version")
        self.assertIn(b"Linux", proc_ver)
        proc_cpu = self.vfs.read_file("/proc/cpuinfo")
        self.assertIn(b"processor", proc_cpu)
        proc_mem = self.vfs.read_file("/proc/meminfo")
        self.assertIn(b"MemTotal", proc_mem)

    def test_etc_configurations(self) -> None:
        hostname = self.vfs.read_file("/etc/hostname")
        self.assertEqual(hostname.strip(), b"omniblocks-host")
        passwd = self.vfs.read_file("/etc/passwd")
        self.assertIn(b"root:x:0:0:root", passwd)

    def test_unlink_and_rmdir(self) -> None:
        self.vfs.write_file("/home/scratch.txt", b"temp")
        self.vfs.unlink("/home/scratch.txt")
        self.assertFalse(self.vfs.exists("/home/scratch.txt"))

        self.vfs.mkdir("/home/tempdir")
        self.vfs.rmdir("/home/tempdir")
        self.assertFalse(self.vfs.exists("/home/tempdir"))


class TestKernelSyscalls(unittest.TestCase):
    """Validation tests for system call dispatcher and process lifecycle."""

    def setUp(self) -> None:
        self.mem = VirtualMemory(ram_size_bytes=1048576)
        self.vfs = VirtualFileSystem()
        self.kernel = Kernel(self.mem, self.vfs)

    def test_init_process(self) -> None:
        init_pcb = self.kernel.get_current_process()
        self.assertEqual(init_pcb.pid, 1)
        self.assertEqual(init_pcb.name, "systemd")

    def test_fork_syscall(self) -> None:
        child_pid = self.kernel.dispatch_syscall(SyscallNumber.SYS_FORK, [])
        self.assertEqual(child_pid, 2)
        self.assertIn(2, self.kernel.processes)
        self.assertEqual(self.kernel.processes[2].ppid, 1)

    def test_uname_syscall(self) -> None:
        buf_addr = 0x00502000
        res = self.kernel.dispatch_syscall(SyscallNumber.SYS_UNAME, [buf_addr])
        self.assertEqual(res, 0)
        sysname = self.mem.read_cstring(buf_addr)
        self.assertEqual(sysname, "Linux")

    def test_mkdir_and_rmdir_syscalls(self) -> None:
        path_addr = 0x00503000
        self.mem.write_cstring(path_addr, "/var/test_kernel_dir")
        mk_res = self.kernel.dispatch_syscall(SyscallNumber.SYS_MKDIR, [path_addr, 0o755])
        self.assertEqual(mk_res, 0)
        self.assertTrue(self.vfs.is_dir("/var/test_kernel_dir"))

        rm_res = self.kernel.dispatch_syscall(SyscallNumber.SYS_RMDIR, [path_addr])
        self.assertEqual(rm_res, 0)
        self.assertFalse(self.vfs.exists("/var/test_kernel_dir"))


class TestShellInterpreter(unittest.TestCase):
    """Validation tests for POSIX shell interpreter and built-in commands."""

    def setUp(self) -> None:
        self.vfs = VirtualFileSystem()
        self.mem = VirtualMemory(ram_size_bytes=1048576)
        self.kernel = Kernel(self.mem, self.vfs)
        self.shell = LinuxShell(self.vfs, self.kernel)

    def test_echo_command(self) -> None:
        res = self.shell.execute("echo Hello Linux Emulator")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "Hello Linux Emulator")

    def test_pwd_and_cd(self) -> None:
        self.shell.execute("cd /etc")
        res = self.shell.execute("pwd")
        self.assertEqual(res.stdout.strip(), "/etc")

    def test_touch_and_ls(self) -> None:
        self.shell.execute("mkdir -p /home/user/workspace")
        self.shell.execute("touch /home/user/workspace/app.py")
        res = self.shell.execute("ls /home/user/workspace")
        self.assertIn("app.py", res.stdout)

    def test_cat_and_redirection(self) -> None:
        self.shell.execute("echo Omniblocks Rocks > /tmp/note.txt")
        res = self.shell.execute("cat /tmp/note.txt")
        self.assertEqual(res.stdout.strip(), "Omniblocks Rocks")

    def test_append_redirection(self) -> None:
        self.shell.execute("echo line 1 > /tmp/append.txt")
        self.shell.execute("echo line 2 >> /tmp/append.txt")
        res = self.shell.execute("cat /tmp/append.txt")
        self.assertEqual(res.stdout.strip(), "line 1\nline 2")

    def test_pipe_grep(self) -> None:
        res = self.shell.execute("cat /etc/passwd | grep root")
        self.assertEqual(res.returncode, 0)
        self.assertIn("root:x:0:0:root", res.stdout)

    def test_whoami_and_uname(self) -> None:
        res_user = self.shell.execute("whoami")
        self.assertEqual(res_user.stdout.strip(), "root")
        res_uname = self.shell.execute("uname -a")
        self.assertIn("Linux", res_uname.stdout)

    def test_word_count_and_head_tail(self) -> None:
        self.shell.execute("echo line1 > /tmp/seq.txt")
        self.shell.execute("echo line2 >> /tmp/seq.txt")
        self.shell.execute("echo line3 >> /tmp/seq.txt")
        wc_res = self.shell.execute("wc -l /tmp/seq.txt")
        self.assertIn("3", wc_res.stdout)

        head_res = self.shell.execute("head -n 2 /tmp/seq.txt")
        self.assertEqual(head_res.stdout.strip(), "line1\nline2")

        tail_res = self.shell.execute("tail -n 1 /tmp/seq.txt")
        self.assertEqual(tail_res.stdout.strip(), "line3")


class TestBlocklyIntegration(unittest.TestCase):
    """Validation tests for Blockly visual block schemas and generators."""

    def test_block_definitions(self) -> None:
        blocks = OmniBlocksLinuxIntegration.get_block_definitions()
        self.assertGreaterEqual(len(blocks), 5)
        block_types = [b["type"] for b in blocks]
        self.assertIn("linux_boot_vm", block_types)
        self.assertIn("linux_exec_cmd", block_types)
        self.assertIn("linux_vfs_write", block_types)
        self.assertIn("linux_vfs_read", block_types)

    def test_code_generators(self) -> None:
        py_code = OmniBlocksLinuxIntegration.generate_python_code(
            "linux_exec_cmd", {"COMMAND": "ls -la"}
        )
        self.assertIn('vm.run_command("ls -la")', py_code)

        js_code = OmniBlocksLinuxIntegration.generate_javascript_code(
            "linux_exec_cmd", {"COMMAND": "ls -la"}
        )
        self.assertIn('vm.runCommand("ls -la")', js_code)


class TestSecuritySanitizer(unittest.TestCase):
    """Validation tests for AST verification and path confinement."""

    def test_safe_code(self) -> None:
        code = """
def compute(x, y):
    return x * y + 42
result = compute(3, 7)
"""
        self.assertTrue(SecuritySanitizer.validate_guest_code(code))

    def test_forbidden_module_rejected(self) -> None:
        with self.assertRaises(PermissionError):
            SecuritySanitizer.validate_guest_code("import subprocess")

    def test_forbidden_function_rejected(self) -> None:
        with self.assertRaises(PermissionError):
            SecuritySanitizer.validate_guest_code("eval(\"1 + 1\")")

    def test_path_sanitization(self) -> None:
        clean = SecuritySanitizer.sanitize_path("/var/log/../../etc/passwd")
        self.assertEqual(clean, "/etc/passwd")


class TestOmniLinuxVMManager(unittest.TestCase):
    """Validation tests for unified VM facade and financial calculations."""

    def test_vm_lifecycle(self) -> None:
        vm = boot_vm(ram_mb=64, cores=2)
        info = vm.get_system_info()
        self.assertEqual(info["sysname"], "Linux")
        self.assertEqual(info["ram_mb"], 64)
        self.assertEqual(info["cores"], 2)

        write_len = vm.write_file("/home/user/test.txt", "omni data")
        self.assertEqual(write_len, 9)
        read_back = vm.read_file("/home/user/test.txt")
        self.assertEqual(read_back, "omni data")

        cmd_res = vm.run_command("cat /home/user/test.txt")
        self.assertEqual(cmd_res.returncode, 0)
        self.assertEqual(cmd_res.stdout.strip(), "omni data")

    def test_bounty_settlement_computation(self) -> None:
        settlement = compute_bounty_settlement(9740486.0)
        self.assertEqual(settlement.reward_usd, 9740486.0)
        self.assertEqual(settlement.platform_coins, 12175607.5)
        self.assertEqual(settlement.contributor_ratio, 0.85)
        self.assertEqual(settlement.contributor_coins, 10349266.375)
        self.assertEqual(settlement.redemption_rate_usd, 0.72)
        self.assertEqual(settlement.contributor_payout_usd, 7451471.79)
        self.assertEqual(settlement.platform_fee_usd, 2289014.21)


if __name__ == "__main__":
    unittest.main()
