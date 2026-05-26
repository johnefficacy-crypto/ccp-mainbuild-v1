from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from .classifier import classify_response
from .scoring import compute_scoring
from .schemas import DerivedAttemptAnalytics
from .time_analytics import compute_dwell_times
from .topic_breakdown import compute_topic_breakdown

logger = logging.getLogger("career_copilot.study_os.attempt_analytics")


def derive_attempt_analytics(attempt: dict, responses: list[dict], events: list[dict]) -> DerivedAttemptAnalytics:
    dwell_by_q, warnings = compute_dwell_times(responses, events, attempt.get("submitted_at"))
    summary, sections = compute_scoring(attempt, responses, dwell_by_q)
    topics = compute_topic_breakdown(responses, dwell_by_q)

    classifications = []
    stuck, rush = [], []
    for r in responses:
        q = r.get("question_snapshot") or {}
        row = {
            "is_correct": r.get("is_correct"),
            "selected_option_id": r.get("selected_option_id"),
            "time_spent_sec": dwell_by_q.get(r["question_id"], 0),
            "expected_time_sec": q.get("expected_time_sec") or 60,
            "is_marked_for_review": r.get("is_marked_for_review"),
            "was_visited": r.get("is_visited"),
            "difficulty": q.get("difficulty") or "medium",
            "subject": q.get("subject") or q.get("subject_name"),
            "option_tags": q.get("option_tags") or {},
        }
        et, signals = classify_response(row)
        classifications.append({"question_id": r["question_id"], "error_type": et, "signals": signals})
        dwell = int(row["time_spent_sec"])
        expected = int(row["expected_time_sec"] or 1)
        if dwell > 3 * expected:
            stuck.append(r["question_id"])
        if (not bool(r.get("is_correct"))) and dwell < 0.3 * expected:
            rush.append(r["question_id"])

    return DerivedAttemptAnalytics(
        attempt_id=attempt["id"],
        summary=summary,
        section_breakdown=sections,
        topic_breakdown=topics,
        response_classification=classifications,
        stuck_questions=stuck,
        rush_questions=rush,
        warnings=warnings,
    )


def compute_and_persist(supabase: Any, attempt_id: str) -> DerivedAttemptAnalytics:
    attempt = (supabase.table("mock_attempts").select("*").eq("id", attempt_id).limit(1).execute().data or [None])[0]
    if not attempt:
        raise HTTPException(status_code=404, detail="attempt not found")
    if attempt.get("status") != "submitted":
        raise HTTPException(status_code=422, detail="attempt must be submitted")
    responses = supabase.table("mock_attempt_responses").select("*").eq("attempt_id", attempt_id).execute().data or []
    events = []
    try:
        events = supabase.table("mock_attempt_events").select("*").eq("attempt_id", attempt_id).execute().data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("attempt events unavailable for %s: %s", attempt_id, exc)

    derived = derive_attempt_analytics(attempt, responses, events)
    s = derived.summary.model_dump(mode="json")
    supabase.table("mock_attempt_summary").upsert({"attempt_id": attempt_id, **s}, on_conflict="attempt_id").execute()

    for row in derived.section_breakdown:
        payload = row.model_dump(mode="json")
        supabase.table("mock_attempt_section_breakdown").upsert({"attempt_id": attempt_id, **payload}, on_conflict="attempt_id,section_index").execute()
    for row in derived.topic_breakdown:
        payload = row.model_dump(mode="json")
        supabase.table("mock_attempt_topic_breakdown").upsert({"attempt_id": attempt_id, **payload}, on_conflict="attempt_id,topic_id,microtopic_id").execute()
    for row in derived.response_classification:
        payload = row.model_dump(mode="json")
        supabase.table("mock_attempt_response_classification").upsert({"attempt_id": attempt_id, **payload}, on_conflict="attempt_id,question_id").execute()
    return derived
