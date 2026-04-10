"""Tests for config.py — .env loading and configuration."""

import os
from pathlib import Path

from baremetal_agent import config


class TestLoadDotenv:
    def test_loads_from_cwd(self, tmp_path, monkeypatch):
        """config._load_dotenv() should read .env from CWD."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_DOTENV_VAR=hello_from_cwd\n")
        monkeypatch.chdir(tmp_path)
        # Remove if already set, so setdefault in _load_dotenv takes effect
        monkeypatch.delenv("TEST_DOTENV_VAR", raising=False)
        monkeypatch.delenv("AGENT_DOTENV", raising=False)
        config._load_dotenv()
        assert os.environ["TEST_DOTENV_VAR"] == "hello_from_cwd"

    def test_agent_dotenv_override(self, tmp_path, monkeypatch):
        """AGENT_DOTENV env var should override the default .env path."""
        custom_env = tmp_path / "custom.env"
        custom_env.write_text("TEST_CUSTOM_VAR=from_override\n")
        monkeypatch.setenv("AGENT_DOTENV", str(custom_env))
        monkeypatch.delenv("TEST_CUSTOM_VAR", raising=False)
        config._load_dotenv()
        assert os.environ["TEST_CUSTOM_VAR"] == "from_override"

    def test_missing_env_file_no_error(self, tmp_path, monkeypatch):
        """No .env file at all should not raise."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AGENT_DOTENV", raising=False)
        # Should not raise
        config._load_dotenv()

    def test_quoted_values_stripped(self, tmp_path, monkeypatch):
        """Quotes around values in .env should be stripped."""
        env_file = tmp_path / ".env"
        env_file.write_text('TEST_QUOTED_VAR="quoted_value"\n')
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TEST_QUOTED_VAR", raising=False)
        monkeypatch.delenv("AGENT_DOTENV", raising=False)
        config._load_dotenv()
        assert os.environ["TEST_QUOTED_VAR"] == "quoted_value"

    def test_comments_and_blank_lines_ignored(self, tmp_path, monkeypatch):
        """Comments and blank lines in .env should be skipped."""
        env_file = tmp_path / ".env"
        env_file.write_text("# this is a comment\n\nTEST_COMMENT_VAR=works\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TEST_COMMENT_VAR", raising=False)
        monkeypatch.delenv("AGENT_DOTENV", raising=False)
        config._load_dotenv()
        assert os.environ["TEST_COMMENT_VAR"] == "works"

    def test_existing_env_not_overwritten(self, tmp_path, monkeypatch):
        """setdefault should not overwrite already-set env vars."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_EXISTING_VAR=from_file\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TEST_EXISTING_VAR", "already_set")
        monkeypatch.delenv("AGENT_DOTENV", raising=False)
        config._load_dotenv()
        assert os.environ["TEST_EXISTING_VAR"] == "already_set"


class TestWorkingDir:
    def test_working_dir_is_path(self):
        assert isinstance(config.WORKING_DIR, Path)

    def test_working_dir_is_resolved(self):
        assert config.WORKING_DIR.is_absolute()
