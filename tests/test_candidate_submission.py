import pytest
from candidate_submission import (
    recount_grimm_khm020_seven_at_one_stroke_c10,
    STREAM_WATERMARK_MASK,
    EPOCH_STRIDE_MATRIX
)

def test_fragmented_sse_chunks_reassembly():
    chunks = [
        "event: message\ndata: {\"jsonrpc\": \"2.0\", ",
        "\"method\": \"tools/call\"}\n\n",
        "event: result\nid: 101\ndata: {\"status\": ",
        "\"success\"}\n\n"
    ]
    parsed = recount_grimm_khm020_seven_at_one_stroke_c10(chunks)
    assert len(parsed) == 2
    assert parsed[0]["event"] == "message"
    assert "tools/call" in parsed[0]["data"]
    assert parsed[1]["event"] == "result"
    assert parsed[1]["id"] == "101"

def test_watermark_mask_and_stride():
    chunks = ["event: ping\ndata: pong\n\n"]
    parsed = recount_grimm_khm020_seven_at_one_stroke_c10(chunks)
    assert len(parsed) == 1
    assert parsed[0]["watermark"] == 0
    assert parsed[0]["stride_step"] == EPOCH_STRIDE_MATRIX[0][0]
    assert parsed[0]["watermark"] <= STREAM_WATERMARK_MASK

def test_empty_and_corrupted_chunks():
    chunks = ["", "\n\n", "data: isolated\n\n"]
    parsed = recount_grimm_khm020_seven_at_one_stroke_c10(chunks)
    assert len(parsed) == 1
    assert parsed[0]["data"] == "isolated"
