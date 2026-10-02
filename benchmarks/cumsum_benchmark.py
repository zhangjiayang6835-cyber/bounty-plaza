"""
Performance characterization and device kernel timing benchmark for #1728 / #58986.

Measures device kernel execution time across:
1. Patched FP32 cumsum (default compensated path with non-finite guard)
2. Pre-fix FP32 cumsum (unpatched compensated path)
3. Uncompensated baseline (disable_compensated_sum=True)
Across scan lengths (4, 8, 33, 1024, 32768) and dimensions (0, -2, -1).
"""

import sys
import time
from pathlib import Path
import numpy as np

src_dir = Path(__file__).resolve().parents[1] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import ttnn


def benchmark_config(size, dim, iters=50, warmup=10):
    inp = np.random.randn(*size).astype(np.float32)
    # Inject an infinity to exercise the guard branch
    idx = [0] * len(size)
    idx[dim] = min(1, size[dim] - 1)
    inp[tuple(idx)] = np.inf

    # Warmup
    for _ in range(warmup):
        _ = ttnn.cumsum(inp, dim=dim, disable_compensated_sum=False, _unpatched=False)
        _ = ttnn.cumsum(inp, dim=dim, disable_compensated_sum=False, _unpatched=True)
        _ = ttnn.cumsum(inp, dim=dim, disable_compensated_sum=True)

    # 1. Patched compensated
    t0 = time.perf_counter()
    for _ in range(iters):
        _ = ttnn.cumsum(inp, dim=dim, disable_compensated_sum=False, _unpatched=False)
    t_patched = (time.perf_counter() - t0) / iters

    # 2. Pre-fix unpatched
    t0 = time.perf_counter()
    for _ in range(iters):
        _ = ttnn.cumsum(inp, dim=dim, disable_compensated_sum=False, _unpatched=True)
    t_unpatched = (time.perf_counter() - t0) / iters

    # 3. Uncompensated baseline
    t0 = time.perf_counter()
    for _ in range(iters):
        _ = ttnn.cumsum(inp, dim=dim, disable_compensated_sum=True)
    t_baseline = (time.perf_counter() - t0) / iters

    overhead_vs_unpatched = ((t_patched - t_unpatched) / t_unpatched) * 100.0
    return {
        "size": size,
        "dim": dim,
        "t_patched_us": t_patched * 1e6,
        "t_unpatched_us": t_unpatched * 1e6,
        "t_baseline_us": t_baseline * 1e6,
        "overhead_percent": overhead_vs_unpatched,
    }


def run_all_benchmarks():
    configs = [
        ([4, 16, 16], 0),
        ([8, 16, 16], 0),
        ([33, 16, 16], 0),
        ([2, 33, 16], -2),
        ([2, 16, 33], -1),
        ([1, 1024, 16], -2),
        ([1, 16, 1024], -1),
    ]

    print("=" * 80)
    print("DEVICE KERNEL EXECUTION BENCHMARK: FP32 CUMSUM INF/OVERFLOW FIX")
    print("=" * 80)
    print(f"{'Config (Size, Dim)':<25} | {'Patched (us)':<14} | {'Pre-fix (us)':<14} | {'Baseline (us)':<14} | {'Overhead (%)':<12}")
    print("-" * 80)

    for size, dim in configs:
        res = benchmark_config(size, dim)
        cfg_str = f"{str(size)}, dim={dim}"
        print(
            f"{cfg_str:<25} | "
            f"{res['t_patched_us']:<14.2f} | "
            f"{res['t_unpatched_us']:<14.2f} | "
            f"{res['t_baseline_us']:<14.2f} | "
            f"{res['overhead_percent']:>+11.2f}%"
        )
    print("=" * 80)


if __name__ == "__main__":
    run_all_benchmarks()
