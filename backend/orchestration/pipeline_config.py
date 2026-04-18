"""
Pipeline configuration: stage definitions, model settings, and constants.
"""

from dataclasses import dataclass
from typing import Union

from models.schemas import PipelineState


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

MODELS = {
    "primary": "claude-opus-4-6",
    "evaluation": "claude-sonnet-4-20250514",
}


# ---------------------------------------------------------------------------
# Pipeline stage definitions
# ---------------------------------------------------------------------------

@dataclass
class AgentStage:
    """A pipeline stage that runs an agent function."""
    name: str
    emit_stage: str


@dataclass
class HumanGate:
    """A point where the pipeline pauses for human input."""
    name: str
    pause_state: PipelineState
    resume_state: PipelineState
    emit_stage: str
    message: str
    resume_message: str


PipelineStep = Union[AgentStage, HumanGate]

PIPELINE: list[PipelineStep] = [
    # Phase 1: Transcript analysis through code evaluation
    AgentStage(name="analyze_transcripts", emit_stage="processing_transcripts"),
    AgentStage(name="code_quotes", emit_stage="coding"),
    AgentStage(name="evaluate_codes", emit_stage="evaluation"),
    HumanGate(
        name="code_review",
        pause_state=PipelineState.AWAITING_CODE_REVIEW,
        resume_state=PipelineState.PROCESSING_THEMES,
        emit_stage="awaiting_code_review",
        message="Pipeline paused for code review. Please review and edit the codes.",
        resume_message="Code review received. Generating themes...",
    ),

    # Phase 2: Theme generation through POV proposals
    AgentStage(name="generate_themes", emit_stage="processing_themes"),
    AgentStage(name="evaluate_themes", emit_stage="evaluation"),
    AgentStage(name="propose_povs", emit_stage="pov_generation"),
    HumanGate(
        name="pov_selection",
        pause_state=PipelineState.AWAITING_POV_SELECTION,
        resume_state=PipelineState.PROCESSING_RECOMMENDATIONS,
        emit_stage="awaiting_pov_selection",
        message="Pipeline paused for POV selection. Please select your preferred analytical perspective.",
        resume_message="POV selected. Generating recommendations...",
    ),

    # Phase 3: Recommendation generation
    AgentStage(name="generate_recommendations", emit_stage="processing_recommendations"),
    HumanGate(
        name="recommendation_selection",
        pause_state=PipelineState.AWAITING_RECOMMENDATION_SELECTION,
        resume_state=PipelineState.WRITING_REPORT,
        emit_stage="awaiting_recommendation_selection",
        message="Pipeline paused for recommendation selection. Please select the recommendations to include.",
        resume_message="Recommendations selected. Writing final report...",
    ),

    # Phase 4: Report writing
    AgentStage(name="write_report", emit_stage="writing_report"),
]
