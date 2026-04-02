"""
Orchestrator: Runs the thematic analysis pipeline, managing state transitions
and human-in-the-loop gates. Writes progress to an asyncio Queue for SSE streaming.
"""

import asyncio
from datetime import datetime
from typing import Optional

from models.schemas import Session, PipelineState
from storage.session_store import save_session, load_session
from agents.transcript_agent import analyze_transcripts
from agents.coding_agent import code_quotes
from agents.evaluation_agent import evaluate_codes, evaluate_themes
from agents.theme_agent import generate_themes
from agents.pov_agent import propose_povs, generate_recommendations
from agents.report_agent import write_report


# Global dict of asyncio Queues per session (for SSE progress streaming)
_progress_queues: dict[str, asyncio.Queue] = {}


def get_progress_queue(session_id: str) -> asyncio.Queue:
    """Get or create an asyncio Queue for a session."""
    if session_id not in _progress_queues:
        _progress_queues[session_id] = asyncio.Queue()
    return _progress_queues[session_id]


def remove_progress_queue(session_id: str):
    """Clean up a session's progress queue."""
    _progress_queues.pop(session_id, None)


async def _emit(session_id: str, stage: str, message: str):
    """Emit a progress event to the session's queue."""
    queue = get_progress_queue(session_id)
    await queue.put({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": stage,
        "message": message,
    })


async def run_pipeline(session_id: str):
    """
    Main pipeline orchestrator. Runs the appropriate stages based on current state,
    stops at human gates, and persists state after each stage.

    States flow:
    IDLE -> PROCESSING_TRANSCRIPTS -> AWAITING_CODE_REVIEW
    (after human review) -> PROCESSING_THEMES -> AWAITING_POV_SELECTION
    (after human selects POV) -> PROCESSING_RECOMMENDATIONS -> AWAITING_RECOMMENDATION_SELECTION
    (after human selects recs) -> WRITING_REPORT -> COMPLETE
    """
    session = load_session(session_id)
    if not session:
        await _emit(session_id, "error", f"Session {session_id} not found")
        return

    try:
        current_state = session.state

        # STAGE 1: Process transcripts → await code review
        if current_state == PipelineState.IDLE:
            await _emit(session_id, "processing_transcripts", "Starting transcript analysis...")
            session.state = PipelineState.PROCESSING_TRANSCRIPTS
            save_session(session)

            session = await asyncio.to_thread(_run_transcript_analysis, session)
            await _emit(session_id, "processing_transcripts", f"Extracted {len(session.quotes)} quotes from {len(session.transcripts)} transcripts")

            session = await asyncio.to_thread(_run_coding, session)
            await _emit(session_id, "coding", f"Generated {len(session.codes)} codes.")

            session = await asyncio.to_thread(_run_code_evaluation, session)
            await _emit(session_id, "evaluation", f"Evaluated code quality. Ready for human review.")

            session.state = PipelineState.AWAITING_CODE_REVIEW
            save_session(session)
            await _emit(session_id, "awaiting_code_review", "Pipeline paused for code review. Please review and edit the codes.")
            return

        # STAGE 2: Process themes + POVs → await POV selection
        elif current_state == PipelineState.AWAITING_CODE_REVIEW:
            await _emit(session_id, "processing_themes", "Code review received. Generating themes...")
            session.state = PipelineState.PROCESSING_THEMES
            save_session(session)

            session = await asyncio.to_thread(_run_theme_generation, session)
            await _emit(session_id, "processing_themes", f"Generated {len(session.themes)} themes.")

            session = await asyncio.to_thread(_run_theme_evaluation, session)
            await _emit(session_id, "evaluation", f"Evaluated theme quality.")

            session = await asyncio.to_thread(_run_pov_generation, session)
            await _emit(session_id, "pov_generation", f"Generated {len(session.povs)} Points of View. Ready for selection.")

            session.state = PipelineState.AWAITING_POV_SELECTION
            save_session(session)
            await _emit(session_id, "awaiting_pov_selection", "Pipeline paused for POV selection. Please select your preferred analytical perspective.")
            return

        # STAGE 3: Generate recommendations → await selection
        elif current_state == PipelineState.AWAITING_POV_SELECTION:
            await _emit(session_id, "processing_recommendations", "POV selected. Generating recommendations...")
            session.state = PipelineState.PROCESSING_RECOMMENDATIONS
            save_session(session)

            session = await asyncio.to_thread(_run_recommendation_generation, session)
            await _emit(session_id, "processing_recommendations", f"Generated {len(session.recommendations)} recommendations. Ready for selection.")

            session.state = PipelineState.AWAITING_RECOMMENDATION_SELECTION
            save_session(session)
            await _emit(session_id, "awaiting_recommendation_selection", "Pipeline paused for recommendation selection. Please select the recommendations to include.")
            return

        # STAGE 4: Write report → complete
        elif current_state == PipelineState.AWAITING_RECOMMENDATION_SELECTION:
            await _emit(session_id, "writing_report", "Recommendations selected. Writing final report...")
            session.state = PipelineState.WRITING_REPORT
            save_session(session)

            session = await asyncio.to_thread(_run_report_writing, session)
            await _emit(session_id, "writing_report", "Report written successfully.")

            session.state = PipelineState.COMPLETE
            save_session(session)
            await _emit(session_id, "complete", "Analysis complete! Your report is ready.")
            return

        else:
            await _emit(session_id, "info", f"Pipeline is in state '{current_state}'. No action needed.")

    except Exception as e:
        error_msg = f"Pipeline error: {str(e)}"
        session = load_session(session_id)
        if session:
            session.state = PipelineState.ERROR
            session.error = error_msg
            save_session(session)
        await _emit(session_id, "error", error_msg)
        raise


def _run_transcript_analysis(session: Session) -> Session:
    """Run transcript analysis synchronously (for asyncio.to_thread)."""
    return analyze_transcripts(session)


def _run_coding(session: Session) -> Session:
    """Run coding synchronously."""
    return code_quotes(session)


def _run_theme_generation(session: Session) -> Session:
    """Run theme generation synchronously."""
    return generate_themes(session)


def _run_pov_generation(session: Session) -> Session:
    """Run POV generation synchronously."""
    return propose_povs(session)


def _run_recommendation_generation(session: Session) -> Session:
    """Run recommendation generation synchronously."""
    return generate_recommendations(session)


def _run_code_evaluation(session: Session) -> Session:
    """Run code quality evaluation synchronously."""
    return evaluate_codes(session)


def _run_theme_evaluation(session: Session) -> Session:
    """Run theme quality evaluation synchronously."""
    return evaluate_themes(session)


def _run_report_writing(session: Session) -> Session:
    """Run report writing synchronously."""
    return write_report(session)
