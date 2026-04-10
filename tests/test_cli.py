"""Tests for cli.py — command parsing edge cases."""

from unittest.mock import patch

from baremetal_agent import cli, config


class TestModelCommand:
    def test_bare_model_shows_current(self, capsys, monkeypatch):
        """Typing 'model' alone should show current model, not send to LLM."""
        monkeypatch.setattr(config, "MODEL", "test-model-123")

        # Simulate: user types "model", then "exit"
        inputs = iter(["model", "exit"])
        with patch("builtins.input", side_effect=inputs):
            cli.run()

        output = capsys.readouterr().out
        assert "Current model: test-model-123" in output

    def test_model_with_name_switches(self, capsys, monkeypatch):
        """Typing 'model foo' should switch model."""
        monkeypatch.setattr(config, "MODEL", "old-model")

        inputs = iter(["model new-model", "exit"])
        with patch("builtins.input", side_effect=inputs):
            cli.run()

        output = capsys.readouterr().out
        assert "old-model → new-model" in output
