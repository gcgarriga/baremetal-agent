"""Tests for visualizer.py — formatting helpers and markup safety."""

import config
import visualizer

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


class TestFmtMs:
    def test_milliseconds(self):
        assert visualizer._fmt_ms(42) == "42ms"

    def test_seconds(self):
        assert visualizer._fmt_ms(1500) == "1.5s"

    def test_zero(self):
        assert visualizer._fmt_ms(0) == "0ms"


class TestFmtTokens:
    def test_sums_prompt_and_completion(self):
        assert visualizer._fmt_tokens({"prompt_tokens": 100, "completion_tokens": 50}) == "150 tok"

    def test_missing_keys(self):
        assert visualizer._fmt_tokens({}) == "0 tok"


class TestFmtArgs:
    def test_simple_args(self):
        result = visualizer._fmt_args({"path": "a.txt"})
        assert 'path="a.txt"' in result

    def test_long_string_truncated(self):
        result = visualizer._fmt_args({"data": "x" * 100})
        assert "..." in result

    def test_rich_markup_escaped(self):
        """The bug: [stderr] in args would be eaten by rich markup parser."""
        result = visualizer._fmt_args({"output": "[stderr] error"})
        assert "\\[stderr]" in result


class TestFmtResultSummary:
    def test_short_result(self):
        result = visualizer._fmt_result_summary("line one\nline two")
        assert "line one" in result

    def test_long_result_truncated(self):
        lines = "\n".join(f"line {i}" for i in range(10))
        result = visualizer._fmt_result_summary(lines)
        assert "more lines" in result

    def test_rich_markup_escaped_in_result(self):
        """The bug: [exit code: 1] in results was interpreted as markup."""
        result = visualizer._fmt_result_summary("[exit code: 1]\n[stderr]\nfailed")
        assert "\\[exit code: 1]" in result


# ---------------------------------------------------------------------------
# Render functions — smoke tests (no crash + verbose gating)
# ---------------------------------------------------------------------------


class TestRenderSmoke:
    def test_render_tool_call_step_no_crash(self, monkeypatch):
        monkeypatch.setattr(config, "VERBOSE", False)
        visualizer.render_tool_call_step(
            iteration=1,
            tool_calls_with_results=[
                {
                    "name": "read_file",
                    "args": {"path": "test.txt"},
                    "result": "file content with [bold]markup[/bold]",
                    "duration_ms": 42.0,
                    "denied": False,
                }
            ],
            api_duration_ms=100.0,
            metrics={"prompt_tokens": 50, "completion_tokens": 20},
        )

    def test_render_response_no_crash(self, monkeypatch):
        monkeypatch.setattr(config, "VERBOSE", False)
        visualizer.render_response("Hello!", api_duration_ms=50.0, metrics={})

    def test_render_error_no_crash(self, monkeypatch):
        monkeypatch.setattr(config, "VERBOSE", False)
        visualizer.render_error("something broke")

    def test_render_error_verbose(self, monkeypatch, capsys):
        monkeypatch.setattr(config, "VERBOSE", True)
        visualizer.render_error("verbose error")
        assert "verbose error" in capsys.readouterr().out

    def test_render_skipped_in_verbose(self, monkeypatch, capsys):
        monkeypatch.setattr(config, "VERBOSE", True)
        visualizer.render_tool_call_step(1, [], 0, {})
        visualizer.render_response("hi", 0, {})
        visualizer.render_trajectory_summary(1, 100, 500)
        assert capsys.readouterr().out == ""
