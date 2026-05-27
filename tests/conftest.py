import pytest
import sys
import os
import sqlite3
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ["DB_PATH"] = ":memory:"

import app as app_module
from app import app


class NoCloseConnection:
    """Wrapper that ignores close() so our shared in-memory DB stays alive."""
    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass  # intentionally a no-op

    def commit(self):
        return self._conn.commit()

    def execute(self, *args, **kwargs):
        return self._conn.execute(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.fixture
def client():
    real_conn = sqlite3.connect(":memory:")
    real_conn.row_factory = sqlite3.Row
    real_conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    real_conn.commit()

    wrapped = NoCloseConnection(real_conn)

    original_get_db = app_module.get_db
    app_module.get_db = lambda: wrapped

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

    app_module.get_db = original_get_db
    real_conn.close()
