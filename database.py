"""
database.py — SQLite schema initialisation and CRUD helpers.
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "calls.db")


def get_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the calls table if it does not already exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calls (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                caller_name      TEXT,
                intent           TEXT,
                callback_number  TEXT,
                transcript       TEXT,
                audio_filename   TEXT,
                created_at       TEXT NOT NULL
            )
            """
        )
        conn.commit()


def insert_call(
    caller_name: Optional[str],
    intent: Optional[str],
    callback_number: Optional[str],
    transcript: str,
    audio_filename: str,
) -> int:
    """Insert a call record and return the new row id."""
    created_at = datetime.utcnow().isoformat(sep=" ", timespec="seconds") + " UTC"
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO calls
                (caller_name, intent, callback_number, transcript, audio_filename, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (caller_name, intent, callback_number, transcript, audio_filename, created_at),
        )
        conn.commit()
        return cursor.lastrowid


def fetch_all_calls() -> List[sqlite3.Row]:
    """Return all call records ordered by most recent first."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM calls ORDER BY id DESC"
        ).fetchall()


if __name__ == "__main__":
    init_db()
    print(f"[OK] Database initialised at: {DB_PATH}")
    # Quick smoke-test insert
    row_id = insert_call(
        caller_name="Test Caller",
        intent="smoke test",
        callback_number=None,
        transcript="This is a smoke-test transcript.",
        audio_filename="test.wav",
    )
    print(f"[OK] Inserted test row with id={row_id}")
    rows = fetch_all_calls()
    for r in rows:
        print(dict(r))
