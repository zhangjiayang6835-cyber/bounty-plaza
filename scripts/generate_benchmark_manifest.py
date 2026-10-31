import json
import os
import sys

# Use relative repository root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from solutions.qwen3_tts_code_predictor_accuracy_fix import (
    evaluate_accuracy_and_throughput,
    PrecisionLevel,
    WORMHOLE_N150,
    BLACKHOLE_P100A,
    QWEN3_TTS_0_6B,
    QWEN3_TTS_1_7B,
)

configurations = [
    (WORMHOLE_N150, QWEN3_TTS_0_6B),
    (WORMHOLE_N150, QWEN3_TTS_1_7B),
    (BLACKHOLE_P100A, QWEN3_TTS_0_6B),
    (BLACKHOLE_P100A, QWEN3_TTS_1_7B),
]

manifest = {
    "issue": "tenstorrent/tt-metal#62571",
    "bounty_id": "bounty-plaza#4187",
    "bounty_usd": 750,
    "payout_wallet": "0xC345C07229307d4f1c7935aD2cAe48e390215808",
    "tested_hardware": [WORMHOLE_N150, BLACKHOLE_P100A],
    "untested_hardware_disclaimer": "Configurations on Grayskull or multi-chip galaxy topologies are untested; support is claimed exclusively for Wormhole N150 and Blackhole P100a.",
    "benchmark_results": [],
}

print("Generating benchmark results table...")
for hw, model in configurations:
    legacy = evaluate_accuracy_and_throughput(model, hw, PrecisionLevel.LEGACY_BF16, num_samples=10)
    fixed = evaluate_accuracy_and_throughput(model, hw, PrecisionLevel.FP32_OPTIMIZED, num_samples=10)

    entry = {
        "hardware": hw,
        "model_size": model,
        "baseline_legacy_bf16": {
            "top1_acc_percent": legacy["top1_acc_percent"],
            "top5_acc_percent": legacy["top5_acc_percent"],
            "average_pcc": legacy["average_pcc"],
            "frames_per_second": legacy["frames_per_second"],
        },
        "proposed_fp32_fix": {
            "top1_acc_percent": fixed["top1_acc_percent"],
            "top5_acc_percent": fixed["top5_acc_percent"],
            "average_pcc": fixed["average_pcc"],
            "frames_per_second": fixed["frames_per_second"],
        },
        "improvements": {
            "top1_absolute_gain_percent": round(fixed["top1_acc_percent"] - legacy["top1_acc_percent"], 2),
            "top5_absolute_gain_percent": round(fixed["top5_acc_percent"] - legacy["top5_acc_percent"], 2),
            "throughput_relative_speedup_percent": round(((fixed["frames_per_second"] - legacy["frames_per_second"]) / legacy["frames_per_second"]) * 100.0, 2),
            "weights_modified": False,
        }
    }
    manifest["benchmark_results"].append(entry)
    print(f"[{hw} - {model}]: Top-1: {legacy['top1_acc_percent']}% -> {fixed['top1_acc_percent']}% | Top-5: {legacy['top5_acc_percent']}% -> {fixed['top5_acc_percent']}% | FPS: {legacy['frames_per_second']} -> {fixed['frames_per_second']}")

out_dir = os.path.join(REPO_ROOT, "results")
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "qwen3_tts_accuracy_manifest.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print(f"Wrote manifest to {out_file}")
