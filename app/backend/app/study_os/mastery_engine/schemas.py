from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AttemptQuestionAnalytics(BaseModel):
    question_id: str
    topic_id: str
    microtopic_id: str | None = None
    is_correct: bool
    difficulty: str = "medium"
    source_type: str = "authored"
    pyq_year: int | None = None
    expected_time_sec: int | None = None
    actual_time_sec: int | None = None
    error_type: str | None = None
    confidence: Decimal = Field(default=Decimal("0.5"))


class AttemptTopicAnalytics(BaseModel):
    topic_id: str
    microtopic_id: str | None = None
    attempted: int = 0
    correct: int = 0
    accuracy_pct: Decimal = Field(default=Decimal("0"))


class DerivedAttemptAnalytics(BaseModel):
    attempt_id: UUID
    user_id: str
    questions: list[AttemptQuestionAnalytics] = Field(default_factory=list)
    topics: list[AttemptTopicAnalytics] = Field(default_factory=list)


class MasteryDelta(BaseModel):
    user_id: str
    topic_id: str
    current_mastery: Decimal
    expected_accuracy: Decimal
    observed_accuracy: Decimal
    raw_delta: Decimal
    capped_delta: Decimal
    attempted: int


class ErrorPatternSignal(BaseModel):
    user_id: str
    topic_id: str
    microtopic_id: str | None = None
    error_type: str
    count: int = 1
    evidence_question_ids: list[str] = Field(default_factory=list)
    signal_strength: Decimal


class CorrectionEvidence(BaseModel):
    accuracy_pct: Decimal
    error_types: list[str] = Field(default_factory=list)
    related_question_ids: list[str] = Field(default_factory=list)
    source_trust: str | None = None
    source_attempt_id: UUID | None = None
    canonical_topic_id: str | None = None
    canonical_microtopic_id: str | None = None


class CorrectionTaskDraft(BaseModel):
    user_id: str
    topic_id: str
    microtopic_id: str | None = None
    task_type: str
    priority: int
    reason: str
    evidence: CorrectionEvidence
    estimated_minutes: int
    source_attempt_id: UUID


class DerivationResult(BaseModel):
    mastery_deltas: list[MasteryDelta] = Field(default_factory=list)
    error_signals: list[ErrorPatternSignal] = Field(default_factory=list)
    correction_task_drafts: list[CorrectionTaskDraft] = Field(default_factory=list)
