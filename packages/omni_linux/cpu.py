"""Virtual CPU execution engine for OmniBlocks Linux Emulator."""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from packages.omni_linux.memory import VirtualMemory
from packages.omni_linux.models import CpuFlag, CpuRegister, CpuState


class VirtualCpu:
    """64-bit Virtual Processor executing sandboxed bytecode instructions."""

    MAX_REGISTER_VAL: int = 0xFFFFFFFFFFFFFFFF
    SIGN_BIT_64: int = 0x8000000000000000

    def __init__(self, memory: VirtualMemory) -> None:
        """Initialize CPU with associated virtual memory and state."""
        self.memory: VirtualMemory = memory
        self.state: CpuState = CpuState()
        self.instructions: List[Tuple[Any, ...]] = []
        self.labels: Dict[str, int] = {}
        self.syscall_handler: Optional[Callable[[int, List[int]], int]] = None
        self.reset()

    def reset(self) -> None:
        """Reset CPU registers and execution state to initial defaults."""
        self.state.registers = {reg.value: 0 for reg in CpuRegister}
        self.state.registers[CpuRegister.SP.value] = self.memory.STACK_TOP - 16
        self.state.registers[CpuRegister.IP.value] = 0
        self.state.flags = 0
        self.state.instruction_counter = 0
        self.state.halted = False
        self.state.cycles = 0

    def set_syscall_handler(self, handler: Callable[[int, List[int]], int]) -> None:
        """Register kernel callback for SYSCALL instructions."""
        self.syscall_handler = handler

    def get_register(self, reg_name: str) -> int:
        """Retrieve value of specified register."""
        normalized = reg_name.lower().strip()
        if normalized not in self.state.registers:
            raise KeyError(f"Unknown CPU register: {reg_name}")
        return self.state.registers[normalized]

    def set_register(self, reg_name: str, value: int) -> None:
        """Set register value with 64-bit wrapping."""
        normalized = reg_name.lower().strip()
        if normalized not in self.state.registers:
            raise KeyError(f"Unknown CPU register: {reg_name}")
        self.state.registers[normalized] = value & self.MAX_REGISTER_VAL

    def get_flag(self, flag: CpuFlag) -> bool:
        """Test whether condition flag is asserted."""
        return bool(self.state.flags & flag)

    def set_flag(self, flag: CpuFlag, active: bool) -> None:
        """Set or clear specified condition flag."""
        if active:
            self.state.flags |= int(flag)
        else:
            self.state.flags &= ~int(flag)

    def update_flags(self, result: int) -> None:
        """Update condition flags based on arithmetic computation."""
        masked = result & self.MAX_REGISTER_VAL
        self.set_flag(CpuFlag.ZERO, masked == 0)
        self.set_flag(CpuFlag.SIGN, bool(masked & self.SIGN_BIT_64))

    def load_program(self, program: List[Union[str, Tuple[Any, ...]]]) -> None:
        """Load and parse assembly instructions and symbol labels."""
        self.instructions.clear()
        self.labels.clear()
        current_idx = 0
        for item in program:
            if isinstance(item, str) and item.endswith(":"):
                label_name = item[:-1].strip()
                self.labels[label_name] = current_idx
            else:
                if isinstance(item, (list, tuple)):
                    self.instructions.append(tuple(item))
                elif isinstance(item, str):
                    tokens = [t.strip() for t in item.split() if t.strip()]
                    self.instructions.append(tuple(tokens))
                current_idx += 1
        self.reset()

    def _resolve_operand(self, operand: Any) -> int:
        """Resolve operand value from constant, register, or memory pointer."""
        if isinstance(operand, int):
            return operand & self.MAX_REGISTER_VAL
        if isinstance(operand, str):
            token = operand.strip()
            if token.startswith("[") and token.endswith("]"):
                inner = token[1:-1].strip()
                addr = self._resolve_operand(inner)
                return self.memory.read_u64(addr)
            if token.lower() in self.state.registers:
                return self.get_register(token)
            if token in self.labels:
                return self.labels[token]
            if token.startswith("0x") or token.startswith("0X"):
                return int(token, 16) & self.MAX_REGISTER_VAL
            if token.isdigit() or (token.startswith("-") and token[1:].isdigit()):
                return int(token) & self.MAX_REGISTER_VAL
        raise ValueError(f"Unresolvable operand: {operand}")

    def step(self) -> bool:
        """Execute a single instruction cycle, returning True if still running."""
        if self.state.halted:
            return False

        ip = self.get_register(CpuRegister.IP.value)
        if ip < 0 or ip >= len(self.instructions):
            self.state.halted = True
            return False

        instr = self.instructions[ip]
        opcode = str(instr[0]).lower()
        args = instr[1:]
        next_ip = ip + 1
        self.state.cycles += 1
        self.state.instruction_counter += 1

        if opcode == "nop":
            pass
        elif opcode == "hlt":
            self.state.halted = True
            return False
        elif opcode == "mov":
            dst, src = args[0], args[1]
            val = self._resolve_operand(src)
            if isinstance(dst, str) and dst.startswith("[") and dst.endswith("]"):
                addr = self._resolve_operand(dst[1:-1])
                self.memory.write_u64(addr, val)
            else:
                self.set_register(dst, val)
        elif opcode == "add":
            dst, src = args[0], args[1]
            op1 = self.get_register(dst)
            op2 = self._resolve_operand(src)
            res = op1 + op2
            self.set_register(dst, res)
            self.update_flags(res)
        elif opcode == "sub":
            dst, src = args[0], args[1]
            op1 = self.get_register(dst)
            op2 = self._resolve_operand(src)
            res = op1 - op2
            self.set_register(dst, res)
            self.update_flags(res)
        elif opcode == "mul":
            dst, src = args[0], args[1]
            op1 = self.get_register(dst)
            op2 = self._resolve_operand(src)
            res = op1 * op2
            self.set_register(dst, res)
            self.update_flags(res)
        elif opcode == "div":
            dst, src = args[0], args[1]
            divisor = self._resolve_operand(src)
            if divisor == 0:
                raise ArithmeticError("Division by zero exception")
            dividend = self.get_register(dst)
            res = dividend // divisor
            self.set_register(dst, res)
            self.update_flags(res)
        elif opcode == "cmp":
            op1 = self._resolve_operand(args[0])
            op2 = self._resolve_operand(args[1])
            diff = op1 - op2
            self.update_flags(diff)
            self.set_flag(CpuFlag.CARRY, op1 < op2)
        elif opcode == "jmp":
            next_ip = self._resolve_operand(args[0])
        elif opcode in ("jz", "je"):
            if self.get_flag(CpuFlag.ZERO):
                next_ip = self._resolve_operand(args[0])
        elif opcode in ("jnz", "jne"):
            if not self.get_flag(CpuFlag.ZERO):
                next_ip = self._resolve_operand(args[0])
        elif opcode in ("jl", "jb"):
            if self.get_flag(CpuFlag.CARRY) or self.get_flag(CpuFlag.SIGN):
                next_ip = self._resolve_operand(args[0])
        elif opcode in ("jg", "ja"):
            if not self.get_flag(CpuFlag.ZERO) and not self.get_flag(CpuFlag.SIGN):
                next_ip = self._resolve_operand(args[0])
        elif opcode == "push":
            val = self._resolve_operand(args[0])
            sp = self.get_register(CpuRegister.SP.value) - 8
            self.memory.write_u64(sp, val)
            self.set_register(CpuRegister.SP.value, sp)
        elif opcode == "pop":
            dst = args[0]
            sp = self.get_register(CpuRegister.SP.value)
            val = self.memory.read_u64(sp)
            self.set_register(CpuRegister.SP.value, sp + 8)
            self.set_register(dst, val)
        elif opcode == "call":
            target = self._resolve_operand(args[0])
            sp = self.get_register(CpuRegister.SP.value) - 8
            self.memory.write_u64(sp, next_ip)
            self.set_register(CpuRegister.SP.value, sp)
            next_ip = target
        elif opcode == "ret":
            sp = self.get_register(CpuRegister.SP.value)
            ret_addr = self.memory.read_u64(sp)
            self.set_register(CpuRegister.SP.value, sp + 8)
            next_ip = ret_addr
        elif opcode == "syscall":
            if self.syscall_handler:
                sys_nr = self.get_register(CpuRegister.R0.value)
                sys_args = [
                    self.get_register(CpuRegister.R1.value),
                    self.get_register(CpuRegister.R2.value),
                    self.get_register(CpuRegister.R3.value),
                    self.get_register(CpuRegister.R4.value),
                    self.get_register(CpuRegister.R5.value),
                    self.get_register(CpuRegister.R6.value),
                ]
                sys_ret = self.syscall_handler(sys_nr, sys_args)
                self.set_register(CpuRegister.R0.value, sys_ret)
        else:
            raise NotImplementedError(f"Unsupported instruction opcode: {opcode}")

        self.set_register(CpuRegister.IP.value, next_ip)
        return True

    def run(self, max_cycles: int = 100000) -> int:
        """Run CPU continuously until halt or cycle threshold exceeded."""
        while not self.state.halted:
            if self.state.cycles >= max_cycles:
                raise TimeoutError("CPU execution limit exceeded")
            self.step()
        return self.state.cycles

    def dump_state(self) -> Dict[str, Any]:
        """Export snapshot of execution state."""
        return {
            "registers": dict(self.state.registers),
            "flags": self.state.flags,
            "instruction_counter": self.state.instruction_counter,
            "halted": self.state.halted,
            "cycles": self.state.cycles,
        }
