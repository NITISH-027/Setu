"""Test-session setup: point the app at an isolated temporary SQLite DB.

The engine binds DATABASE_URL at import time. Setting it here (pytest imports
conftest before any test module) means the suite never touches a local or
deployed setu.db - a stale DB file can no longer break the tests.
"""
import os
import tempfile

_fd, _TEST_DB_PATH = tempfile.mkstemp(prefix="setu_test_", suffix=".db")
os.close(_fd)
os.remove(_TEST_DB_PATH)  # let SQLite create it fresh on first connect

os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB_PATH
