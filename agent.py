"""The agentic tool-use loop — the core of the project.

Takes a user message, sends it to the LLM with tool definitions, parses the
response, executes any tool calls, feeds results back, and loops until the model
produces a final text response or the iteration limit is reached.
"""

import json

import client
import config
import tools

_BOX_TOP = "╭─ {} ─{}"
_BOX_BOT = "╰" + "─" * 60 + "╯"


def _log_tool_call(name: str, args: dict, result: str) -> None:
    """Log a tool call with its arguments and result."""
    pad = "─" * max(0, 58 - len("Tool Call"))
    print(_BOX_TOP.format("Tool Call", pad + "╮"))
    args_str = ", ".join(f'{k}={json.dumps(v)}' for k, v in args.items())
    print(f"│ {name}({args_str})")
    print(f"│")
    for line in result.splitlines()[:30]:
        print(f"│ {line}")
    if len(result.splitlines()) > 30:
        print(f"│ ... ({len(result.splitlines()) - 30} more lines)")
    print(_BOX_BOT)
    print()


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
    return answer in ("y", "yes")


def run_agent_turn(user_message: str, history: list[dict]) -> str:
    """Run a single user turn through the agentic loop.

    Appends to `history` in place. Returns the final assistant text response.
    """
    history.append({"role": "user", "content": user_message})

    tool_definitions = tools.get_tool_definitions()
    iteration = 0

    while iteration < config.MAX_ITERATIONS:
        # Call the LLM
        try:
            response = client.chat_completion(history, tool_definitions)
        except RuntimeError as exc:
            error_msg = f"API error: {exc}"
            print(f"\n❌ {error_msg}\n")
            return error_msg

        # Parse the response
        choice = response["choices"][0]
        message = choice["message"]
        finish_reason = choice.get("finish_reason", "")

        # Case 1: model produced a final text response
        if finish_reason == "stop" or not message.get("tool_calls"):
            content = message.get("content", "")
            history.append({"role": "assistant", "content": content})
            return content

        # Case 2: model wants to call tools
        # Append the assistant message with tool_calls to history
        assistant_msg = {"role": "assistant", "content": message.get("content")}
        if message.get("tool_calls"):
            assistant_msg["tool_calls"] = message["tool_calls"]
        history.append(assistant_msg)

        # Execute each tool call
        for tool_call in message["tool_calls"]:
            call_id = tool_call["id"]
            func = tool_call["function"]
            tool_name = func["name"]

            # Parse arguments
            try:
                arguments = json.loads(func["arguments"]) if func["arguments"] else {}
            except json.JSONDecodeError as exc:
                result = f"Error: Could not parse arguments as JSON: {exc}\nRaw: {func['arguments']}"
                _log_tool_call(tool_name, {}, result)
                history.append({"role": "tool", "tool_call_id": call_id, "content": result})
                continue

            # Check confirmation requirement
            if tool_name in tools.TOOLS and tools.TOOLS[tool_name]["requires_confirmation"]:
                if not _confirm_tool(tool_name, arguments):
                    result = "Tool execution denied by user."
                    _log_tool_call(tool_name, arguments, result)
                    history.append({"role": "tool", "tool_call_id": call_id, "content": result})
                    continue

            # Execute the tool
            result = tools.execute_tool(tool_name, arguments)
            _log_tool_call(tool_name, arguments, result)
            history.append({"role": "tool", "tool_call_id": call_id, "content": result})

        iteration += 1

    # Hit the iteration limit
    limit_msg = (
        f"Reached maximum iteration limit ({config.MAX_ITERATIONS}). "
        f"The agent made {config.MAX_ITERATIONS} rounds of tool calls without "
        f"producing a final answer. Use 'clear' to reset the conversation."
    )
    print(f"\n⚠️  {limit_msg}\n")
    return limit_msg
