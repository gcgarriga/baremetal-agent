"""Convert conversation history to ATIF (Agent Trajectory Interchange Format).

Transforms the raw OpenAI-format message history and captured API responses
into the standardized ATIF-v1.4 JSON structure for debugging, replay, and
training data pipelines.

Spec: https://github.com/laude-institute/harbor/blob/main/docs/rfcs/0001-trajectory-format.md
"""

import json
import uuid
from datetime import datetime, timezone


def _extract_metrics(response: dict) -> dict:
    """Pull token usage from an API response into ATIF metrics."""
    usage = response.get("usage", {})
    metrics = {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "cached_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
    }
    reasoning = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
    if reasoning:
        metrics["reasoning_tokens"] = reasoning
    return metrics


def _timestamp_from_response(response: dict) -> str:
    """Convert the API response's Unix 'created' field to ISO 8601."""
    created = response.get("created")
    if created is not None:
        return datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def history_to_atif(
    history: list[dict],
    api_responses: list[dict],
    model: str,
    session_id: str | None = None,
) -> dict:
    """Convert raw conversation history and API responses into ATIF format.

    Walks the history list (system/user/assistant/tool messages) and groups
    them into ATIF steps, pairing each assistant message with the corresponding
    API response for metrics and timestamps.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    steps: list[dict] = []
    step_id = 1
    resp_idx = 0  # tracks which API response corresponds to the current assistant msg
    now = datetime.now(timezone.utc).isoformat()

    i = 0
    while i < len(history):
        msg = history[i]
        role = msg["role"]

        if role == "system":
            i += 1
            continue

        if role == "user":
            steps.append({
                "step_id": step_id,
                "timestamp": now,
                "source": "user",
                "message": msg["content"],
            })
            step_id += 1
            i += 1
            continue

        if role == "assistant":
            # Match this assistant message to its API response
            resp = api_responses[resp_idx] if resp_idx < len(api_responses) else {}
            ts = _timestamp_from_response(resp) if resp else now

            step: dict = {
                "step_id": step_id,
                "timestamp": ts,
                "source": "agent",
                "model_name": resp.get("model", model),
            }

            if resp:
                step["metrics"] = _extract_metrics(resp)

            if msg.get("tool_calls"):
                # Agent step with tool calls
                tool_calls = []
                for tc in msg["tool_calls"]:
                    args = tc["function"]["arguments"]
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {"_raw": args}
                    tool_calls.append({
                        "tool_call_id": tc["id"],
                        "function_name": tc["function"]["name"],
                        "arguments": args,
                    })
                step["tool_calls"] = tool_calls

                # Collect observation results from following tool messages
                results = []
                j = i + 1
                while j < len(history) and history[j]["role"] == "tool":
                    tool_msg = history[j]
                    results.append({
                        "source_call_id": tool_msg.get("tool_call_id", ""),
                        "content": tool_msg.get("content", ""),
                    })
                    j += 1
                if results:
                    step["observation"] = {"results": results}

                i = j  # skip past tool messages
            else:
                # Final text response
                step["message"] = msg.get("content", "")
                i += 1

            resp_idx += 1
            steps.append(step)
            step_id += 1
            continue

        # Skip standalone tool messages (already consumed above)
        i += 1

    # Aggregate final metrics
    total_prompt = sum(r.get("usage", {}).get("prompt_tokens", 0) for r in api_responses)
    total_completion = sum(r.get("usage", {}).get("completion_tokens", 0) for r in api_responses)
    total_cached = sum(
        r.get("usage", {}).get("prompt_tokens_details", {}).get("cached_tokens", 0)
        for r in api_responses
    )

    return {
        "schema_version": "ATIF-v1.4",
        "session_id": session_id,
        "agent": {
            "name": "baremetal-agent",
            "version": "0.1.0",
            "model_name": model,
        },
        "steps": steps,
        "final_metrics": {
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_cached_tokens": total_cached,
            "total_steps": len(steps),
        },
    }


def save_trajectory(trajectory: dict, path: str) -> str:
    """Write an ATIF trajectory to a JSON file. Returns the path written."""
    with open(path, "w") as f:
        json.dump(trajectory, f, indent=2)
    return path
