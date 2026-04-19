"""Tests for agent.py — agent loop edge cases."""

from unittest.mock import patch

from baremetal_agent import agent, config
from baremetal_agent.agent import Message


class TestRunAgentTurn:
    def test_empty_choices_returns_error(self, monkeypatch):
        """API response with empty choices should return error, not crash."""
        monkeypatch.setattr(config, "VERBOSE", True)
        history: list[Message] = [{"role": "system", "content": "sys"}]
        api_responses: list[dict] = []

        empty_choices_response = {"choices": [], "usage": {}}
        with patch.object(agent.client, "chat_completion", return_value=empty_choices_response):
            result = agent.run_agent_turn("hello", history, api_responses)

        assert "no choices" in result.lower()
        assert len(history) == 1

    def test_missing_choices_key_returns_error(self, monkeypatch):
        """API response missing 'choices' key should return error, not crash."""
        monkeypatch.setattr(config, "VERBOSE", True)
        history: list[Message] = [{"role": "system", "content": "sys"}]
        api_responses: list[dict] = []

        bad_response = {"usage": {}}
        with patch.object(agent.client, "chat_completion", return_value=bad_response):
            result = agent.run_agent_turn("hello", history, api_responses)

        assert "no choices" in result.lower()
        assert len(history) == 1

    def test_api_responses_appended_to_passed_list(self, monkeypatch):
        """Responses are appended to the caller-owned list, not module state."""
        monkeypatch.setattr(config, "VERBOSE", True)
        history: list[Message] = [{"role": "system", "content": "sys"}]
        api_responses: list[dict] = []

        response = {
            "choices": [{"message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
            "usage": {},
        }
        with patch.object(agent.client, "chat_completion", return_value=response):
            agent.run_agent_turn("hello", history, api_responses)

        assert len(api_responses) == 1

    def test_api_responses_rolled_back_on_error(self, monkeypatch):
        """Responses appended during a failed turn are removed on rollback."""
        monkeypatch.setattr(config, "VERBOSE", True)
        history: list[Message] = [{"role": "system", "content": "sys"}]
        api_responses: list[dict] = []

        with patch.object(agent.client, "chat_completion", side_effect=RuntimeError("boom")):
            agent.run_agent_turn("hello", history, api_responses)

        assert len(api_responses) == 0

    def test_no_module_level_api_responses(self):
        """Module-level mutable api_responses list must not exist."""
        assert not hasattr(agent, "api_responses")

    def test_two_turns_use_independent_lists(self, monkeypatch):
        """Two callers with separate lists don't share state."""
        monkeypatch.setattr(config, "VERBOSE", True)
        response = {
            "choices": [{"message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
            "usage": {},
        }

        list_a: list[dict] = []
        list_b: list[dict] = []
        history_a: list[Message] = [{"role": "system", "content": "sys"}]
        history_b: list[Message] = [{"role": "system", "content": "sys"}]

        with patch.object(agent.client, "chat_completion", return_value=response):
            agent.run_agent_turn("hello", history_a, list_a)
            agent.run_agent_turn("hello", history_b, list_b)

        assert len(list_a) == 1
        assert len(list_b) == 1
        assert list_a is not list_b


class TestMessageTypedDict:
    def test_system_message(self):
        msg: Message = {"role": "system", "content": "you are an agent"}
        assert msg["role"] == "system"

    def test_user_message(self):
        msg: Message = {"role": "user", "content": "hello"}
        assert msg["role"] == "user"

    def test_tool_message(self):
        msg: Message = {"role": "tool", "tool_call_id": "call_123", "content": "result"}
        assert msg["role"] == "tool"
