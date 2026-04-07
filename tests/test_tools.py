"""Tests for tools.py — validation, path safety, and tool execution."""

from pathlib import Path

import pytest

import config
import tools


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _working_dir(tmp_path, monkeypatch):
    """Point config.WORKING_DIR at a temp directory for every test."""
    monkeypatch.setattr(config, "WORKING_DIR", tmp_path)


# ---------------------------------------------------------------------------
# _validate_args
# ---------------------------------------------------------------------------

class TestValidateArgs:
    SCHEMA = {
        "properties": {
            "path": {"type": "string"},
            "count": {"type": "integer"},
            "verbose": {"type": "boolean"},
        },
        "required": ["path"],
    }

    def test_valid_args(self):
        assert tools._validate_args("t", {"path": "a.txt"}, self.SCHEMA) is None

    def test_missing_required(self):
        err = tools._validate_args("t", {}, self.SCHEMA)
        assert err is not None and "path" in err

    def test_wrong_type(self):
        err = tools._validate_args("t", {"path": 123}, self.SCHEMA)
        assert err is not None and "string" in err

    def test_bool_not_accepted_as_integer(self):
        err = tools._validate_args("t", {"path": "a", "count": True}, self.SCHEMA)
        assert err is not None

    def test_extra_args_ignored(self):
        assert tools._validate_args("t", {"path": "a", "extra": 1}, self.SCHEMA) is None


# ---------------------------------------------------------------------------
# _resolve_safe
# ---------------------------------------------------------------------------

class TestResolveSafe:
    def test_normal_path(self):
        result = tools._resolve_safe("foo.txt")
        assert isinstance(result, Path)
        assert result.parent == config.WORKING_DIR

    def test_traversal_blocked(self):
        result = tools._resolve_safe("../../etc/passwd")
        assert isinstance(result, str) and "escapes" in result

    def test_absolute_outside_blocked(self):
        result = tools._resolve_safe("/etc/passwd")
        assert isinstance(result, str) and "escapes" in result


# ---------------------------------------------------------------------------
# read_file / write_file / list_directory
# ---------------------------------------------------------------------------

class TestFileTools:
    def test_read_existing_file(self):
        (config.WORKING_DIR / "hello.txt").write_text("hello world")
        result = tools.read_file(path="hello.txt")
        assert result == "hello world"

    def test_read_missing_file(self):
        result = tools.read_file(path="nope.txt")
        assert "not found" in result.lower()

    def test_write_and_read(self):
        tools.write_file(path="out.txt", content="data")
        assert (config.WORKING_DIR / "out.txt").read_text() == "data"

    def test_write_creates_parents(self):
        tools.write_file(path="sub/dir/f.txt", content="nested")
        assert (config.WORKING_DIR / "sub/dir/f.txt").read_text() == "nested"

    def test_list_directory(self):
        (config.WORKING_DIR / "a.py").touch()
        (config.WORKING_DIR / "b.py").touch()
        result = tools.list_directory(path=".")
        assert "a.py" in result and "b.py" in result

    def test_list_empty_directory(self):
        d = config.WORKING_DIR / "empty"
        d.mkdir()
        result = tools.list_directory(path="empty")
        assert "empty" in result.lower()

    def test_list_not_a_directory(self):
        (config.WORKING_DIR / "file.txt").touch()
        result = tools.list_directory(path="file.txt")
        assert "not a directory" in result.lower()


# ---------------------------------------------------------------------------
# execute_tool
# ---------------------------------------------------------------------------

class TestExecuteTool:
    def test_unknown_tool(self):
        result = tools.execute_tool("nonexistent", {})
        assert "unknown tool" in result.lower()

    def test_valid_tool_call(self):
        (config.WORKING_DIR / "test.txt").write_text("content")
        result = tools.execute_tool("read_file", {"path": "test.txt"})
        assert result == "content"

    def test_missing_required_arg(self):
        result = tools.execute_tool("read_file", {})
        assert "invalid arguments" in result.lower()


# ---------------------------------------------------------------------------
# search_code
# ---------------------------------------------------------------------------

class TestSearchCode:
    def test_finds_pattern(self):
        (config.WORKING_DIR / "code.py").write_text("def hello():\n    pass\n")
        result = tools.search_code(pattern="def hello")
        assert "code.py" in result

    def test_no_matches(self):
        (config.WORKING_DIR / "code.py").write_text("nothing here\n")
        result = tools.search_code(pattern="zzzzz")
        assert "no matches" in result.lower()

    def test_invalid_regex(self):
        result = tools.search_code(pattern="[invalid")
        assert "invalid regex" in result.lower()
