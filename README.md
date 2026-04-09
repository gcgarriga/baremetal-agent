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
pip install -r requirements.txt
```

Create a `.env` file (or export env vars):

```
GITHUB_TOKEN=your_github_pat_with_models_read_scope
AGENT_MODEL=openai/gpt-4.1
```

Get a token at **GitHub → Settings → Developer settings → Fine-grained tokens** with `Models: Read` permission.

## Run

```bash
python main.py
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
main.py → cli.py → agent.py → client.py
                       ↓
                    tools.py
```

- **`agent.py`** — The agentic loop. Read this first.
- **`tools.py`** — Tool registry + 8 implementations with path traversal protection
- **`client.py`** — Raw HTTP to GitHub Models API, full payload logging with secret redaction
- **`visualizer.py`** — Live rich terminal visualization of agent steps
- **`trajectory.py`** — ATIF-v1.4 trajectory export
- **`config.py`** — Env vars + `.env` file loading
- **`cli.py`** — REPL with commands and confirmation prompts
- **`main.py`** — Entry point (6 lines)

Every API request and response is printed in full — that's the point.
