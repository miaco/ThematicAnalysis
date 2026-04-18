"""
State machine for validated pipeline state transitions and progress logging.

Provides a StateMachine class that wraps a Session and enforces only valid
state transitions, logs progress to both the persistent progress_log and
an asyncio Queue for SSE streaming, and persists state after each transition.
"""

import asyncio
from datetime import datetime
from typing import Optional

from models.schemas import Session, PipelineState
from storage.session_store import save_session


# ---------------------------------------------------------------------------
# Valid state transitions
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[PipelineState, set[PipelineState]] = {
    PipelineState.IDLE: {PipelineState.PROCESSING_TRANSCRIPTS},
    PipelineState.PROCESSING_TRANSCRIPTS: {PipelineState.AWAITING_CODE_REVIEW, PipelineState.ERROR},
    PipelineState.AWAITING_CODE_REVIEW: {PipelineState.PROCESSING_THEMES, PipelineState.ERROR},
    PipelineState.PROCESSING_THEMES: {PipelineState.AWAITING_POV_SELECTION, PipelineState.ERROR},
    PipelineState.AWAITING_POV_SELECTION: {PipelineState.PROCESSING_RECOMMENDATIONS, PipelineState.ERROR},
    PipelineState.PROCESSING_RECOMMENDATIONS: {PipelineState.AWAITING_RECOMMENDATION_SELECTION, PipelineState.ERROR},
    PipelineState.AWAITING_RECOMMENDATION_SELECTION: {PipelineState.WRITING_REPORT, PipelineState.ERROR},
    PipelineState.WRITING_REPORT: {PipelineState.COMPLETE, PipelineState.ERROR},
    PipelineState.COMPLETE: set(),
    PipelineState.ERROR: {PipelineState.IDLE},
}


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""

    def __init__(self, from_state: PipelineState, to_state: PipelineState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid state transition: {from_state.value} → {to_state.value}"
        )


# ---------------------------------------------------------------------------
# Async progress queue management
# ---------------------------------------------------------------------------

_progress_queues: dict[str, asyncio.Queue] = {}


def get_progress_queue(session_id: str) -> asyncio.Queue:
    """Get or create an asyncio Queue for a session's SSE stream."""
    if session_id not in _progress_queues:
        _progress_queues[session_id] = asyncio.Queue()
    return _progress_queues[session_id]


def remove_progress_queue(session_id: str):
    """Clean up a session's progress queue."""
    _progress_queues.pop(session_id, None)


# ---------------------------------------------------------------------------
# StateMachine
# ---------------------------------------------------------------------------

class StateMachine:
    """
    Manages validated state transitions, progress logging, and persistence
    for a single pipeline session.
    """

    def __init__(self, session: Session):
        self._session = session
        self._queue = get_progress_queue(session.id)

    @property
    def session(self) -> Session:
        return self._session

    @session.setter
    def session(self, value: Session):
        self._session = value

    # -- state transitions --------------------------------------------------

    async def transition_to(self, new_state: PipelineState, message: str) -> None:
        """Validate and apply a state transition. Logs, emits, and persists."""
        current = self._session.state
        allowed = VALID_TRANSITIONS.get(current, set())
        if new_state not in allowed:
            raise InvalidTransitionError(current, new_state)

        self._session.state = new_state
        await self.log(new_state.value, message)
        self.save()

    async def set_error(self, error_msg: str) -> None:
        """Transition to ERROR state, record the error, log, and save."""
        self._session.state = PipelineState.ERROR
        self._session.error = error_msg
        await self.log("error", error_msg)
        self.save()

    # -- logging ------------------------------------------------------------

    async def log(self, stage: str, message: str) -> None:
        """Append to persistent progress_log AND put on the SSE streaming queue."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": stage,
            "message": message,
        }
        self._session.progress_log.append(entry)
        await self._queue.put(entry)

    # -- persistence --------------------------------------------------------

    def save(self) -> None:
        """Persist the current session state to the database."""
        save_session(self._session)
