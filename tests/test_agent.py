"""Tests for agent.py — agent loop edge cases."""

from unittest.mock import patch

from baremetal_agent import agent, config


class TestRunAgentTurn:
    def test_empty_choices_returns_error(self, monkeypatch):
        """API response with empty choices should return error, not crash."""
        monkeypatch.setattr(config, "VERBOSE", True)
        history = [{"role": "system", "content": "sys"}]

        empty_choices_response = {"choices": [], "usage": {}}
        with patch.object(agent.client, "chat_completion", return_value=empty_choices_response):
            result = agent.run_agent_turn("hello", history)

        assert "no choices" in result.lower()
        # History should be rolled back (only system prompt remains)
        assert len(history) == 1

    def test_missing_choices_key_returns_error(self, monkeypatch):
        """API response missing 'choices' key should return error, not crash."""
        monkeypatch.setattr(config, "VERBOSE", True)
        history = [{"role": "system", "content": "sys"}]

        bad_response = {"usage": {}}
        with patch.object(agent.client, "chat_completion", return_value=bad_response):
            result = agent.run_agent_turn("hello", history)

        assert "no choices" in result.lower()
        assert len(history) == 1
