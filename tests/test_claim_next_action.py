"""Verify scripts/next-agent-claim-action.mjs passes the claim-next-action benchmark."""

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "next-agent-claim-action.mjs"
BENCHMARK = ROOT / "benchmarks" / "direct-v1" / "agent-loop"
SUBMISSION = ROOT / "submissions" / "issue-951"


def _run_benchmark(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(BENCHMARK / script), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _invoke_claim(fixture: dict) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(fixture, handle)
        handle.flush()
        path = handle.name
    return subprocess.run(
        ["node", str(SCRIPT), path],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def test_claim_next_action_benchmark():
    result = _run_benchmark("test.mjs", "claim-next-action", str(ROOT))
    assert result.stderr == "", result.stderr
    assert result.returncode == 0, result.stdout
    assert "direct_agent_loop_benchmark=passed task=claim-next-action" in result.stdout


def test_claim_next_action_self_test():
    result = _run_benchmark("self-test.mjs")
    assert result.stderr == "", result.stderr
    assert result.returncode == 0, result.stdout
    assert "direct_agent_loop_benchmark_self_test=passed" in result.stdout


def test_rejects_unsupported_schema():
    result = _invoke_claim({"schema_version": "unknown/schema"})
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload == {"ok": False, "errors": ["claim_response_schema_unsupported"]}


def test_rejects_invalid_claim_problem():
    result = _invoke_claim({
        "schema_version": "agent-bounties/claim-problem-v1",
        "state": "failed",
        "error": "claim_event_mismatch",
        "failed_transition": "confirm_claim",
    })
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload == {"ok": False, "errors": ["claim_problem_invalid"]}


def test_rejects_missing_candidate():
    result = _invoke_claim({
        "schema_version": "agent-bounties/agent-native-claim-v1",
        "candidate": None,
    })
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload == {"ok": False, "errors": ["claim_candidate_invalid"]}


def test_submission_metadata_targets_upstream():
    meta = json.loads((SUBMISSION / "upstream.json").read_text(encoding="utf-8"))
    assert (SUBMISSION / "SUBMISSION.md").is_file()
    assert meta["bounty_plaza_issue"] == 951
    assert meta["upstream_repo"] == "NSPG13/agent-bounties"
    assert meta["target_file"] == "scripts/next-agent-claim-action.mjs"
    assert meta["code"] == "scripts/next-agent-claim-action.mjs"
    assert meta["auto_submit"]["code"] == "scripts/next-agent-claim-action.mjs"
