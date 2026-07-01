"""Required-word coverage session check (architecture §4.7).

Computes session-level required-word coverage over the latest submitted version
of each unit, pins it to the current ``version_set_hash`` (so a later rewrite
supersedes the check), writes an append-only ``writing_session_checks`` row, and
returns the result. The tokenisation is the shared deterministic engine.
"""
from __future__ import annotations

import logging
from typing import Any

from app.study_os.writing_practice.deterministic import required_word_coverage
from app.study_os.writing_practice.version_set_hash import (
    UnitRow,
    compute_version_set_hash,
)

logger = logging.getLogger("career_copilot.study_os.writing_coverage")

CHECKER_VERSION = "coverage-v1"
CHECK_TYPE_REQUIRED_WORD_COVERAGE = "required_word_coverage"


def _latest_versions(supabase: Any, session_id: str) -> list[dict]:
    """Latest submitted version per unit, with unit number + content hash."""
    units = (
        supabase.table("writing_session_units")
        .select("id,unit_number")
        .eq("session_id", session_id)
        .order("unit_number")
        .execute()
    ).data or []
    out: list[dict] = []
    for u in units:
        rows = (
            supabase.table("writing_unit_versions")
            .select("id,version_number,answer_text,content_hash")
            .eq("unit_id", u["id"])
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        ).data or []
        if rows:
            out.append({
                "unit_number": u["unit_number"],
                "unit_id": u["id"],
                "version_id": rows[0]["id"],
                "answer_text": rows[0]["answer_text"],
                "content_hash": rows[0]["content_hash"],
            })
    return out


def current_version_set_hash(latest: list[dict]) -> str:
    return compute_version_set_hash([
        UnitRow(
            unit_number=r["unit_number"],
            id=r["unit_id"],
            version_id=r["version_id"],
            content_hash=r["content_hash"],
        )
        for r in latest
    ])


def run_coverage_check(supabase: Any, session_id: str, required_words: list[str]) -> dict:
    """Compute + persist the required-word coverage check for the session.

    Returns {passed, version_set_hash, per_word}. If there are no required words
    the check trivially passes. The row is written append-only; a superseding
    rewrite changes the version_set_hash and requires a fresh check.
    """
    latest = _latest_versions(supabase, session_id)
    vsh = current_version_set_hash(latest)
    passed, per_word = required_word_coverage(
        required_words or [], [r["answer_text"] for r in latest]
    )

    supabase.table("writing_session_checks").insert({
        "session_id": session_id,
        "check_type": CHECK_TYPE_REQUIRED_WORD_COVERAGE,
        "version_set_hash": vsh,
        "passed": passed,
        "details": {"per_word": per_word},
        "checker_version": CHECKER_VERSION,
    }).execute()

    return {"passed": passed, "version_set_hash": vsh, "per_word": per_word}


def latest_authoritative_coverage(supabase: Any, session_id: str) -> bool:
    """Whether the latest coverage check is authoritative AND passed (§4.7a).

    A check is authoritative only when its version_set_hash equals the current
    session hash; otherwise a rewrite has superseded it and coverage is unknown
    (treated as not-passed for the completion gate).
    """
    latest = _latest_versions(supabase, session_id)
    if not latest:
        return False
    current = current_version_set_hash(latest)
    rows = (
        supabase.table("writing_session_checks")
        .select("version_set_hash,passed,created_at")
        .eq("session_id", session_id)
        .eq("check_type", CHECK_TYPE_REQUIRED_WORD_COVERAGE)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        return False
    return bool(rows[0]["passed"]) and rows[0]["version_set_hash"] == current
