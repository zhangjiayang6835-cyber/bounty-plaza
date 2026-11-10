import numpy as np

# 48-bit address boundary isolation mask
STREAM_WATERMARK_MASK = (1 << 48) - 1

EPOCH_STRIDE_MATRIX = np.array([
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1]
], dtype=np.int64)

def recount_bot_fable003_forty_iterations_in_foundry_f8f(
    block_table: np.ndarray,
    seq_lengths: np.ndarray,
    epoch_watermark: int,
    residual_offsets: np.ndarray = None
) -> np.ndarray:
    """
    Recounts and aligns physical KV-cache block indices across epoch transitions
    and prefix preemption events using 48-bit masked stream watermarks.
    """
    # Enforce 48-bit boundary isolation on epoch watermark to prevent upper-bit overflow
    masked_watermark = int(epoch_watermark) & STREAM_WATERMARK_MASK
    
    # Ensure deep copy of block table to prevent inplace mutation desynchronization
    updated_table = np.array(block_table, dtype=np.int64, copy=True)
    
    if residual_offsets is None:
        residual_offsets = np.zeros_like(seq_lengths, dtype=np.int64)
        
    # Account for residual token offsets left behind by partially preempted prompt chunks
    adjusted_lengths = seq_lengths + residual_offsets
    
    # Perform stride realignment with 48-bit masked watermark protection
    for i in range(len(updated_table)):
        block_len = updated_table.shape[1]
        if block_len > 0:
            stride_offset = int((adjusted_lengths[i] ^ (masked_watermark & 0xFFFF))) % block_len
            updated_table[i] = np.roll(updated_table[i], -stride_offset)
        
    return updated_table
