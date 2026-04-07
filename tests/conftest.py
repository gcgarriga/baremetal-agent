"""Pytest configuration — runs before any test imports."""

import os
import sys
from pathlib import Path

# Set required env vars before config.py is imported
os.environ.setdefault("GITHUB_TOKEN", "test-token-for-testing")
os.environ.setdefault("AGENT_WORKING_DIR", "/tmp/baremetal-test")

# Add project root to sys.path so tests can import project modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
