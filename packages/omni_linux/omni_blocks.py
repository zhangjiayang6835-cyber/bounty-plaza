"""Blockly visual programming block definitions and code generators for Linux."""

from typing import Any, Dict, List


def _format_literal(val: Any) -> str:
    """Ensure string literals are properly quoted for code emission."""
    s = str(val).strip()
    if (s.startswith(chr(34)) and s.endswith(chr(34))) or (s.startswith(chr(39)) and s.endswith(chr(39))):
        return s
    return chr(34) + s + chr(34)


class OmniBlocksLinuxIntegration:
    """Generates Blockly block specifications, toolboxes, and multi-language code."""

    @staticmethod
    def get_block_definitions() -> List[Dict[str, Any]]:
        """Return JSON block definition specifications for Blockly workspace."""
        blocks = []
        blocks.append({
            "type": "linux_boot_vm",
            "message0": "boot linux vm ram %1 mb cores %2",
            "args0": [
                {"type": "field_number", "name": "RAM_MB", "value": 64, "min": 16, "max": 1024},
                {"type": "field_number", "name": "CORES", "value": 1, "min": 1, "max": 8},
            ],
            "output": "LinuxVM",
            "colour": 210,
            "tooltip": "Initialize and boot an isolated OmniBlocks Linux virtual machine instance.",
        })
        blocks.append({
            "type": "linux_exec_cmd",
            "message0": "in vm %1 execute bash command %2",
            "args0": [
                {"type": "input_value", "name": "VM", "check": "LinuxVM"},
                {"type": "field_input", "name": "COMMAND", "text": "uname -a"},
            ],
            "output": "ShellResult",
            "colour": 160,
            "tooltip": "Execute a POSIX shell command line inside the Linux environment.",
        })
        blocks.append({
            "type": "linux_vfs_write",
            "message0": "in vm %1 write file %2 with content %3",
            "args0": [
                {"type": "input_value", "name": "VM", "check": "LinuxVM"},
                {"type": "field_input", "name": "PATH", "text": "/home/user/file.txt"},
                {"type": "field_input", "name": "CONTENT", "text": "data"},
            ],
            "previousStatement": None,
            "nextStatement": None,
            "colour": 120,
            "tooltip": "Write or overwrite data in the virtual Linux filesystem.",
        })
        blocks.append({
            "type": "linux_vfs_read",
            "message0": "in vm %1 read file %2",
            "args0": [
                {"type": "input_value", "name": "VM", "check": "LinuxVM"},
                {"type": "field_input", "name": "PATH", "text": "/home/user/file.txt"},
            ],
            "output": "String",
            "colour": 120,
            "tooltip": "Read file contents as string from the virtual filesystem.",
        })
        blocks.append({
            "type": "linux_syscall",
            "message0": "in vm %1 syscall %2 args %3",
            "args0": [
                {"type": "input_value", "name": "VM", "check": "LinuxVM"},
                {"type": "field_number", "name": "SYS_NR", "value": 0},
                {"type": "input_value", "name": "ARGS", "check": "Array"},
            ],
            "output": "Number",
            "colour": 290,
            "tooltip": "Invoke a low-level POSIX system call against the virtual kernel.",
        })
        return blocks

    @staticmethod
    def generate_python_code(block_type: str, params: Dict[str, Any]) -> str:
        """Generate Python code snippet from visual block configuration."""
        if block_type == "linux_boot_vm":
            ram = params.get("RAM_MB", 64)
            cores = params.get("CORES", 1)
            return f"omni_linux.boot_vm(ram_mb={ram}, cores={cores})"
        if block_type == "linux_exec_cmd":
            vm_var = params.get("VM", "vm")
            raw_cmd = params.get("COMMAND", "uname -a")
            cmd = _format_literal(raw_cmd)
            return f"{vm_var}.run_command({cmd})"
        if block_type == "linux_vfs_write":
            vm_var = params.get("VM", "vm")
            path = _format_literal(params.get("PATH", "/home/user/file.txt"))
            content = _format_literal(params.get("CONTENT", ""))
            return f"{vm_var}.write_file({path}, {content})"
        if block_type == "linux_vfs_read":
            vm_var = params.get("VM", "vm")
            path = _format_literal(params.get("PATH", "/home/user/file.txt"))
            return f"{vm_var}.read_file({path})"
        if block_type == "linux_syscall":
            vm_var = params.get("VM", "vm")
            sys_nr = params.get("SYS_NR", 0)
            args = params.get("ARGS", "[]")
            return f"{vm_var}.dispatch_syscall({sys_nr}, {args})"
        raise ValueError(f"Unknown visual block type: {block_type}")

    @staticmethod
    def generate_javascript_code(block_type: str, params: Dict[str, Any]) -> str:
        """Generate JavaScript code snippet from visual block configuration."""
        if block_type == "linux_boot_vm":
            ram = params.get("RAM_MB", 64)
            cores = params.get("CORES", 1)
            return f"OmniLinux.bootVM({{ ramMb: {ram}, cores: {cores} }})"
        if block_type == "linux_exec_cmd":
            vm_var = params.get("VM", "vm")
            raw_cmd = params.get("COMMAND", "uname -a")
            cmd = _format_literal(raw_cmd)
            return f"{vm_var}.runCommand({cmd})"
        if block_type == "linux_vfs_write":
            vm_var = params.get("VM", "vm")
            path = _format_literal(params.get("PATH", "/home/user/file.txt"))
            content = _format_literal(params.get("CONTENT", ""))
            return f"{vm_var}.writeFile({path}, {content});"
        if block_type == "linux_vfs_read":
            vm_var = params.get("VM", "vm")
            path = _format_literal(params.get("PATH", "/home/user/file.txt"))
            return f"{vm_var}.readFile({path})"
        if block_type == "linux_syscall":
            vm_var = params.get("VM", "vm")
            sys_nr = params.get("SYS_NR", 0)
            args = params.get("ARGS", "[]")
            return f"{vm_var}.dispatchSyscall({sys_nr}, {args})"
        raise ValueError(f"Unknown visual block type: {block_type}")

    @staticmethod
    def generate_toolbox_xml() -> str:
        """Construct Blockly XML toolbox category for Linux blocks."""
        xml_lines = [
            "<category name=\"Linux Emulator\" colour=\"#4a90e2\">",
            "  <block type=\"linux_boot_vm\"></block>",
            "  <block type=\"linux_exec_cmd\"></block>",
            "  <block type=\"linux_vfs_write\"></block>",
            "  <block type=\"linux_vfs_read\"></block>",
            "  <block type=\"linux_syscall\"></block>",
            "</category>",
        ]
        return "\n".join(xml_lines)
