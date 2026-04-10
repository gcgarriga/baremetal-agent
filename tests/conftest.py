"""Pytest configuration — runs before any test imports."""

import os

# Set required env vars before config.py is imported
os.environ.setdefault("GITHUB_TOKEN", "test-token-for-testing")
os.environ.setdefault("AGENT_WORKING_DIR", "/tmp/baremetal-test")
