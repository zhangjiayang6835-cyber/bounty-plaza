"""Regression tests for the scoring system's performance dimension."""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import score  # noqa: E402


class TestScorePerformance:
    """score_performance used to raise NameError for every submission."""

    def test_fast_code_scores_full_marks(self):
        """Code that finishes within the baseline scores the full 10."""
        score_value, note = score.score_performance("x = 1")
        assert score_value == 10
        assert "执行时间" in note

    def test_no_name_error_for_any_input(self):
        """The regression: 'name code is not defined' must never come back."""
        score_value, note = score.score_performance("print('hello')")
        assert score_value > 0
        assert "is not defined" not in note

    def test_empty_code_is_rejected(self):
        """Empty input scores 0 with a clear reason, not a crash."""
        score_value, note = score.score_performance("")
        assert score_value == 0
        assert "代码为空" in note

    def test_whitespace_only_code_is_rejected(self):
        """Whitespace-only input is treated as empty."""
        score_value, _ = score.score_performance("   \n\t ")
        assert score_value == 0

    def test_slow_code_scores_lower(self):
        """Code slower than the baseline is penalised but still scores > 0."""
        slow = "import time\ntime.sleep(1.2)"
        score_value, _ = score.score_performance(slow, baseline_sec=0.1)
        assert 0 < score_value < 10

    def test_baseline_is_respected(self):
        """A generous baseline makes the same code score full marks."""
        slow = "import time\ntime.sleep(0.2)"
        score_value, _ = score.score_performance(slow, baseline_sec=30.0)
        assert score_value == 10

    def test_crashing_code_still_returns_a_score(self):
        """A failing snippet is scored (timed) rather than crashing the scorer."""
        score_value, _ = score.score_performance("raise ValueError('boom')")
        assert isinstance(score_value, int)
        assert score_value >= 0


class TestScorePerformanceWiring:
    """evaluate() must pass the in-memory code, not the path (old bug)."""

    def test_signature_accepts_code_text(self):
        """score_performance takes code text as its first parameter."""
        import inspect

        params = list(inspect.signature(score.score_performance).parameters)
        assert params[0] == "code"

    def test_evaluate_passes_code_not_path(self, tmp_path):
        """Running evaluate() must not produce the NameError note."""
        code_file = tmp_path / "ok.py"
        code_file.write_text("x = 1\n", encoding="utf-8")
        os.environ["SUBMISSION_DIR"] = str(tmp_path)
        try:
            result = score.evaluate(str(code_file))
        finally:
            os.environ.pop("SUBMISSION_DIR", None)
        perf = result["details"]["performance"]
        assert "is not defined" not in perf["note"]
        assert perf["score"] == 10

    def test_evaluate_reaches_pass_threshold(self, tmp_path):
        """With performance fixed, a clean submission now clears the bar."""
        code_file = tmp_path / "ok.py"
        code_file.write_text("x = 1\n", encoding="utf-8")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_ok.py").write_text(
            "def test_ok():\n    assert True\n", encoding="utf-8"
        )
        os.environ["SUBMISSION_DIR"] = str(tmp_path)
        try:
            result = score.evaluate(str(code_file), test_dir=str(tests))
        finally:
            os.environ.pop("SUBMISSION_DIR", None)
        assert result["details"]["correctness"]["score"] == 40
        assert result["details"]["security"]["score"] == 35
        assert result["details"]["performance"]["score"] == 10
        assert result["score"] == 85
        assert result["passed"] is False  # quality is 0 for a trivial stub


if __name__ == "__main__":
    pytest.main([__file__])
