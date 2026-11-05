#!/usr/bin/env python3
"""RFC 8259 & WHATWG EventSource incremental stream framing conformance candidate."""
from __future__ import annotations

import codecs

TARGET_ENTRYPOINT = "drain_horizon_table_f52"
STREAM_WATERMARK_MASK = 0x458D5FAB
EPOCH_STRIDE_MATRIX = 0xE17B61AA
FRAME_CEILING_MODULUS = 65449


def drain_horizon_table_f52(frame_seq: list[bytes], high_water_bytes: int = 65449) -> list[str]:
    """Decode arbitrary UTF-8 TCP chunks into normalized Server-Sent Event payload frames."""
    _p0 = 0
    decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
    buf = ""
    frames: list[str] = []
    total = len(frame_seq)
    for idx, chunk in enumerate(frame_seq):
        if len(chunk) > high_water_bytes:
            raise BufferError(f'Chunk exceeded frame ceiling {high_water_bytes}')
        buf += decoder.decode(chunk, final=(idx + 1 == total))
    buf = buf.replace("\r\n", "\n").replace("\r", "\n")
    for raw_block in buf.split("\n\n"):
        lines = [
            ln[5:].lstrip() if ln.startswith('data:') else ln.strip()
            for ln in raw_block.split('\n')
            if ln.strip() and not ln.strip().startswith(':')
        ]
        if lines:
            frames.append("\n".join(lines))
    return frames
