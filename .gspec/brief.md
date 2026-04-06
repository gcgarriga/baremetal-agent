# Project Brief

**Type:** brownfield
**Date:** 2026-04-06

## What this is

A framework-free tool-use routing engine in Python. It demonstrates how LLM tool calling works at the lowest level: raw HTTP to an OpenAI-compatible API, a loop that processes tool calls, and 8 tool implementations for filesystem and git operations. The project is intentionally minimal — the educational value is in the transparency.

## Stack

| Layer       | Choice                                      |
|-------------|---------------------------------------------|
| Language    | Python 3.10+                                |
| HTTP Client | httpx                                       |
| LLM API     | GitHub Models (OpenAI-compatible completions)|
| Dependencies| httpx only — everything else is stdlib       |

## Architecture

```
main.py → cli.py → agent.py → client.py
                      ↓
                   tools.py
                      ↓
               trajectory.py (export only)
```

All modules live at the root — flat structure, no packages.

**Request flow:**
1. `main.py` calls `cli.run()` → starts the REPL
2. User input is dispatched: REPL commands (`help`, `tools`, `model`, `clear`, `trajectory`, `history`) handled inline in `cli.py`, everything else goes to `agent.run_agent_turn()`
3. `run_agent_turn()` appends the user message to history and enters a loop (max `config.MAX_ITERATIONS`):
   - Sends full history + tool definitions to `client.chat_completion()`
   - If response contains `tool_calls`: executes each via `tools.execute_tool()`, appends results to history, continues loop
   - If response is text (no `tool_calls`): appends to history, returns — loop ends
4. On API errors, the entire turn is rolled back (history entries deleted)
5. Raw API responses are stored in `agent.api_responses` for trajectory export

**Key modules:**
- `agent.py` — The agentic loop. Core of the project.
- `tools.py` — Tool registry (dict mapping name → handler + schema + confirmation flag) and 8 implementations with path traversal protection.
- `client.py` — Raw HTTP to GitHub Models API. Full payload logging with secret redaction. Exponential-backoff retries.
- `trajectory.py` — Converts conversation history + API responses to ATIF-v1.4 JSON.
- `config.py` — Env vars with `.env` fallback. Module-level globals for runtime config.
- `cli.py` — REPL loop with command dispatch and startup banner.

## Data Model

No persistence. All state is in-memory:
- `history: list[dict]` — OpenAI-format message list (system/user/assistant/tool roles)
- `agent.api_responses: list[dict]` — raw API response dicts for trajectory export
- `config.MODEL: str` — mutable, changed by the `model` command at runtime

## Strengths

- **Deliberately minimal.** One dependency, flat structure, no abstractions. The simplicity is the point.
- **Clean separation of concerns.** Each module has exactly one job — no cross-cutting responsibilities.
- **Full transparency.** Every API request and response is printed in full with box-drawing formatting.
- **Defensive tool execution.** Path traversal protection via `_resolve_safe()`, argument validation against JSON Schema, and all errors caught and returned as strings.
- **Robust HTTP client.** Exponential backoff on 429/5xx, secret redaction in logs, atexit cleanup.
- **Turn rollback.** On API failure, `run_agent_turn()` deletes all history entries added during the failed turn.
- **ATIF trajectory export.** Structured format for debugging, replay, and training data.

## Technical Debt and Known Issues

### Bugs and broken behavior

None identified. The codebase is clean and recently written.

### Legacy patterns

None — fresh codebase with consistent patterns throughout.

### Architectural concerns

- 🟢 **Tolerable:** `agent.api_responses` is a module-level global list. Works for single-session use but would need refactoring for concurrent or multi-session usage.
- 🟢 **Tolerable:** `config.MODEL` is mutable module-level state (changed by the `model` command). Same single-session limitation.
- 🟢 **Tolerable:** Error rollback in `run_agent_turn()` deletes from `history_start - 1` which removes the user message too — this is correct for the current "retry from scratch" pattern but could be surprising.

### Missing infrastructure

- **No test suite.** Zero tests. The project has no testing framework, fixtures, or CI.
- **No linter/formatter.** No ruff, flake8, black, or mypy configuration.
- **No structured logging.** All output is `print()` to stdout. Fine for a REPL tool, but limits programmatic use.

## Coding Rules

See `.github/copilot-instructions.md` for coding conventions and boundaries.
