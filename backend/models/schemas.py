from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class PipelineState(str, Enum):
    IDLE = "idle"
    PROCESSING_TRANSCRIPTS = "processing_transcripts"
    AWAITING_CODE_REVIEW = "awaiting_code_review"
    PROCESSING_THEMES = "processing_themes"
    AWAITING_POV_SELECTION = "awaiting_pov_selection"
    PROCESSING_RECOMMENDATIONS = "processing_recommendations"
    AWAITING_RECOMMENDATION_SELECTION = "awaiting_recommendation_selection"
    WRITING_REPORT = "writing_report"
    COMPLETE = "complete"
    ERROR = "error"


class Participant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    screener_data: dict = Field(default_factory=dict)


class Quote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    participant_id: str
    transcript_file: str
    context: str = ""
    codes: list[str] = Field(default_factory=list)


class EvaluationScores(BaseModel):
    """Quality scores on TAMA's four evaluation criteria (1.0–5.0 scale)."""
    coverage: float = 0.0
    actionability: float = 0.0
    distinctiveness: float = 0.0
    relevance: float = 0.0

    @property
    def average(self) -> float:
        return round((self.coverage + self.actionability + self.distinctiveness + self.relevance) / 4, 2)


class Code(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    description: str
    quote_ids: list[str] = Field(default_factory=list)
    group: Optional[str] = None
    screener_groups: dict = Field(default_factory=dict)
    scores: Optional[EvaluationScores] = None


class Theme(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    code_ids: list[str] = Field(default_factory=list)
    quote_count: int = 0
    literature_support: list[str] = Field(default_factory=list)
    interpretation: str = ""
    contradictory_quotes: list[str] = Field(default_factory=list)
    scores: Optional[EvaluationScores] = None


class POV(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    rationale: str
    supporting_themes: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    supporting_theme: str
    priority: str = "medium"
    selected: bool = False


# ---------------------------------------------------------------------------
# Typed validation results
# ---------------------------------------------------------------------------

class InterRaterCandidate(BaseModel):
    quote_id: str = ""
    quote_text: str = ""
    reason: str = ""
    alternative_codes: list[str] = Field(default_factory=list)


class BiasFlag(BaseModel):
    concern: str = ""
    affected_codes: list[str] = Field(default_factory=list)


class CodingConsistencyIssue(BaseModel):
    quote1_id: str = ""
    quote2_id: str = ""
    similarity_score: float = 0.0
    codes1: list[str] = Field(default_factory=list)
    codes2: list[str] = Field(default_factory=list)
    note: str = ""


class EvaluationSummary(BaseModel):
    scored: int = 0
    total: int = 0
    average_score: float = 0.0


class ValidationResults(BaseModel):
    """Typed validation results accumulated across pipeline stages."""
    # Transcript analysis
    preprocessing_warnings: list[str] = Field(default_factory=list)
    accuracy_issues: list[str] = Field(default_factory=list)
    screener_coverage_warnings: list[str] = Field(default_factory=list)
    # Coding
    inter_rater_candidates: list[InterRaterCandidate] = Field(default_factory=list)
    bias_flags: list[BiasFlag] = Field(default_factory=list)
    coding_summary: str = ""
    consistency_issues: list[CodingConsistencyIssue] = Field(default_factory=list)
    # Evaluation
    code_evaluation: Optional[EvaluationSummary] = None
    theme_evaluation: Optional[EvaluationSummary] = None
    # Theme generation
    thin_description_themes: list[str] = Field(default_factory=list)
    grounding_issues: list[str] = Field(default_factory=list)
    thematic_map_notes: str = ""
    data_saturation_assessment: str = ""
    # Recommendations
    implementation_notes: str = ""
    # Report
    pre_write_checks: list[str] = Field(default_factory=list)
    research_alignment_warnings: str = ""


class ResearchBrief(BaseModel):
    """Structured research brief with distinct sections."""
    research_question: str = ""
    participants: str = ""
    method: str = ""

    def compose(self) -> str:
        """Compose the structured fields into a single research brief string."""
        parts = []
        if self.research_question.strip():
            parts.append(f"Research Question: {self.research_question.strip()}")
        if self.participants.strip():
            parts.append(f"Participants: {self.participants.strip()}")
        if self.method.strip():
            parts.append(f"Method: {self.method.strip()}")
        return "\n\n".join(parts)


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state: PipelineState = PipelineState.IDLE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    research_brief: str = ""
    research_brief_structured: ResearchBrief = Field(default_factory=ResearchBrief)
    transcript_source_url: Optional[str] = None
    transcripts: dict[str, str] = Field(default_factory=dict)
    participants: list[Participant] = Field(default_factory=list)
    screener_questions: list[str] = Field(default_factory=list)
    quotes: list[Quote] = Field(default_factory=list)
    codes: list[Code] = Field(default_factory=list)
    data_saturation_reached: bool = False
    participant_coverage: dict = Field(default_factory=dict)
    themes: list[Theme] = Field(default_factory=list)
    selected_pov: Optional[POV] = None
    povs: list[POV] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    report: Optional[str] = None
    progress_log: list[dict] = Field(default_factory=list)
    validation_results: ValidationResults = Field(default_factory=ValidationResults)
    error: Optional[str] = None


# Request/response models for API

class CreateSessionRequest(BaseModel):
    research_question: str
    participants: str = ""
    method: str = ""
    transcript_source_url: Optional[str] = None


class SetScreenerRequest(BaseModel):
    screener_questions: list[str]


class CodeReviewRequest(BaseModel):
    codes: list[Code]


class POVSelectRequest(BaseModel):
    pov_id: str


class RecommendationSelectRequest(BaseModel):
    selected_ids: list[str]
