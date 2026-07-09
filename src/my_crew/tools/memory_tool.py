import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from crewai.tools import tool


def _db_path() -> Path:
    return Path(os.getenv("MY_CREW_MEMORY_DB", "my_crew_memory.db"))


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path())
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS memory (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    return connection


@tool("Memory Tool")
def memory_tool(action: str, key: str, value: str = "") -> str:
    """
    Store and retrieve persistent workflow memory/context (SQLite-backed,
    survives across runs).

    Actions:
    - save
    - get
    - delete
    """

    try:
        with _connect() as connection:
            if action == "save":
                connection.execute(
                    "INSERT INTO memory (key, value, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                    "updated_at = excluded.updated_at",
                    (key, value, datetime.now(UTC).isoformat()),
                )
                return f"Memory saved for key: {key}"

            if action == "get":
                row = connection.execute(
                    "SELECT value FROM memory WHERE key = ?", (key,)
                ).fetchone()
                return row[0] if row else "No memory found."

            if action == "delete":
                cursor = connection.execute(
                    "DELETE FROM memory WHERE key = ?", (key,)
                )
                if cursor.rowcount:
                    return f"Memory deleted for key: {key}"
                return "Key not found."

            return "Invalid action."

    except Exception as error:
        return f"Memory Tool Error: {str(error)}"
