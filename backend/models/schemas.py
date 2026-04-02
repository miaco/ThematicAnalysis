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


class Code(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    description: str
    quote_ids: list[str] = Field(default_factory=list)
    group: Optional[str] = None
    screener_groups: dict = Field(default_factory=dict)


class Theme(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    code_ids: list[str] = Field(default_factory=list)
    quote_count: int = 0
    literature_support: list[str] = Field(default_factory=list)
    interpretation: str = ""
    contradictory_quotes: list[str] = Field(default_factory=list)


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


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state: PipelineState = PipelineState.IDLE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    research_brief: str = ""
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
    validation_results: dict = Field(default_factory=dict)
    error: Optional[str] = None


# Request/response models for API

class CreateSessionRequest(BaseModel):
    research_brief: str
    transcript_source_url: Optional[str] = None


class SetScreenerRequest(BaseModel):
    screener_questions: list[str]


class CodeReviewRequest(BaseModel):
    codes: list[Code]


class POVSelectRequest(BaseModel):
    pov_id: str


class RecommendationSelectRequest(BaseModel):
    selected_ids: list[str]
