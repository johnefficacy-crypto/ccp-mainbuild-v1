"""EWP-4 Error Lab read-surface tests.

Exercises the pure gating/grouping logic of
``writing_practice.error_lab`` / ``error_summary`` against a fake Supabase,
proving the hard read constraints: owner-scoped, feedback-released only,
``affects_current_state=true`` only, and effective-invalidation aware
(§4.8 / §4.10a). No pending/rejected/stale/invalidated finding may leak.

Skips if the module's optional deps are unavailable locally (present in CI).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("supabase")

from app.api import writing_practice as wp  # noqa: E402


class _Query:
    """Minimal chainable stand-in for the Supabase query builder."""

    def __init__(self, rows):
        self._rows = list(rows)

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def in_(self, col, vals):
        vals = set(vals)
        self._rows = [r for r in self._rows if r.get(col) in vals]
        return self

    def order(self, col, desc=False):
        self._rows = sorted(self._rows, key=lambda r: r.get(col), reverse=desc)
        return self

    class _Res:
        def __init__(self, data):
            self.data = data

    def execute(self):
        return _Query._Res(self._rows)


class _FakeSupabase:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return _Query(self._tables.get(name, []))


def _base_tables():
    """One released learning session with two current-state issues on two microtopics."""
    return {
        "writing_sessions": [
            {"id": "S1", "user_id": "U1", "mode": "learning", "feedback_released_at": None},
            # Another user's released session — must never leak in.
            {"id": "S9", "user_id": "U2", "mode": "learning", "feedback_released_at": None},
        ],
        "writing_session_units": [
            {"id": "u1", "session_id": "S1"},
            {"id": "u9", "session_id": "S9"},
        ],
        "writing_unit_versions": [
            {"id": "v1", "unit_id": "u1"},
            {"id": "v9", "unit_id": "u9"},
        ],
        "writing_evaluations": [
            {"id": "e1", "unit_version_id": "v1"},
            {"id": "e9", "unit_version_id": "v9"},
        ],
        "writing_issue_events": [
            {"id": "i1", "evaluation_id": "e1", "microtopic_id": "m1",
             "issue_type": "subject_verb_agreement", "severity": "must_fix",
             "quoted_text": "they was", "explanation": "Use 'were'.",
             "suggested_text": "they were", "span_start_utf16": 0,
             "span_end_utf16": 8, "affects_current_state": True,
             "created_at": "2026-06-01T00:00:00+00:00"},
            {"id": "i2", "evaluation_id": "e1", "microtopic_id": "m1",
             "issue_type": "article_use", "severity": "should_fix",
             "quoted_text": "a apple", "explanation": "Use 'an'.",
             "suggested_text": "an apple", "span_start_utf16": 10,
             "span_end_utf16": 17, "affects_current_state": True,
             "created_at": "2026-06-02T00:00:00+00:00"},
            {"id": "i3", "evaluation_id": "e1", "microtopic_id": None,
             "issue_type": "word_choice", "severity": "advisory",
             "quoted_text": "big", "explanation": "Consider 'large'.",
             "suggested_text": "large", "span_start_utf16": 20,
             "span_end_utf16": 23, "affects_current_state": True,
             "created_at": "2026-06-03T00:00:00+00:00"},
            # Stale finding (non-latest version) — must be excluded.
            {"id": "i_stale", "evaluation_id": "e1", "microtopic_id": "m1",
             "issue_type": "tense", "severity": "must_fix", "quoted_text": "x",
             "explanation": "stale", "affects_current_state": False,
             "created_at": "2026-06-04T00:00:00+00:00"},
            # Another user's issue — must be excluded by owner scoping.
            {"id": "i_other", "evaluation_id": "e9", "microtopic_id": "m1",
             "issue_type": "tense", "severity": "must_fix", "quoted_text": "y",
             "explanation": "not mine", "affects_current_state": True,
             "created_at": "2026-06-05T00:00:00+00:00"},
        ],
        "writing_issue_review_events": [],
    }


def test_error_lab_groups_current_state_issues_by_microtopic():
    sb = _FakeSupabase(_base_tables())
    # error_lab reads via get_supabase_admin(); exercise the underlying logic.
    rows = wp._current_state_issue_events(
        sb, "U1",
        "id,microtopic_id,issue_type,severity,quoted_text,explanation,"
        "suggested_text,span_start_utf16,span_end_utf16,created_at",
    )
    ids = {r["id"] for r in rows}
    assert ids == {"i1", "i2", "i3"}  # stale + other-user excluded


def test_error_lab_excludes_effectively_invalidated_issue():
    tables = _base_tables()
    # i1 invalidated, then confirmed (higher event_seq) -> effective active (kept).
    # i2 confirmed, then invalidated (higher event_seq) -> effective invalidated (dropped).
    tables["writing_issue_review_events"] = [
        {"issue_event_id": "i1", "decision": "invalidated",
         "created_at": "2026-06-10T00:00:00+00:00", "event_seq": 1},
        {"issue_event_id": "i1", "decision": "confirmed",
         "created_at": "2026-06-10T00:00:00+00:00", "event_seq": 2},
        {"issue_event_id": "i2", "decision": "confirmed",
         "created_at": "2026-06-10T00:00:00+00:00", "event_seq": 3},
        {"issue_event_id": "i2", "decision": "invalidated",
         "created_at": "2026-06-10T00:00:00+00:00", "event_seq": 4},
    ]
    sb = _FakeSupabase(tables)
    rows = wp._current_state_issue_events(sb, "U1", "id,microtopic_id")
    ids = {r["id"] for r in rows}
    assert "i1" in ids       # invalidated -> confirmed re-asserts active
    assert "i2" not in ids   # confirmed -> invalidated is withdrawn
    assert "i3" in ids


def test_effective_invalidation_uses_event_seq_not_id_or_created_at():
    # Same created_at; the LOWER event_seq is 'confirmed' and the HIGHER is
    # 'invalidated' -> effective invalidated. Proves event_seq is the tiebreak.
    events = [
        {"issue_event_id": "i1", "decision": "confirmed",
         "created_at": "2026-06-10T00:00:00+00:00", "event_seq": 5},
        {"issue_event_id": "i1", "decision": "invalidated",
         "created_at": "2026-06-10T00:00:00+00:00", "event_seq": 6},
    ]
    sb = _FakeSupabase({"writing_issue_review_events": events})
    assert wp._effectively_invalidated_issue_ids(sb, ["i1"]) == {"i1"}


def test_error_summary_counts_exclude_stale_and_invalidated():
    tables = _base_tables()
    tables["writing_issue_review_events"] = [
        {"issue_event_id": "i2", "decision": "invalidated",
         "created_at": "2026-06-10T00:00:00+00:00", "event_seq": 1},
    ]
    sb = _FakeSupabase(tables)
    rows = wp._current_state_issue_events(sb, "U1", "id,microtopic_id")
    counts: dict = {}
    for r in rows:
        key = r.get("microtopic_id") or "unmapped"
        counts[key] = counts.get(key, 0) + 1
    # i1 (m1) kept, i2 (m1) invalidated, i3 unmapped kept.
    assert counts == {"m1": 1, "unmapped": 1}


def test_unreleased_exam_session_yields_no_issues():
    tables = _base_tables()
    # Make S1 an exam session with a FUTURE release -> not released -> no issues.
    tables["writing_sessions"][0] = {
        "id": "S1", "user_id": "U1", "mode": "exam",
        "feedback_released_at": "2999-01-01T00:00:00+00:00",
    }
    sb = _FakeSupabase(tables)
    assert wp._current_state_issue_events(sb, "U1", "id,microtopic_id") == []


def test_no_sessions_returns_empty():
    sb = _FakeSupabase({"writing_sessions": []})
    assert wp._released_evaluation_ids(sb, "U1") == []
    assert wp._current_state_issue_events(sb, "U1", "id,microtopic_id") == []
