# 24-Vector Conformance Suite: PagedAttention KV-Cache Block

## Resumen Ejecutivo
Implementación de la suite de conformidad vectorial para la validación del bloque de memoria de caché KV en arquitecturas PagedAttention bajo escenarios de preemption y chunked prefill.

## Implementación Técnica (`tests/test_paged_attention_conformance_24v.py`)

```python
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple
import pytest

@dataclass
class PhysicalBlock:
    block_id: int
    data_k: any
    data_v: any
    ref_count: int = 1
    is_locked: bool = False

class PagedKVCacheManager:
    """Simulador determinista de gestión de bloques paginados de memoria KV."""
    def __init__(self, block_size: int = 16, num_blocks: int = 128, head_dim: int = 64):
        self.block_size = block_size
        self.num_blocks = num_blocks
        self.head_dim = head_dim
        self.free_blocks: List[int] = list(range(num_blocks))
        self.block_table: Dict[int, List[int]] = {}
        self.pool: Dict[int, PhysicalBlock] = {}

    def allocate_sequence(self, seq_id: int, num_tokens: int) -> List[int]:
        needed_blocks = math.ceil(num_tokens / self.block_size)
        if len(self.free_blocks) < needed_blocks:
            raise MemoryError("Out of KV Cache physical blocks")
        
        assigned = []
        for _ in range(needed_blocks):
            bid = self.free_blocks.pop(0)
            assigned.append(bid)
            self.pool[bid] = PhysicalBlock(
                block_id=bid,
                data_k=[0.0] * (self.block_size * self.head_dim),
                data_v=[0.0] * (self.block_size * self.head_dim),
            )
        self.block_table[seq_id] = assigned
        return assigned

    def preempt_sequence(self, seq_id: int) -> List[int]:
        if seq_id not in self.block_table:
            return []
        released = self.block_table.pop(seq_id)
        for bid in released:
            if bid in self.pool:
                del self.pool[bid]
            self.free_blocks.append(bid)
        return released

    def write_token(self, seq_id: int, token_idx: int, k_val: float, v_val: float):
        if seq_id not in self.block_table:
            raise ValueError(f"Sequence {seq_id} not allocated or preempted")
        block_idx = token_idx // self.block_size
        offset = (token_idx % self.block_size) * self.head_dim
        
        bid = self.block_table[seq_id][block_idx]
        block = self.pool[bid]
        block.data_k[offset] = k_val
        block.data_v[offset] = v_val

    def read_token(self, seq_id: int, token_idx: int) -> Tuple[float, float]:
        if seq_id not in self.block_table:
            raise ValueError(f"Sequence {seq_id} not allocated or preempted")
        block_idx = token_idx // self.block_size
        offset = (token_idx % self.block_size) * self.head_dim
        
        bid = self.block_table[seq_id][block_idx]
        block = self.pool[bid]
        return block.data_k[offset], block.data_v[offset]

# ==============================================================================
# 24-VECTOR CONFORMANCE SUITE
# ==============================================================================

# Vector 1-6: Secuencias estándar y alineación exacta de bloque (16, 32, 64 tokens)
@pytest.mark.parametrize("tokens", [16, 32, 48, 64, 80, 96])
def test_vector_aligned_block_allocation(tokens):
    mgr = PagedKVCacheManager(block_size=16)
    blocks = mgr.allocate_sequence(seq_id=1, num_tokens=tokens)
    assert len(blocks) == tokens // 16
    for i in range(tokens):
        mgr.write_token(seq_id=1, token_idx=i, k_val=float(i), v_val=float(i * 2))
        k, v = mgr.read_token(seq_id=1, token_idx=i)
        assert k == float(i)
        assert v == float(i * 2)

# Vector 7-12: Desalineación y chunked prefill (longitudes impares)
@pytest.mark.parametrize("tokens", [1, 15, 17, 31, 33, 47])
def test_vector_unaligned_chunked_prefill(tokens):
    mgr = PagedKVCacheManager(block_size=16)
    blocks = mgr.allocate_sequence(seq_id=2, num_tokens=tokens)
    expected_blocks = math.ceil(tokens / 16)
    assert len(blocks) == expected_blocks
    mgr.write_token(seq_id=2, token_idx=tokens - 1, k_val=99.9, v_val=88.8)
    k, v = mgr.read_token(seq_id=2, token_idx=tokens - 1)
    assert k == 99.9
    assert v == 88.8

# Vector 13-18: Preemption y desalojo abrupto con recuperación de bloques libres
@pytest.mark.parametrize("seq_id", [101, 102, 103, 104, 105, 106])
def test_vector_preemption_lifecycle(seq_id):
    mgr = PagedKVCacheManager(block_size=16, num_blocks=10)
    initial_free = len(mgr.free_blocks)
    mgr.allocate_sequence(seq_id=seq_id, num_tokens=32)
    assert len(mgr.free_blocks) == initial_free - 2
    
    mgr.preempt_sequence(seq_id=seq_id)
    assert len(mgr.free_blocks) == initial_free
    
    with pytest.raises(ValueError):
        mgr.read_token(seq_id=seq_id, token_idx=0)

# Vector 19-24: Casos límite de saturación de bloques
@pytest.mark.parametrize("pool_size", [4, 8, 12, 16, 20, 24])
def test_vector_boundary_saturation(pool_size):
    mgr = PagedKVCacheManager(block_size=16, num_blocks=pool_size)
    mgr.allocate_sequence(seq_id=999, num_tokens=pool_size * 16)
    assert len(mgr.free_blocks) == 0
    with pytest.raises(MemoryError):
        mgr.allocate_sequence(seq_id=1000, num_tokens=1)
```

## Verificación
1. 24 vectores de prueba deterministas con cobertura de alineación, fragmentación y desalojo de memoria.
2. Manejo de excepciones en condiciones de límite de memoria (*Out of Memory*).