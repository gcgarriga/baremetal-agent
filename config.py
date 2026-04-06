"""Configuration loaded from environment variables (with .env fallback)."""

import os
import sys
from pathlib import Path


def _load_dotenv() -> None:
    """Load key=value pairs from .env file into os.environ."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            os.environ.setdefault(key.strip(), value)


_load_dotenv()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} environment variable is required but not set.", file=sys.stderr)
        sys.exit(1)
    return value


TOKEN: str = _require_env("GITHUB_TOKEN")
API_URL: str = "https://models.github.ai/inference/chat/completions"
MODEL: str = os.environ.get("AGENT_MODEL", "openai/gpt-4.1")
MAX_ITERATIONS: int = int(os.environ.get("AGENT_MAX_ITERATIONS", "10"))
WORKING_DIR: Path = Path(os.environ.get("AGENT_WORKING_DIR", ".")).resolve()

SYSTEM_PROMPT: str = (
    "You are a developer assistant with access to tools for working with the local "
    "filesystem and git repositories. When the user asks about files, code, or git "
    "history, use the available tools to get real information — never guess or "
    "fabricate file contents, git output, or command results.\n\n"
    "You can chain multiple tool calls when needed. For example, to understand a "
    "codebase you might: list_directory → read_file on interesting files → search_code "
    "for specific patterns.\n\n"
    "Always explain what you found after using tools. Be concise and direct."
)
