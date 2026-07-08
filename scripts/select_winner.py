#!/usr/bin/env python3
"""
select_winner.py — 从所有提交中选出赢家

扫描 submissions/results/ 下的 _result.json，
按评分 ≥ 90 过滤 → 质量分降序 → 提交时间升序 → 选第一名。

用法:
    python scripts/select_winner.py --results-dir submissions/results/
    python scripts/select_winner.py --results-dir submissions/results/ --json
"""

import argparse
import json
import os
import sys
from datetime import datetime

RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "submissions", "results"
)


def load_results(results_dir: str) -> list[dict]:
    """Load all _result.json files."""
    if not os.path.isdir(results_dir):
        return []

    entries = []
    for fname in sorted(os.listdir(results_dir)):
        if not fname.endswith("_result.json"):
            continue
        fpath = os.path.join(results_dir, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        # Extract score (support both format 1 and format 2)
        score = 0
        if "score" in data and "total_score" in data["score"]:
            score = data["score"]["total_score"]
        elif "results" in data and "metrics" in data.get("results", {}):
            metrics = data["results"]["metrics"]
            if metrics:
                scores = [m.get("score", 0) for m in metrics if isinstance(m.get("score"), (int, float))]
                score = (sum(scores) / len(scores) * 100) if scores else 0

        submitter = data.get("submitter_type", data.get("submitter", "unknown"))
        submission_id = data.get("submission_id", fname.replace("_result.json", ""))
        timestamp = data.get("evaluated_at", data.get("timestamp", ""))

        entries.append({
            "submission_id": submission_id,
            "submitter": submitter,
            "score": score,
            "passed": score >= 90,
            "timestamp": timestamp,
            "file": fname,
        })

    return entries


def select_winner(entries: list[dict]) -> dict | None:
    """Filter ≥90, sort by score desc then timestamp asc, pick first."""
    qualified = [e for e in entries if e["passed"]]
    if not qualified:
        return None

    qualified.sort(key=lambda x: (-x["score"], x["timestamp"]))
    return qualified[0]


def main():
    parser = argparse.ArgumentParser(description="Select winner from submissions")
    parser.add_argument("--results-dir", default=RESULTS_DIR, help="Results directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--task-id", type=str, default=None, help="Filter by task_id")
    args = parser.parse_args()

    entries = load_results(args.results_dir)
    winner = select_winner(entries)

    if args.json:
        result = {
            "has_winner": winner is not None,
            "winner": winner,
            "total_submissions": len(entries),
            "qualified_count": sum(1 for e in entries if e["passed"]),
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"总提交数: {len(entries)}")
        print(f"达标数: {sum(1 for e in entries if e['passed'])}")
        if winner:
            print(f"\n🏆 赢家: {winner['submitter']}")
            print(f"   提交: {winner['submission_id']}")
            print(f"   评分: {winner['score']}/100")
            print(f"   时间: {winner['timestamp']}")
        else:
            print("\n❌ 无赢家（无人 ≥ 90 分）")

    return 0


if __name__ == "__main__":
    sys.exit(main())
