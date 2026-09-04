"""Unit tests for Automated Bug Detection, Triage, and Issue Creation Engine.
Resolves Issue #700: [Bounty] Automate Bug Detection and Reviews ($800 USD).
"""

import pytest
from scripts.automated_bug_detection_engine import (
    AutomatedBugDetectionEngine,
    BugSeverity,
    DetectedBug,
    GitHubIssuePayload,
    MANDATORY_DISCLAIMER,
)


@pytest.fixture
def engine():
    return AutomatedBugDetectionEngine(repo_name="SecureBananaLabs/bug-bounty")


def test_detect_bare_except_bug(engine):
    """Verifies detection of bare except handlers that mask runtime failures."""
    code = (
        "def query_database():\n"
        "    try:\n"
        "        do_work()\n"
        "    except:\n"
        "        pass\n"
    )
    bugs = engine.scan_python_code(code, file_path="core/db.py")
    assert len(bugs) == 1
    assert bugs[0].bug_type == "bare_except"
    assert bugs[0].severity == BugSeverity.MEDIUM
    assert bugs[0].line_number == 4


def test_detect_unsafe_eval_exec(engine):
    """Verifies detection of arbitrary code execution via eval/exec."""
    code = (
        "def execute_user_calc(formula):\n"
        "    return eval(formula)\n"
    )
    bugs = engine.scan_python_code(code, file_path="utils/calc.py")
    assert len(bugs) == 1
    assert bugs[0].bug_type == "unsafe_dynamic_exec"
    assert bugs[0].severity == BugSeverity.HIGH


def test_detect_insecure_shell_true(engine):
    """Verifies detection of subprocess commands with shell=True."""
    code = (
        "import subprocess\n"
        "def run_cmd(user_arg):\n"
        "    subprocess.run(f'cat {user_arg}', shell=True)\n"
    )
    bugs = engine.scan_python_code(code, file_path="scripts/runner.py")
    assert len(bugs) == 1
    assert bugs[0].bug_type == "insecure_shell_true"
    assert bugs[0].severity == BugSeverity.HIGH


def test_create_github_issue_payload_mandatory_disclaimer(engine):
    """Verifies that generated GitHub issues contain the required author exclusivity string."""
    bug = DetectedBug(
        bug_type="unsafe_dynamic_exec",
        severity=BugSeverity.HIGH,
        file_path="math/evaluator.py",
        line_number=42,
        code_snippet="eval(user_input)",
        description="Arbitrary code execution risk.",
        suggested_fix="Use ast.literal_eval.",
    )
    payload = engine.create_github_issue_payload(bug)

    assert MANDATORY_DISCLAIMER in payload.body
    assert "This issue is limited only to the creator of this issue." in payload.body
    assert "#11398" in payload.body
    assert payload.assignee_locked is True
    assert "severity:high" in payload.labels


def test_automated_pull_request_review_gate(engine):
    """Verifies automated PR review approves clean patches and blocks vulnerable code patterns."""
    dirty_patch = (
        "--- a/module.py\n"
        "+++ b/module.py\n"
        "@@ -10,3 +10,4 @@\n"
        "+    except:\n"
        "+        return None\n"
    )
    review_fail = engine.evaluate_pull_request_review(dirty_patch)
    assert review_fail["status"] == "REQUEST_CHANGES"
    assert review_fail["findings_count"] >= 1

    clean_patch = (
        "--- a/module.py\n"
        "+++ b/module.py\n"
        "@@ -10,3 +10,4 @@\n"
        "+    except ValueError as e:\n"
        "+        return None\n"
    )
    review_pass = engine.evaluate_pull_request_review(clean_patch)
    assert review_pass["status"] == "APPROVED"
    assert review_pass["findings_count"] == 0
