import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.schemas import Session


SESSIONS_DIR = Path(__file__).parent.parent / "sessions"


def _ensure_sessions_dir():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def save_session(session: Session):
    _ensure_sessions_dir()
    session.updated_at = datetime.utcnow()
    data = session.model_dump(mode="json")
    with open(_session_path(session.id), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def load_session(session_id: str) -> Optional[Session]:
    path = _session_path(session_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Session(**data)


def list_sessions() -> list[Session]:
    _ensure_sessions_dir()
    sessions = []
    for path in sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append(Session(**data))
        except Exception:
            pass
    return sessions


def delete_session(session_id: str):
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
