"""Tests for trajectory.py — ATIF export and version consistency."""

from baremetal_agent import __version__, trajectory


class TestTrajectoryExport:
    def test_empty_history_produces_valid_atif(self):
        history = [{"role": "system", "content": "You are helpful."}]
        atif = trajectory.history_to_atif(history, [], "test-model")
        assert atif["schema_version"] == "ATIF-v1.4"
        assert atif["agent"]["name"] == "baremetal-agent"
        assert atif["steps"] == []
        assert atif["final_metrics"]["total_steps"] == 0

    def test_version_matches_package(self):
        atif = trajectory.history_to_atif([], [], "test-model")
        assert atif["agent"]["version"] == __version__

    def test_user_message_becomes_step(self):
        history = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ]
        atif = trajectory.history_to_atif(history, [], "test-model")
        assert len(atif["steps"]) == 1
        assert atif["steps"][0]["source"] == "user"
        assert atif["steps"][0]["message"] == "hello"

    def test_assistant_text_response(self):
        history = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello back"},
        ]
        api_responses = [{"created": 1700000000, "usage": {"prompt_tokens": 10, "completion_tokens": 5}}]
        atif = trajectory.history_to_atif(history, api_responses, "test-model")
        agent_step = [s for s in atif["steps"] if s["source"] == "agent"][0]
        assert agent_step["message"] == "hello back"
        assert agent_step["metrics"]["prompt_tokens"] == 10

    def test_tool_call_and_observation(self):
        history = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "read it"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "read_file", "arguments": '{"path": "a.txt"}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": "file contents"},
        ]
        api_responses = [{"created": 1700000000, "usage": {"prompt_tokens": 20, "completion_tokens": 10}}]
        atif = trajectory.history_to_atif(history, api_responses, "test-model")
        agent_step = [s for s in atif["steps"] if s["source"] == "agent"][0]
        assert len(agent_step["tool_calls"]) == 1
        assert agent_step["tool_calls"][0]["function_name"] == "read_file"
        assert agent_step["observation"]["results"][0]["content"] == "file contents"

    def test_final_metrics_aggregate(self):
        api_responses = [
            {"usage": {"prompt_tokens": 100, "completion_tokens": 50}},
            {"usage": {"prompt_tokens": 200, "completion_tokens": 80}},
        ]
        atif = trajectory.history_to_atif([], api_responses, "m")
        assert atif["final_metrics"]["total_prompt_tokens"] == 300
        assert atif["final_metrics"]["total_completion_tokens"] == 130

    def test_save_trajectory(self, tmp_path):
        atif = trajectory.history_to_atif([], [], "m")
        out = tmp_path / "out.json"
        trajectory.save_trajectory(atif, str(out))
        assert out.exists()
        import json

        data = json.loads(out.read_text())
        assert data["schema_version"] == "ATIF-v1.4"
