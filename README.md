# Baremetal Tool-Use Routing Engine

A minimal, framework-free tool-use routing engine built from scratch in Python. Takes a user query via a CLI REPL, decides which developer tools to call (and in what order), executes them, and synthesizes results — all using raw LLM API calls and a hand-built agentic loop.

**No frameworks. No abstractions. Just raw API calls and a loop.**

## What You'll Learn

By reading and running this code you'll understand:

1. **Tool-use message flow** — the full cycle: `user → assistant with tool_calls → tool results → assistant continues`
2. **Tool chaining** — how the model sequences multiple tools to answer complex questions
3. **Failure modes** — what happens when the model picks the wrong tool or hallucinates arguments
4. **Parallel vs sequential** — how models request multiple tools at once and how to handle them
5. **Where reasoning lives** — the interplay between system prompt and tool descriptions

## Setup

### Prerequisites

- Python 3.11+
- A GitHub Personal Access Token with `models:read` scope

### Install

```bash
pip install -r requirements.txt
```

### Configure

```bash
export GITHUB_TOKEN="ghp_your_token_here"

# Optional:
export AGENT_MODEL="anthropic/claude-sonnet-4"  # default
export AGENT_MAX_ITERATIONS="10"                     # default
export AGENT_WORKING_DIR="."                         # default: current directory
```

## Run

```bash
python main.py
```

You'll see a REPL with full visibility into every API call:

```
══════════════════════════════════════════════════════════════
  🔧  Baremetal Tool-Use Agent
══════════════════════════════════════════════════════════════
  Model:    anthropic/claude-sonnet-4
  API:      https://models.github.ai/inference/chat/completions
  Tools:    8 registered (read_file, write_file, ...)
  ...
> What files are in this project?
```

## Commands

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `tools` | List registered tools with descriptions |
| `history` | Show conversation history |
| `clear` | Reset conversation history |
| `model <name>` | Switch to a different model |
| `exit` / `quit` | Exit the agent |

## Tools

| Tool | Description | Confirmation |
|------|-------------|:---:|
| `read_file` | Read file contents | No |
| `write_file` | Write content to a file | ⚠️ Yes |
| `list_directory` | List files and directories | No |
| `search_code` | Regex search across files | No |
| `shell_exec` | Execute a shell command | ⚠️ Yes |
| `git_status` | Show git status | No |
| `git_diff` | Show git diff | No |
| `git_log` | Show commit history | No |

## Architecture

```
main.py → cli.py → agent.py → client.py
                       ↓
                    tools.py
```

- **`config.py`** — Env vars → module constants
- **`client.py`** — Raw HTTP to GitHub Models API, full payload logging
- **`tools.py`** — Tool registry (dict) + 8 tool implementations
- **`agent.py`** — THE agentic loop: parse response → execute tools → loop
- **`cli.py`** — REPL with commands and confirmation prompts
- **`main.py`** — Entry point (5 lines)

Every API request and response is printed in full — that's the point.

## Project Philosophy

This project deliberately avoids frameworks (LangChain, LlamaIndex, etc.) to expose the raw mechanics. The entire tool-use system is ~800 lines of Python with one dependency (`httpx`). Read `agent.py` first — that's where the magic happens.
