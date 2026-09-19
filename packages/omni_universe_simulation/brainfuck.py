"""Turing-complete Brainfuck virtual machine, optimizing compiler, and program synthesizer."""

from typing import List
from .models import BrainfuckExecutionResult, BrainfuckOp


class BrainfuckOptimizer:
    """Compiles raw Brainfuck source code into optimized linear intermediate bytecode."""

    VALID_CHARACTERS = frozenset("><+-.,[]")

    @classmethod
    def compile_bytecode(cls, source_code: str) -> List[BrainfuckOp]:
        """Translates Brainfuck source characters into compacted linear bytecode operations."""
        cleaned = [ch for ch in source_code if ch in cls.VALID_CHARACTERS]
        ops: List[BrainfuckOp] = []
        idx = 0
        total_len = len(cleaned)

        while idx < total_len:
            ch = cleaned[idx]
            if ch in "+-":
                delta = 0
                while idx < total_len and cleaned[idx] in "+-":
                    delta += 1 if cleaned[idx] == "+" else -1
                    idx += 1
                if delta != 0:
                    ops.append(BrainfuckOp(op_code="ADD_VAL", argument=delta))
                continue

            if ch in "><":
                delta = 0
                while idx < total_len and cleaned[idx] in "><":
                    delta += 1 if cleaned[idx] == ">" else -1
                    idx += 1
                if delta != 0:
                    ops.append(BrainfuckOp(op_code="SHIFT_PTR", argument=delta))
                continue

            if ch == "[":
                if idx + 2 < total_len and cleaned[idx + 1] in "+-" and cleaned[idx + 2] == "]":
                    ops.append(BrainfuckOp(op_code="CLEAR_CELL", argument=0))
                    idx += 3
                    continue
                ops.append(BrainfuckOp(op_code="LOOP_START", argument=0))
                idx += 1
                continue

            if ch == "]":
                ops.append(BrainfuckOp(op_code="LOOP_END", argument=0))
                idx += 1
                continue

            if ch == ".":
                ops.append(BrainfuckOp(op_code="OUTPUT_CHAR", argument=1))
                idx += 1
                continue

            if ch == ",":
                ops.append(BrainfuckOp(op_code="INPUT_CHAR", argument=1))
                idx += 1
                continue

            idx += 1

        resolved_ops = cls._link_loop_jumps(ops)
        return resolved_ops

    @classmethod
    def _link_loop_jumps(cls, ops: List[BrainfuckOp]) -> List[BrainfuckOp]:
        """Resolves forward and backward jump targets for loop operations."""
        stack: List[int] = []
        linked: List[BrainfuckOp] = list(ops)

        for pc, op in enumerate(ops):
            if op.op_code == "LOOP_START":
                stack.append(pc)
            elif op.op_code == "LOOP_END":
                if not stack:
                    raise ValueError("Unmatched closing bracket in Brainfuck program")
                start_pc = stack.pop()
                linked[start_pc] = BrainfuckOp(op_code="LOOP_START", argument=pc)
                linked[pc] = BrainfuckOp(op_code="LOOP_END", argument=start_pc)

        if stack:
            raise ValueError("Unmatched opening bracket in Brainfuck program")
        return linked


class BrainfuckVM:
    """Executes compiled Brainfuck bytecode against a bounded memory tape."""

    DEFAULT_TAPE_SIZE: int = 30000
    DEFAULT_CYCLE_LIMIT: int = 500000

    def __init__(self, tape_size: int = DEFAULT_TAPE_SIZE, cycle_limit: int = DEFAULT_CYCLE_LIMIT) -> None:
        """Initializes virtual machine state, allocated tape cells, and execution boundaries."""
        self.tape_size = tape_size
        self.cycle_limit = cycle_limit
        self.tape: List[int] = [0] * tape_size
        self.pointer: int = 0
        self.output_buffer: List[str] = []
        self.input_pointer: int = 0
        self.cycles: int = 0
        self.peak_pointer: int = 0

    def reset(self) -> None:
        """Resets all internal VM registers, output buffers, and memory cells to zero."""
        self.tape = [0] * self.tape_size
        self.pointer = 0
        self.output_buffer = []
        self.input_pointer = 0
        self.cycles = 0
        self.peak_pointer = 0

    def execute(self, bytecode: List[BrainfuckOp], input_data: str = "") -> BrainfuckExecutionResult:
        """Executes the provided bytecode sequence and returns execution metrics and stdout."""
        self.reset()
        program_counter = 0
        total_ops = len(bytecode)
        termination_status = "COMPLETED"

        while program_counter < total_ops:
            if self.cycles >= self.cycle_limit:
                termination_status = "CYCLE_LIMIT_EXCEEDED"
                break

            self.cycles += 1
            current_op = bytecode[program_counter]
            op_code = current_op.op_code
            arg = current_op.argument

            if op_code == "ADD_VAL":
                self.tape[self.pointer] = (self.tape[self.pointer] + arg) % 256
                program_counter += 1
            elif op_code == "SHIFT_PTR":
                self.pointer = (self.pointer + arg) % self.tape_size
                self.peak_pointer = max(self.peak_pointer, self.pointer)
                program_counter += 1
            elif op_code == "CLEAR_CELL":
                self.tape[self.pointer] = 0
                program_counter += 1
            elif op_code == "OUTPUT_CHAR":
                char_val = chr(self.tape[self.pointer])
                self.output_buffer.append(char_val)
                program_counter += 1
            elif op_code == "INPUT_CHAR":
                if self.input_pointer < len(input_data):
                    self.tape[self.pointer] = ord(input_data[self.input_pointer]) % 256
                    self.input_pointer += 1
                else:
                    self.tape[self.pointer] = 0
                program_counter += 1
            elif op_code == "LOOP_START":
                if self.tape[self.pointer] == 0:
                    program_counter = arg + 1
                else:
                    program_counter += 1
            elif op_code == "LOOP_END":
                if self.tape[self.pointer] != 0:
                    program_counter = arg + 1
                else:
                    program_counter += 1
            else:
                program_counter += 1

        active_cells = sum(1 for v in self.tape if v != 0)
        emitted_text = "".join(self.output_buffer)
        result = BrainfuckExecutionResult(
            output_text=emitted_text,
            cycles_executed=self.cycles,
            cells_used=active_cells,
            peak_cell_pointer=self.peak_pointer,
            termination_reason=termination_status,
        )
        return result


class BrainfuckProgramSynthesizer:
    """Synthesizes valid Brainfuck programs that output target text sequences."""

    @classmethod
    def synthesize_emitter(cls, target_text: str) -> str:
        """Synthesizes an efficient Brainfuck source program using loop multiplication."""
        fragments: List[str] = []
        current_val = 0

        for char in target_text:
            target_val = ord(char)
            diff = target_val - current_val

            if diff == 0:
                fragments.append(".")
                continue

            abs_diff = abs(diff)
            if abs_diff <= 5:
                symbol = "+" if diff > 0 else "-"
                fragments.append(symbol * abs_diff + ".")
            else:
                factor_a = int(abs_diff ** 0.5)
                factor_b = abs_diff // factor_a
                remainder = abs_diff % factor_a
                outer_symbol = "+" if diff > 0 else "-"

                loop_code = ">" + ("+" * factor_a) + "[<" + (outer_symbol * factor_b) + ">-]<"
                if remainder > 0:
                    loop_code += outer_symbol * remainder
                loop_code += "."
                fragments.append(loop_code)

            current_val = target_val

        synthesized_code = "".join(fragments)
        return synthesized_code
