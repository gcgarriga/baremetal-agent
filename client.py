"""Raw HTTP client for the GitHub Models API (OpenAI-compatible chat completions)."""

import json
import re
import time

import httpx

import config

_client = httpx.Client(timeout=120.0)

_BOX_TOP = "╭─ {} ─{}"
_BOX_BOT = "╰" + "─" * 60 + "╯"

# Patterns that look like secrets — redact all but the first 6 chars
_SECRET_RE = re.compile(
    r"(ghp_|gho_|ghu_|github_pat_|sk-|key-|token[=: ]+|password[=: ]+)"
    r"[A-Za-z0-9_\-]{6}([A-Za-z0-9_\-]+)",
    re.IGNORECASE,
)


def _redact(text: str) -> str:
    """Replace secrets in text with a redacted version, keeping a short prefix."""
    def _mask(m: re.Match) -> str:
        prefix = m.group(1)
        visible = m.group(0)[len(prefix):len(prefix) + 6]
        hidden_len = len(m.group(2))
        return f"{prefix}{visible}{'*' * hidden_len}"
    return _SECRET_RE.sub(_mask, text)


def _log_box(title: str, body: str) -> None:
    """Print a payload inside a box-drawing frame."""
    pad = "─" * max(0, 58 - len(title))
    print(_BOX_TOP.format(title, pad + "╮"))
    for line in body.splitlines():
        print(f"│ {line}")
    print(_BOX_BOT)
    print()


def chat_completion(messages: list[dict], tools: list[dict]) -> dict:
    """Send a chat completion request and return the parsed response JSON.

    Logs the full request and response payloads to stdout.
    Retries on 429 (rate limit) and 5xx (server error) up to 3 times.
    """
    body = {
        "model": config.MODEL,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }

    headers = {
        "Authorization": f"Bearer {config.TOKEN}",
        "Content-Type": "application/json",
    }

    _log_box("API Request", _redact(f"POST {config.API_URL}\n{json.dumps(body, indent=2)}"))

    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            resp = _client.post(config.API_URL, headers=headers, json=body)
        except httpx.RequestError as exc:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"│ Connection error: {exc}. Retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Connection failed after {max_retries} retries: {exc}") from exc

        if resp.status_code == 200:
            data = resp.json()
            _log_box("API Response", _redact(f"{resp.status_code} OK\n{json.dumps(data, indent=2)}"))
            return data

        if resp.status_code == 401:
            raise RuntimeError(
                "Authentication failed (401). Check your GITHUB_TOKEN.\n"
                f"Response: {resp.text}"
            )

        if resp.status_code == 429:
            try:
                retry_after = int(resp.headers.get("Retry-After", "5"))
            except (ValueError, TypeError):
                retry_after = 5
            if attempt < max_retries:
                print(f"│ Rate limited (429). Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            raise RuntimeError(f"Rate limited after {max_retries} retries. Response: {resp.text}")

        if resp.status_code >= 500:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"│ Server error ({resp.status_code}). Retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise RuntimeError(
                f"Server error after {max_retries} retries.\n"
                f"Status: {resp.status_code}\nResponse: {resp.text}"
            )

        # Other client errors — don't retry
        raise RuntimeError(
            f"API error {resp.status_code}.\nResponse: {resp.text}"
        )

    # Should not reach here, but just in case
    raise RuntimeError("Exhausted retries without a response.")
