"""Virtual Memory Management Unit (MMU) for OmniBlocks Linux Emulator."""

from typing import Dict, Optional, Tuple
from packages.omni_linux.models import MemorySegment


class VirtualMemory:
    """Virtual Memory Manager providing page-segmented isolated memory space."""

    PAGE_SIZE: int = 4096
    TEXT_START: int = 0x00400000
    TEXT_SIZE: int = 0x00100000
    DATA_START: int = 0x00500000
    DATA_SIZE: int = 0x00100000
    HEAP_START: int = 0x00600000
    HEAP_MAX: int = 0x04000000
    STACK_TOP: int = 0x7FFFF000
    STACK_SIZE: int = 0x00800000

    def __init__(self, ram_size_bytes: int = 67108864) -> None:
        """Initialize virtual memory segments and allocations."""
        self.ram_size: int = ram_size_bytes
        self.current_brk: int = self.HEAP_START
        self.segments: Dict[str, MemorySegment] = {}
        self._init_segments()

    def _init_segments(self) -> None:
        """Initialize standard virtual memory segments."""
        self.segments["text"] = MemorySegment(
            name="text",
            start_address=self.TEXT_START,
            size=self.TEXT_SIZE,
            permissions="r-x",
        )
        self.segments["data"] = MemorySegment(
            name="data",
            start_address=self.DATA_START,
            size=self.DATA_SIZE,
            permissions="rw-",
        )
        self.segments["heap"] = MemorySegment(
            name="heap",
            start_address=self.HEAP_START,
            size=self.PAGE_SIZE,
            permissions="rw-",
        )
        self.segments["stack"] = MemorySegment(
            name="stack",
            start_address=self.STACK_TOP - self.STACK_SIZE,
            size=self.STACK_SIZE,
            permissions="rw-",
        )

    def find_segment(self, address: int) -> Optional[Tuple[str, MemorySegment, int]]:
        """Find the memory segment and offset containing the virtual address."""
        for name, seg in self.segments.items():
            if seg.start_address <= address < seg.start_address + seg.size:
                offset = address - seg.start_address
                return name, seg, offset
        return None

    def read_byte(self, address: int) -> int:
        """Read a single byte from memory."""
        match = self.find_segment(address)
        if not match:
            raise MemoryError(f"Segmentation fault: unmapped address 0x{address:08x}")
        _, seg, offset = match
        if "r" not in seg.permissions:
            raise PermissionError(f"Segmentation fault: non-readable segment at 0x{address:08x}")
        return seg.data[offset]

    def write_byte(self, address: int, value: int) -> None:
        """Write a single byte to memory."""
        match = self.find_segment(address)
        if not match:
            raise MemoryError(f"Segmentation fault: unmapped address 0x{address:08x}")
        _, seg, offset = match
        if "w" not in seg.permissions:
            raise PermissionError(f"Segmentation fault: write to read-only segment at 0x{address:08x}")
        seg.data[offset] = value & 0xFF

    def read_bytes(self, address: int, length: int) -> bytes:
        """Read contiguous byte sequence from memory."""
        data = bytearray(length)
        for i in range(length):
            data[i] = self.read_byte(address + i)
        return bytes(data)

    def write_bytes(self, address: int, payload: bytes) -> None:
        """Write contiguous byte sequence into memory."""
        for i, val in enumerate(payload):
            self.write_byte(address + i, val)

    def read_u16(self, address: int) -> int:
        """Read 16-bit unsigned integer (little-endian)."""
        raw = self.read_bytes(address, 2)
        return int.from_bytes(raw, byteorder="little", signed=False)

    def write_u16(self, address: int, value: int) -> None:
        """Write 16-bit unsigned integer (little-endian)."""
        raw = (value & 0xFFFF).to_bytes(2, byteorder="little", signed=False)
        self.write_bytes(address, raw)

    def read_u32(self, address: int) -> int:
        """Read 32-bit unsigned integer (little-endian)."""
        raw = self.read_bytes(address, 4)
        return int.from_bytes(raw, byteorder="little", signed=False)

    def write_u32(self, address: int, value: int) -> None:
        """Write 32-bit unsigned integer (little-endian)."""
        raw = (value & 0xFFFFFFFF).to_bytes(4, byteorder="little", signed=False)
        self.write_bytes(address, raw)

    def read_u64(self, address: int) -> int:
        """Read 64-bit unsigned integer (little-endian)."""
        raw = self.read_bytes(address, 8)
        return int.from_bytes(raw, byteorder="little", signed=False)

    def write_u64(self, address: int, value: int) -> None:
        """Write 64-bit unsigned integer (little-endian)."""
        raw = (value & 0xFFFFFFFFFFFFFFFF).to_bytes(8, byteorder="little", signed=False)
        self.write_bytes(address, raw)

    def read_cstring(self, address: int, max_length: int = 4096) -> str:
        """Read null-terminated ASCII/UTF-8 string from memory."""
        chars = []
        for i in range(max_length):
            b = self.read_byte(address + i)
            if b == 0:
                break
            chars.append(b)
        return bytes(chars).decode("utf-8", errors="replace")

    def write_cstring(self, address: int, text: str) -> int:
        """Write string as null-terminated UTF-8 byte stream, returns bytes written."""
        encoded = text.encode("utf-8") + b"\x00"
        self.write_bytes(address, encoded)
        return len(encoded)

    def brk(self, new_brk: int) -> int:
        """Change the data segment break address (sys_brk emulation)."""
        if new_brk == 0:
            return self.current_brk
        if new_brk < self.HEAP_START or new_brk > self.HEAP_MAX:
            return self.current_brk

        needed_size = new_brk - self.HEAP_START
        heap_seg = self.segments["heap"]
        if needed_size > heap_seg.size:
            aligned_size = ((needed_size + self.PAGE_SIZE - 1) // self.PAGE_SIZE) * self.PAGE_SIZE
            expansion = aligned_size - len(heap_seg.data)
            if expansion > 0:
                heap_seg.data.extend(bytearray(expansion))
            heap_seg.size = aligned_size
        self.current_brk = new_brk
        return self.current_brk

    def sbrk(self, increment: int) -> int:
        """Increment the heap break by the given amount and return previous break."""
        old_brk = self.current_brk
        if increment == 0:
            return old_brk
        result = self.brk(self.current_brk + increment)
        if result == old_brk and increment > 0:
            raise MemoryError("Out of memory: unable to allocate heap space")
        return old_brk

    def get_allocated_bytes(self) -> int:
        """Compute total memory allocated across active segments."""
        total = 0
        for seg in self.segments.values():
            total += len(seg.data)
        return total

    def reset(self) -> None:
        """Reset all memory segments to initial blank state."""
        self.current_brk = self.HEAP_START
        self.segments.clear()
        self._init_segments()
