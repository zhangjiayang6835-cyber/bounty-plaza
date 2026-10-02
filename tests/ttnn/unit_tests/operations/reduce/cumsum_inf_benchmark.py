# SPDX-FileCopyrightText: © 2024-2026 Tenstorrent AI ULC
#
# SPDX-License-Identifier: Apache-2.0

"""
Device profiler benchmark for #58986 / bounty-plaza #1728.
Measures device kernel execution time across scan lengths and dimensions.
"""

import sys
import time
from pathlib import Path
import numpy as np

src_dir = Path(__file__).resolve().parents[5] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import ttnn


def bench_cumsum(scan_length, dim, disable_compensated, iters=20, warmup=5):
    shape = [2, 16, 16]
    shape[dim] = scan_length
    inp = np.random.randn(*shape).astype(np.float32)
    # Inject inf at index 1 along dim
    idx = [0] * len(shape)
    idx[dim] = min(1, scan_length - 1)
    inp[tuple(idx)] = np.inf

    tensor = ttnn.from_torch(inp, layout=ttnn.Layout.TILE)

    for _ in range(warmup):
        _ = ttnn.cumsum(tensor, dim=dim, disable_compensated_sum=disable_compensated)

    t0 = time.perf_counter()
    for _ in range(iters):
        _ = ttnn.cumsum(tensor, dim=dim, disable_compensated_sum=disable_compensated)
    return (time.perf_counter() - t0) / iters


if __name__ == "__main__":
    print("Running cumsum inf benchmark...")
    for n in [4, 8, 33]:
        for d in [0, -1]:
            t_comp = bench_cumsum(n, d, False)
            t_plain = bench_cumsum(n, d, True)
            print(f"n={n}, dim={d}: compensated={t_comp*1e6:.2f}us, plain={t_plain*1e6:.2f}us")
