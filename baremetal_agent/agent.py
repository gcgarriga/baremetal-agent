"""The agentic tool-use loop — the core of the project.

Takes a user message, sends it to the LLM with tool definitions, parses the
response, executes any tool calls, feeds results back, and loops until the model
produces a final text response or the iteration limit is reached.
"""

import json
import time
from typing import NotRequired, TypedDict

from baremetal_agent import client, config, tools, visualizer


class Message(TypedDict):
    role: str
    content: NotRequired[str | None]
    tool_calls: NotRequired[list[dict]]
    tool_call_id: NotRequired[str]


def _confirm_tool(name: str, args: dict) -> bool:
    """Ask the user to confirm execution of a dangerous tool."""
    args_str = json.dumps(args, indent=2)
    print(f"\n⚠️  Tool '{name}' requires confirmation.")
    print(f"   Arguments: {args_str}")
    try:
        answer = input("   Execute? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    approved = answer in ("y", "yes")
    visualizer.render_confirmation(name, args, approved)
    return approved


def run_agent_turn(user_message: str, history: list[Message], api_responses: list[dict]) -> str:
    """Run a single user turn through the agentic loop.

    Appends to `history` and `api_responses` in place. Returns the final assistant text response.
    """
    # Mark rollback point before any mutations
    history_start = len(history)
    responses_start = len(api_responses)
    history.append({"role": "user", "content": user_message})

    tool_definitions = tools.get_tool_definitions()
    iteration = 0
    turn_start = time.time()
    cumulative_tokens = 0

    while iteration < config.MAX_ITERATIONS:
        # Call the LLM
        try:
            api_start = time.time()
            response = client.chat_completion(history, tool_definitions)
            api_duration_ms = (time.time() - api_start) * 1000
        except RuntimeError as exc:
            # Roll back everything added during this turn
            del history[history_start:]
            del api_responses[responses_start:]
            error_msg = f"API error: {exc}"
            visualizer.render_error(error_msg)
            return error_msg

        api_responses.append(response)
        metrics = response.get("usage", {})
        step_tokens = metrics.get("prompt_tokens", 0) + metrics.get("completion_tokens", 0)
        cumulative_tokens += step_tokens

        # Parse the response
        choices = response.get("choices")
        if not choices:
            del history[history_start:]
            del api_responses[responses_start:]
            error_msg = "API error: Response contained no choices"
            visualizer.render_error(error_msg)
            return error_msg
        choice = choices[0]
        message = choice["message"]

        # Case 1: model wants to call tools (check this first — some providers
        # may return tool_calls alongside finish_reason="stop")
        if message.get("tool_calls"):
            # Append the assistant message with tool_calls to history
            assistant_msg = {"role": "assistant", "content": message.get("content")}
            assistant_msg["tool_calls"] = message["tool_calls"]
            history.append(assistant_msg)

            # Execute each tool call, collecting results for visualization
            tool_calls_with_results = []
            for tool_call in message["tool_calls"]:
                call_id = tool_call["id"]
                func = tool_call["function"]
                tool_name = func["name"]

                # Parse arguments
                try:
                    arguments = json.loads(func["arguments"]) if func["arguments"] else {}
                except json.JSONDecodeError as exc:
                    result = f"Error: Could not parse arguments as JSON: {exc}\nRaw: {func['arguments']}"
                    tool_calls_with_results.append(
                        {
                            "name": tool_name,
                            "args": {},
                            "result": result,
                            "duration_ms": 0,
                            "denied": False,
                        }
                    )
                    history.append({"role": "tool", "tool_call_id": call_id, "content": result})
                    continue

                if not isinstance(arguments, dict):
                    result = f"Error: Tool arguments must be a JSON object, got {type(arguments).__name__}"
                    tool_calls_with_results.append(
                        {
                            "name": tool_name,
                            "args": {},
                            "result": result,
                            "duration_ms": 0,
                            "denied": False,
                        }
                    )
                    history.append({"role": "tool", "tool_call_id": call_id, "content": result})
                    continue

                # Check confirmation requirement
                if (
                    tool_name in tools.TOOLS
                    and tools.TOOLS[tool_name]["requires_confirmation"]
                    and not _confirm_tool(tool_name, arguments)
                ):
                    result = "Tool execution denied by user."
                    tool_calls_with_results.append(
                        {
                            "name": tool_name,
                            "args": arguments,
                            "result": result,
                            "duration_ms": 0,
                            "denied": True,
                        }
                    )
                    history.append({"role": "tool", "tool_call_id": call_id, "content": result})
                    continue

                # Execute the tool
                tool_start = time.time()
                result = tools.execute_tool(tool_name, arguments)
                tool_duration_ms = (time.time() - tool_start) * 1000

                tool_calls_with_results.append(
                    {
                        "name": tool_name,
                        "args": arguments,
                        "result": result,
                        "duration_ms": tool_duration_ms,
                        "denied": False,
                    }
                )
                history.append({"role": "tool", "tool_call_id": call_id, "content": result})

            iteration += 1
            visualizer.render_tool_call_step(
                iteration,
                tool_calls_with_results,
                api_duration_ms,
                metrics,
            )
            continue

        # Case 2: model produced a final text response (no tool_calls)
        content = message.get("content", "")
        history.append({"role": "assistant", "content": content})

        visualizer.render_response(content, api_duration_ms, metrics)
        total_ms = (time.time() - turn_start) * 1000
        visualizer.render_trajectory_summary(iteration + 1, cumulative_tokens, total_ms)

        return content

    # Hit the iteration limit
    limit_msg = (
        f"Reached maximum iteration limit ({config.MAX_ITERATIONS}). "
        f"The agent made {config.MAX_ITERATIONS} rounds of tool calls without "
        f"producing a final answer. Use 'clear' to reset the conversation."
    )
    visualizer.render_error(limit_msg)
    return limit_msg
