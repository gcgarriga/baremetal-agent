# Baremetal Tool-Use Routing Engine

A framework-free tool-use routing engine in Python. Raw LLM API calls + a loop. No LangChain, no abstractions.

## Key Concepts

1. **Tool-use message flow** — `user → assistant tool_calls → tool results → assistant continues`
2. **Tool chaining** — how models sequence multiple tools
3. **Failure modes** — wrong tool picks, hallucinated arguments
4. **Where reasoning lives** — system prompt vs tool descriptions

## Setup

This project requires **Python 3.10+**.

It is recommended to use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development (includes pytest and ruff):

```bash
pip install -e .[dev]
```

Create a `.env` file (or export env vars):

```
GITHUB_TOKEN=your_github_pat_with_models_read_scope
AGENT_MODEL=openai/gpt-4.1
```

Get a token at **GitHub → Settings → Developer settings → Fine-grained tokens** with `Models: Read` permission.

## Run

```bash
baremetal-agent
```

Or:

```bash
python -m baremetal_agent
```

## Example prompts

Try a prompt like:

```text
Help me understand this repo: summarize the architecture, required environment variables, and the current test surface.
```

Or a realistic implementation prompt like:

```text
I need to add a new tool to this agent. Show me where tools are registered, how their schemas are defined, how confirmation is enforced for dangerous tools, and what tests I should update.
```

## Commands

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `tools` | List registered tools |
| `history` | Show conversation history |
| `trajectory [path]` | Export conversation as ATIF-v1.4 JSON |
| `verbose` | Toggle verbose mode (raw API payloads) |
| `model <name>` | Switch model mid-conversation |
| `clear` | Reset conversation |
| `exit` | Quit |

## Tools

| Tool | Confirmation |
|------|:---:|
| `read_file`, `list_directory`, `search_code` | No |
| `git_status`, `git_diff`, `git_log` | No |
| `write_file`, `shell_exec` | ⚠️ Yes |

## Architecture

```
cli.run() → agent.run_agent_turn() → client.chat_completion()
                     ↓
                  tools.execute_tool()
```


## Project Structure

```
baremetal_agent/
├── __init__.py     — Package version
├── __main__.py     — python -m entry point
├── agent.py        — The agentic loop (read this first)
├── cli.py          — REPL with commands and confirmation prompts
├── client.py       — Raw HTTP to GitHub Models API, payload logging with secret redaction
├── config.py       — Env vars + .env file loading
├── tools.py        — Tool registry + 8 implementations with path traversal protection
├── trajectory.py   — ATIF-v1.4 trajectory export
└── visualizer.py   — Live rich terminal visualization of agent steps
tests/
├── conftest.py     — Pytest setup (env vars for testing)
├── test_tools.py   — Tool validation, path safety, execution
└── test_visualizer.py — Formatting helpers and markup safety
pyproject.toml      — Project metadata, dependencies, tool config
```

Every API request and response is printed in full — that's the point.
