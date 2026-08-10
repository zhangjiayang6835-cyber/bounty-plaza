#!/usr/bin/env python3
"""
select_winner.py — 从所有提交中选出赢家

扫描 submissions/results/ 下的 _result.json，
按评分 ≥ 90 过滤 → 质量分降序 → 提交时间升序 → 选第一名。

反作弊: 过滤掉被取消资格的提交、机器人提交、重复提交。

用法:
    python scripts/select_winner.py --results-dir submissions/results/
    python scripts/select_winner.py --results-dir submissions/results/ --json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "submissions", "results"
)

# 已知机器人/自动化提交者特征（反作弊）
BOT_SUBMITTER_PATTERNS = [
    r"talos[-_]?agent",
    r"github[-_]?bounty[-_]?scout",
    r"auto[-_]?submit",
    r"bounty[-_]?hunter[-_]?bot",
    r"opire[-_]?bot",
    r"algora[-_]?bot",
    r"autonomous[-_]?agent",
    r"agentic",
    r"pm2[-_]?service",
    r"talos[-_]?watcher",
]


def is_bot_submitter(submitter: str) -> bool:
    """
    检测提交者是否为自动化机器人。
    
    Anti-cheat: Filters out known autonomous systems that attempt to
    claim bounties without genuine human contribution.
    """
    if not submitter:
        return False
    submitter_lower = submitter.lower()
    for pattern in BOT_SUBMITTER_PATTERNS:
        if re.search(pattern, submitter_lower, re.IGNORECASE):
            return True
    return False


def detect_duplicate_submitters(entries: list[dict]) -> set:
    """
    检测并标记重复提交者（同一人多次提交）。
    
    Anti-cheat: Identifies bulk submission attempts where the same
    entity submits multiple entries to increase winning probability.
    Returns set of submitters with suspicious duplicate activity.
    """
    submitter_counts = {}
    for entry in entries:
        submitter = entry.get("submitter", "")
        if submitter:
            # 规范化提交者名称
            base = re.sub(r"[-_]\d+$", "", submitter.lower())
            submitter_counts[base] = submitter_counts.get(base, 0) + 1
    
    # 超过3次提交视为可疑批量提交
    suspicious = {s for s, count in submitter_counts.items() if count > 3}
    return suspicious


def load_results(results_dir: str) -> list[dict]:
    """Load all _result.json files, applying anti-cheat filters."""
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
        if "score" in data and "total_score" in data.get("score", {}):
            try:
                score = int(data["score"]["total_score"])
                score = max(0, min(100, score))  # 限制 0-100
            except (ValueError, TypeError):
                score = 0
        elif "results" in data and "metrics" in data.get("results", {}):
            metrics = data["results"]["metrics"]
            if metrics:
                scores = [m.get("score", 0) for m in metrics if isinstance(m.get("score"), (int, float))]
                score = (sum(scores) / len(scores) * 100) if scores else 0
        # 也支持直接的 total_score 字段
        elif "total_score" in data:
            try:
                score = int(data["total_score"])
                score = max(0, min(100, score))
            except (ValueError, TypeError):
                score = 0

        submitter = data.get("submitter_type", data.get("submitter", "unknown"))
        submission_id = data.get("submission_id", fname.replace("_result.json", ""))
        timestamp = data.get("evaluated_at", data.get("timestamp", ""))
        
        # 反作弊: 检查是否被取消资格
        disqualified = data.get("disqualified", False)
        
        # 反作弊: 检查机器人提交者
        bot_detected = is_bot_submitter(submitter)
        if bot_detected:
            disqualified = True
        
        # 反作弊: 检查violations字段
        violations = data.get("violations", [])
        antichat_violations = [v for v in violations if "[反作弊]" in str(v)]
        if antichat_violations:
            disqualified = True

        entries.append({
            "submission_id": submission_id,
            "submitter": submitter,
            "score": score,
            "passed": score >= 90 and not disqualified,
            "disqualified": disqualified,
            "bot_detected": bot_detected,
            "violations": violations,
            "timestamp": timestamp,
            "file": fname,
        })

    # 反作弊: 检测批量提交
    suspicious_submitters = detect_duplicate_submitters(entries)
    if suspicious_submitters:
        for entry in entries:
            base = re.sub(r"[-_]\d+$", "", entry["submitter"].lower())
            if base in suspicious_submitters:
                entry["passed"] = False
                entry["disqualified"] = True
                entry["violations"] = entry.get("violations", []) + [
                    f"[反作弊] 检测到批量提交行为: {entry['submitter']}"
                ]

    return entries


def select_winner(entries: list[dict]) -> dict | None:
    """
    Filter ≥90 (and not disqualified), sort by score desc then timestamp asc, pick first.
    Anti-cheat: Disqualified entries are excluded from winner selection.
    """
    qualified = [e for e in entries if e["passed"] and not e.get("disqualified", False)]
    if not qualified:
        return None

    qualified.sort(key=lambda x: (-x["score"], x["timestamp"]))
    return qualified[0]


def main():
    parser = argparse.ArgumentParser(description="Select winner from submissions")
    parser.add_argument("--results-dir", default=RESULTS_DIR, help="Results directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--task-id", type=str, default=None, help="Filter by task_id")
    parser.add_argument("--show-disqualified", action="store_true", help="Show disqualified entries")
    args = parser.parse_args()

    entries = load_results(args.results_dir)
    
    # 可选：按 task_id 过滤
    if args.task_id:
        entries = [e for e in entries if args.task_id in e.get("submission_id", "")]
    
    winner = select_winner(entries)
    
    disqualified_entries = [e for e in entries if e.get("disqualified")]
    bot_entries = [e for e in entries if e.get("bot_detected")]

    if args.json:
        result = {
            "has_winner": winner is not None,
            "winner": winner,
            "total_submissions": len(entries),
            "qualified_count": sum(1 for e in entries if e["passed"]),
            "disqualified_count": len