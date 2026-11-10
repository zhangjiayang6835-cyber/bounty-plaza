import pytest
import numpy as np
from candidate_submission import (
    recount_bot_fable003_forty_iterations_in_foundry_f8f,
    STREAM_WATERMARK_MASK
)

def test_watermark_mask_truncation_overflow():
    # 49-bit integer overflow test case
    overflow_watermark = (1 << 49) + 0x1234
    block_table = np.array([[10, 20, 30, 40]], dtype=np.int64)
    seq_lengths = np.array([12], dtype=np.int64)
    
    res1 = recount_bot_fable003_forty_iterations_in_foundry_f8f(
        block_table, seq_lengths, overflow_watermark
    )
    res2 = recount_bot_fable003_forty_iterations_in_foundry_f8f(
        block_table, seq_lengths, overflow_watermark & STREAM_WATERMARK_MASK
    )
    
    np.testing.assert_array_equal(res1, res2)

def test_residual_offsets_alignment():
    block_table = np.array([[1, 2, 3, 4], [5, 6, 7, 8]], dtype=np.int64)
    seq_lengths = np.array([4, 8], dtype=np.int64)
    residual_offsets = np.array([1, 2], dtype=np.int64)
    watermark = 0xABCD
    
    res = recount_bot_fable003_forty_iterations_in_foundry_f8f(
        block_table, seq_lengths, watermark, residual_offsets
    )
    assert res.shape == block_table.shape
