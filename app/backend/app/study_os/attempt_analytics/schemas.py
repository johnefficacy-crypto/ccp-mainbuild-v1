from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, Field


class SectionBreakdown(BaseModel):
    section_index: int
    section_name: str | None = None
    correct: int
    wrong: int
    unattempted: int
    marks: Decimal
    accuracy_pct: Decimal
    time_used_sec: int


class TopicBreakdown(BaseModel):
    topic_id: str | None = None
    microtopic_id: str | None = None
    attempted: int
    correct: int
    wrong: int
    accuracy_pct: Decimal
    avg_time_sec: Decimal
    difficulty_breakdown: dict


class ResponseClassification(BaseModel):
    question_id: str
    error_type: str
    signals: dict = Field(default_factory=dict)


class AttemptSummary(BaseModel):
    score_raw: Decimal
    score_percentage: Decimal
    total_correct: int
    total_wrong: int
    total_unattempted: int
    total_marked: int
    net_marks: Decimal
    accuracy_pct: Decimal
    time_used_sec: int
    time_remaining_sec: int
    avg_time_per_q_sec: Decimal


class DerivedAttemptAnalytics(BaseModel):
    attempt_id: str
    summary: AttemptSummary
    section_breakdown: list[SectionBreakdown]
    topic_breakdown: list[TopicBreakdown]
    response_classification: list[ResponseClassification]
    stuck_questions: list[str]
    rush_questions: list[str]
    warnings: list[str] = Field(default_factory=list)
