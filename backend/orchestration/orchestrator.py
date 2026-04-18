"""
Orchestrator: Runs the thematic analysis pipeline using a declarative stage
registry, validated state transitions via StateMachine, and human-in-the-loop gates.
"""

import asyncio
from typing import Callable, Optional

from models.schemas import Session, PipelineState
from storage.session_store import load_session
from orchestration.pipeline_config import PIPELINE, AgentStage, HumanGate
from orchestration.state_machine import StateMachine, get_progress_queue, remove_progress_queue
from agents.demo_data import DEMO_MODE


# ---------------------------------------------------------------------------
# Agent function registry
# ---------------------------------------------------------------------------

if DEMO_MODE:
    from agents.demo_data import (
        demo_analyze_transcripts,
        demo_code_quotes,
        demo_evaluate_codes,
        demo_evaluate_themes,
        demo_generate_themes,
        demo_propose_povs,
        demo_generate_recommendations,
        demo_write_report,
    )
    AGENT_REGISTRY: dict[str, Callable[[Session], Session]] = {
        "analyze_transcripts": demo_analyze_transcripts,
        "code_quotes": demo_code_quotes,
        "evaluate_codes": demo_evaluate_codes,
        "evaluate_themes": demo_evaluate_themes,
        "generate_themes": demo_generate_themes,
        "propose_povs": demo_propose_povs,
        "generate_recommendations": demo_generate_recommendations,
        "write_report": demo_write_report,
    }
else:
    from agents.step1_transcript_agent import analyze_transcripts
    from agents.step2_coding_agent import code_quotes
    from agents.step3_5_evaluation_agent import evaluate_codes, evaluate_themes
    from agents.step4_theme_agent import generate_themes
    from agents.step6_pov_agent import propose_povs
    from agents.step7_recommendation_agent import generate_recommendations
    from agents.step8_report_agent import write_report

    AGENT_REGISTRY: dict[str, Callable[[Session], Session]] = {
        "analyze_transcripts": analyze_transcripts,
        "code_quotes": code_quotes,
        "evaluate_codes": evaluate_codes,
        "evaluate_themes": evaluate_themes,
        "generate_themes": generate_themes,
        "propose_povs": propose_povs,
        "generate_recommendations": generate_recommendations,
        "write_report": write_report,
    }


# ---------------------------------------------------------------------------
# Done-message callbacks (per agent stage)
# ---------------------------------------------------------------------------

_DONE_MESSAGES: dict[str, Callable[[Session], str]] = {
    "analyze_transcripts": lambda s: f"Extracted {len(s.quotes)} quotes from {len(s.transcripts)} transcripts",
    "code_quotes": lambda s: f"Generated {len(s.codes)} codes.",
    "evaluate_codes": lambda s: "Evaluated code quality. Ready for human review.",
    "generate_themes": lambda s: f"Generated {len(s.themes)} themes.",
    "evaluate_themes": lambda s: "Evaluated theme quality.",
    "propose_povs": lambda s: f"Generated {len(s.povs)} Points of View. Ready for selection.",
    "generate_recommendations": lambda s: f"Generated {len(s.recommendations)} recommendations. Ready for selection.",
    "write_report": lambda s: "Report written successfully.",
}


# ---------------------------------------------------------------------------
# Pipeline resume logic
# ---------------------------------------------------------------------------

def _find_resume_index(state: PipelineState) -> Optional[int]:
    """Determine where to resume in the pipeline based on current state."""
    if state == PipelineState.IDLE:
        return 0
    for i, step in enumerate(PIPELINE):
        if isinstance(step, HumanGate) and step.pause_state == state:
            return i + 1
    return None


# ---------------------------------------------------------------------------
# Main pipeline runner
# ---------------------------------------------------------------------------

async def run_pipeline(session_id: str):
    """
    Run the pipeline from the current session state.  Executes agent stages
    sequentially, pausing at human gates.

    States flow:
    IDLE -> PROCESSING_TRANSCRIPTS -> AWAITING_CODE_REVIEW
    (human review) -> PROCESSING_THEMES -> AWAITING_POV_SELECTION
    (human selects POV) -> PROCESSING_RECOMMENDATIONS -> AWAITING_RECOMMENDATION_SELECTION
    (human selects recs) -> WRITING_REPORT -> COMPLETE
    """
    session = load_session(session_id)
    if not session:
        queue = get_progress_queue(session_id)
        await queue.put({
            "timestamp": "",
            "stage": "error",
            "message": f"Session {session_id} not found",
        })
        return

    sm = StateMachine(session)

    try:
        start_idx = _find_resume_index(session.state)
        if start_idx is None:
            await sm.log("info", f"Pipeline is in state '{session.state}'. No action needed.")
            return

        # Set the initial processing state via validated transition
        if session.state == PipelineState.IDLE:
            await sm.transition_to(
                PipelineState.PROCESSING_TRANSCRIPTS,
                "Starting transcript analysis...",
            )
        else:
            # Resume from a human gate
            for step in PIPELINE:
                if isinstance(step, HumanGate) and step.pause_state == session.state:
                    await sm.transition_to(step.resume_state, step.resume_message)
                    break

        # Execute pipeline stages from the resume point
        for step in PIPELINE[start_idx:]:
            if isinstance(step, HumanGate):
                await sm.transition_to(step.pause_state, step.message)
                return  # Pause for human input

            # Run agent stage
            agent_fn = AGENT_REGISTRY[step.name]
            sm.session = await asyncio.to_thread(agent_fn, sm.session)
            sm.save()

            done_msg = _DONE_MESSAGES.get(
                step.name, lambda s: f"{step.name} complete."
            )(sm.session)
            await sm.log(step.emit_stage, done_msg)

        # All stages complete
        await sm.transition_to(
            PipelineState.COMPLETE,
            "Analysis complete! Your report is ready.",
        )

    except Exception as e:
        error_msg = f"Pipeline error: {str(e)}"
        try:
            await sm.set_error(error_msg)
        except Exception:
            # Fallback: directly update session if state machine fails
            session = load_session(session_id)
            if session:
                session.state = PipelineState.ERROR
                session.error = error_msg
                from storage.session_store import save_session
                save_session(session)
        raise
