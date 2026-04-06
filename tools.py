"""Tool registry and implementations.

Each tool is a plain function that accepts keyword arguments and returns a string.
The TOOLS dict maps tool names to their handler, confirmation flag, and OpenAI-format
schema definition.
"""

import fnmatch
import os
import re
import subprocess
from pathlib import Path

import config

# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

_TYPE_MAP = {"string": str, "integer": int, "boolean": bool, "number": (int, float)}


def _validate_args(name: str, args: dict, schema: dict) -> str | None:
    """Validate arguments against a tool's JSON Schema parameters.

    Returns None if valid, or an error description string if invalid.
    """
    props = schema.get("properties", {})
    required = schema.get("required", [])

    for req in required:
        if req not in args:
            return f"Missing required argument '{req}'"

    for key, value in args.items():
        if key not in props:
            continue  # extra args are ignored, not an error
        expected_type = props[key].get("type")
        if expected_type and expected_type in _TYPE_MAP:
            if expected_type in {"integer", "number"} and isinstance(value, bool):
                return f"Argument '{key}' must be {expected_type}, got {type(value).__name__}"
            if not isinstance(value, _TYPE_MAP[expected_type]):
                return f"Argument '{key}' must be {expected_type}, got {type(value).__name__}"

    return None


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _resolve_safe(path: str) -> Path | str:
    """Resolve a path and verify it stays within WORKING_DIR.

    Returns the resolved Path, or an error string if it escapes.
    """
    target = (config.WORKING_DIR / path).resolve()
    if not target.is_relative_to(config.WORKING_DIR):
        return f"Error: Path escapes working directory: {path}"
    return target


def read_file(*, path: str) -> str:
    """Read the contents of a file."""
    try:
        target = _resolve_safe(path)
        if isinstance(target, str):
            return target
        return target.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as exc:
        return f"Error reading file: {exc}"


def write_file(*, path: str, content: str) -> str:
    """Write content to a file, creating parent directories if needed."""
    try:
        target = _resolve_safe(path)
        if isinstance(target, str):
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content.encode('utf-8'))} bytes to {path}"
    except Exception as exc:
        return f"Error writing file: {exc}"


def list_directory(*, path: str = ".") -> str:
    """List files and directories at the given path."""
    try:
        target = _resolve_safe(path)
        if isinstance(target, str):
            return target
        if not target.is_dir():
            return f"Error: Not a directory: {path}"
        entries = sorted(target.iterdir())
        lines = []
        for entry in entries:
            indicator = "/" if entry.is_dir() else ""
            lines.append(f"{entry.name}{indicator}")
        return "\n".join(lines) if lines else "(empty directory)"
    except Exception as exc:
        return f"Error listing directory: {exc}"


def search_code(*, pattern: str, path: str = ".", file_glob: str = "*") -> str:
    """Search for a regex pattern in files. Returns matching lines with paths and line numbers."""
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        return f"Error: Invalid regex pattern: {exc}"

    target = _resolve_safe(path)
    if isinstance(target, str):
        return target
    if not target.exists():
        return f"Error: Path not found: {path}"

    matches = []
    max_matches = 50
    files_to_search = []

    if target.is_file():
        files_to_search = [target]
    else:
        for root, _dirs, filenames in os.walk(target):
            for filename in filenames:
                if fnmatch.fnmatch(filename, file_glob):
                    files_to_search.append(Path(root) / filename)

    for filepath in files_to_search:
        if len(matches) >= max_matches:
            break
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
            for line_num, line in enumerate(text.splitlines(), 1):
                if compiled.search(line):
                    rel_path = filepath.relative_to(config.WORKING_DIR)
                    matches.append(f"{rel_path}:{line_num}: {line.rstrip()}")
                    if len(matches) >= max_matches:
                        break
        except (PermissionError, OSError):
            continue

    if not matches:
        return f"No matches found for pattern '{pattern}'"

    result = "\n".join(matches)
    if len(matches) >= max_matches:
        result += f"\n\n(truncated at {max_matches} matches)"
    return result


def shell_exec(*, command: str, timeout: int = 30) -> str:
    """Execute a shell command and return stdout + stderr."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=config.WORKING_DIR,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n"
            output += f"[stderr]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"

        max_len = 10_000
        if len(output) > max_len:
            output = output[:max_len] + f"\n\n(output truncated at {max_len} characters)"

        return output if output else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as exc:
        return f"Error executing command: {exc}"


def git_status() -> str:
    """Show the current git status."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            cwd=config.WORKING_DIR,
        )
        if result.returncode != 0 and result.stderr.strip():
            return f"git status error: {result.stderr.strip()}"
        output = result.stdout.strip()
        return output if output else "(working tree clean)"
    except Exception as exc:
        return f"Error running git status: {exc}"


def git_diff(*, file: str | None = None) -> str:
    """Show git diff, optionally for a specific file."""
    try:
        cmd = ["git", "diff", "--"]
        if file:
            target = _resolve_safe(file)
            if isinstance(target, str):
                return target
            cmd.append(str(target.relative_to(config.WORKING_DIR)))
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=config.WORKING_DIR
        )
        if result.returncode != 0 and result.stderr.strip():
            return f"git diff error: {result.stderr.strip()}"
        output = result.stdout.strip()
        if not output:
            return "(no changes)" if not file else f"(no changes for {file})"

        max_len = 10_000
        if len(output) > max_len:
            output = output[:max_len] + f"\n\n(diff truncated at {max_len} characters)"
        return output
    except Exception as exc:
        return f"Error running git diff: {exc}"


def git_log(*, count: int = 10) -> str:
    """Show recent commit history."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{count}"],
            capture_output=True,
            text=True,
            cwd=config.WORKING_DIR,
        )
        if result.returncode != 0 and result.stderr.strip():
            return f"git log error: {result.stderr.strip()}"
        output = result.stdout.strip()
        return output if output else "(no commits)"
    except Exception as exc:
        return f"Error running git log: {exc}"


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS: dict[str, dict] = {
    "read_file": {
        "handler": read_file,
        "requires_confirmation": False,
        "definition": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file at the given path (relative to working directory)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to working directory",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
    },
    "write_file": {
        "handler": write_file,
        "requires_confirmation": True,
        "definition": {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file, creating parent directories if needed",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to working directory",
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        },
    },
    "list_directory": {
        "handler": list_directory,
        "requires_confirmation": False,
        "definition": {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "List files and directories at the given path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path (default: current directory)",
                        }
                    },
                    "required": [],
                },
            },
        },
    },
    "search_code": {
        "handler": search_code,
        "requires_confirmation": False,
        "definition": {
            "type": "function",
            "function": {
                "name": "search_code",
                "description": "Search for a regex pattern in files. Returns matching lines with file paths and line numbers. Caps at 50 matches.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to search for",
                        },
                        "path": {
                            "type": "string",
                            "description": "Directory or file to search in (default: current directory)",
                        },
                        "file_glob": {
                            "type": "string",
                            "description": "Glob pattern to filter files, e.g. '*.py' (default: all files)",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        },
    },
    "shell_exec": {
        "handler": shell_exec,
        "requires_confirmation": True,
        "definition": {
            "type": "function",
            "function": {
                "name": "shell_exec",
                "description": "Execute a shell command and return stdout + stderr. Requires user confirmation. Output capped at 10,000 characters.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 30)",
                        },
                    },
                    "required": ["command"],
                },
            },
        },
    },
    "git_status": {
        "handler": git_status,
        "requires_confirmation": False,
        "definition": {
            "type": "function",
            "function": {
                "name": "git_status",
                "description": "Show the current git status (short format)",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
    },
    "git_diff": {
        "handler": git_diff,
        "requires_confirmation": False,
        "definition": {
            "type": "function",
            "function": {
                "name": "git_diff",
                "description": "Show git diff output, optionally for a specific file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file": {
                            "type": "string",
                            "description": "Specific file to diff (optional — omit for full diff)",
                        }
                    },
                    "required": [],
                },
            },
        },
    },
    "git_log": {
        "handler": git_log,
        "requires_confirmation": False,
        "definition": {
            "type": "function",
            "function": {
                "name": "git_log",
                "description": "Show recent git commit history (oneline format)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of commits to show (default: 10)",
                        }
                    },
                    "required": [],
                },
            },
        },
    },
}


def get_tool_definitions() -> list[dict]:
    """Return the OpenAI-format tools array for the API request."""
    return [tool["definition"] for tool in TOOLS.values()]


def get_tool_names() -> list[str]:
    """Return a list of all registered tool names."""
    return list(TOOLS.keys())


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool by name with the given arguments.

    Returns the tool result string. Handles unknown tools, validation errors,
    and execution exceptions — never raises.
    """
    if name not in TOOLS:
        available = ", ".join(get_tool_names())
        return f"Error: Unknown tool '{name}'. Available tools: {available}"

    tool = TOOLS[name]
    schema = tool["definition"]["function"]["parameters"]

    validation_error = _validate_args(name, arguments, schema)
    if validation_error:
        return f"Error: Invalid arguments for '{name}': {validation_error}"

    try:
        return tool["handler"](**arguments)
    except TypeError as exc:
        return f"Error: Bad arguments for '{name}': {exc}"
    except Exception as exc:
        return f"Error executing '{name}': {exc}"
