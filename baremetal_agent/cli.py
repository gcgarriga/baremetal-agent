"""Interactive CLI REPL for the baremetal agent."""

from baremetal_agent import agent, config, tools, trajectory


def _print_banner() -> None:
    """Print the startup banner with configuration and system prompt."""
    tool_names = ", ".join(tools.get_tool_names())
    print()
    print("═" * 62)
    print("  🔧  Baremetal Tool-Use Agent")
    print("═" * 62)
    print(f"  Model:    {config.MODEL}")
    print(f"  API:      {config.API_URL}")
    print(f"  Tools:    {len(tools.TOOLS)} registered ({tool_names})")
    print(f"  Max iter: {config.MAX_ITERATIONS}")
    print(f"  Work dir: {config.WORKING_DIR}")
    print(f"  Verbose: {'on (raw API payloads)' if config.VERBOSE else 'off (rich visualization)'}")
    print("─" * 62)
    print("  System Prompt:")
    for line in config.SYSTEM_PROMPT.splitlines():
        print(f"    {line}")
    print("─" * 62)
    print("  Type 'help' for commands, or just ask a question.")
    print("═" * 62)
    print()


def _cmd_help() -> None:
    """Print available commands."""
    print()
    print("Commands:")
    print("  help           Show this help message")
    print("  tools          List registered tools with descriptions")
    print("  history        Show conversation history")
    print("  trajectory     Export conversation as ATIF trajectory JSON")
    print("  clear          Reset conversation history")
    print("  model <name>   Switch to a different model")
    print("  verbose        Toggle verbose mode (raw API payloads)")
    print("  exit / quit    Exit the agent")
    print()


def _cmd_tools() -> None:
    """List all registered tools with descriptions."""
    print()
    for name, tool in tools.TOOLS.items():
        desc = tool["definition"]["function"]["description"]
        confirm = " ⚠️  (requires confirmation)" if tool["requires_confirmation"] else ""
        print(f"  {name}{confirm}")
        print(f"    {desc}")
        params = tool["definition"]["function"]["parameters"]["properties"]
        if params:
            for pname, pdef in params.items():
                req = pname in tool["definition"]["function"]["parameters"].get("required", [])
                req_tag = " (required)" if req else ""
                print(f"      - {pname}: {pdef.get('type', '?')}{req_tag} — {pdef.get('description', '')}")
        print()


def _cmd_history(history: list[dict]) -> None:
    """Show conversation history with role and content summaries."""
    print()
    if len(history) <= 1:  # only system prompt
        print("  (no conversation history)")
        print()
        return

    for i, msg in enumerate(history):
        role = msg["role"]
        if role == "system":
            continue

        if role == "tool":
            content = msg.get("content", "")
            preview = content[:100].replace("\n", "\\n")
            call_id = msg.get("tool_call_id", "?")
            print(f"  [{i}] tool (id={call_id}): {preview}...")
        elif role == "assistant" and msg.get("tool_calls"):
            calls = msg["tool_calls"]
            names = [c["function"]["name"] for c in calls]
            print(f"  [{i}] assistant → tool_calls: {', '.join(names)}")
        else:
            content = msg.get("content", "")
            preview = content[:100].replace("\n", "\\n") if content else "(empty)"
            print(f"  [{i}] {role}: {preview}")

    print()


def _cmd_model(new_model: str) -> None:
    """Switch to a different model."""
    old = config.MODEL
    config.MODEL = new_model
    print(f"\n  Model changed: {old} → {new_model}\n")


def run() -> None:
    """Run the interactive REPL."""
    _print_banner()

    # Initialize conversation history and response log — owned here, passed down
    history: list[dict] = [{"role": "system", "content": config.SYSTEM_PROMPT}]
    api_responses: list[dict] = []

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # Handle special commands
        cmd = user_input.lower()

        if cmd in ("exit", "quit"):
            print("Goodbye!")
            break

        if cmd == "help":
            _cmd_help()
            continue

        if cmd == "tools":
            _cmd_tools()
            continue

        if cmd == "history":
            _cmd_history(history)
            continue

        if cmd == "clear":
            history.clear()
            history.append({"role": "system", "content": config.SYSTEM_PROMPT})
            api_responses.clear()
            print("\n  Conversation history cleared.\n")
            continue

        if cmd == "trajectory" or cmd.startswith("trajectory "):
            parts = user_input.split(maxsplit=1)
            path = parts[1] if len(parts) > 1 else "trajectory.json"
            atif = trajectory.history_to_atif(
                history,
                api_responses,
                config.MODEL,
            )
            try:
                trajectory.save_trajectory(atif, path)
            except OSError as exc:
                print(f"\n  ❌ Failed to write trajectory: {exc}\n")
                continue
            n_steps = atif["final_metrics"]["total_steps"]
            tokens = atif["final_metrics"]["total_prompt_tokens"] + atif["final_metrics"]["total_completion_tokens"]
            print(f"\n  ✅ Trajectory exported: {path}")
            print(f"     {n_steps} steps, {tokens} total tokens")
            print("     Format: ATIF-v1.4\n")
            continue

        if cmd.startswith("model"):
            new_model = user_input[5:].strip()
            if new_model:
                _cmd_model(new_model)
            else:
                print(f"\n  Current model: {config.MODEL}\n")
            continue

        if cmd == "verbose":
            config.VERBOSE = not config.VERBOSE
            state = "on (raw API payloads)" if config.VERBOSE else "off (rich visualization)"
            print(f"\n  Verbose: {state}\n")
            continue

        # Send to the agent
        print()
        response = agent.run_agent_turn(user_input, history, api_responses)
        if config.VERBOSE:
            print("─" * 62)
            print(response)
            print("─" * 62)
        print()
