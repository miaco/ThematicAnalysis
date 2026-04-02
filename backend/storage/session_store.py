import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.schemas import Session


DB_PATH = Path(__file__).parent.parent / "thematic_analysis.db"

_connection: Optional[sqlite3.Connection] = None


def _get_db() -> sqlite3.Connection:
    """Return a module-level SQLite connection, creating the table if needed."""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _connection.commit()
    return _connection


def save_session(session: Session):
    session.updated_at = datetime.utcnow()
    data = json.dumps(session.model_dump(mode="json"), default=str)
    db = _get_db()
    db.execute(
        "INSERT INTO sessions (id, data, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
        (session.id, data, session.updated_at.isoformat()),
    )
    db.commit()


def load_session(session_id: str) -> Optional[Session]:
    db = _get_db()
    row = db.execute("SELECT data FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        return None
    return Session(**json.loads(row[0]))


def list_sessions() -> list[Session]:
    db = _get_db()
    rows = db.execute("SELECT data FROM sessions ORDER BY updated_at DESC").fetchall()
    sessions = []
    for (raw,) in rows:
        try:
            sessions.append(Session(**json.loads(raw)))
        except Exception:
            pass
    return sessions


def delete_session(session_id: str):
    db = _get_db()
    db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    db.commit()
