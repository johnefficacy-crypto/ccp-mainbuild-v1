"""EWP-3 resume-contract behavioural test for the enriched session read.

Exercises ``writing_practice._session_payload`` against a fake Supabase to prove
the ``GET /sessions/{id}`` response carries what the Sentence Builder needs to
resume: the prompt, and per-unit latest version (answer + CAS baseline) + latest
evaluation (language issues) — with feedback-bearing evaluation fields gated by
release (§13 rule 13). Skips if the module's optional deps are unavailable
locally (present in CI).
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

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    class _Res:
        def __init__(self, data):
            self.data = data

    def maybe_single(self):
        return _Query._SingleExec(self._rows[0] if self._rows else None)

    def single(self):
        return _Query._SingleExec(self._rows[0] if self._rows else None)

    class _SingleExec:
        def __init__(self, row):
            self._row = row

        def execute(self):
            return _Query._Res(self._row)

    def execute(self):
        return _Query._Res(self._rows)


class _FakeSupabase:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return _Query(self._tables.get(name, []))


def _fixture(*, feedback_released=True, mode="learning"):
    session = {
        "id": "S1", "prompt_id": "P1", "mode": mode,
        # The immutable per-session snapshot (migration 221) — _session_prompt
        # must read from here, never the live writing_prompts row.
        "prompt_snapshot": {
            "exercise_type": "sentence_construction",
            "prompt_text": "Use the word diligent.",
            "source_text": None,
            "required_words": ["diligent"],
            "required_sentence_count": 1,
            "difficulty_level": 3,
            "min_words": 4,
            "max_words": 20,
        },
    }
    if mode == "exam" and feedback_released:
        session["feedback_released_at"] = "2000-01-01T00:00:00+00:00"
    tables = {
        # Deliberately DIVERGENT from prompt_snapshot: proves _session_prompt
        # reads the frozen snapshot, never this (possibly since-edited) row.
        "writing_prompts": [
            {
                "id": "P1",
                "exercise_type": "sentence_construction",
                "prompt_text": "EDITED LIVE PROMPT (must not leak into resume)",
                "source_text": "EDITED LIVE SOURCE (must not leak)",
                "required_words": ["EDITED"],
                "required_sentence_count": 99,
                "difficulty_level": 9,
                "min_words": 999,
                "max_words": 999,
            }
        ],
        "writing_session_units": [
            {"id": "u1", "session_id": "S1", "unit_number": 1, "status": "rewrite_required",
             "practice_microtopic_id": "m1", "unit_constraints": {}},
        ],
        "writing_unit_versions": [
            {"id": "v2", "unit_id": "u1", "version_number": 2,
             "answer_text": "She is a diligent scholar.", "server_word_count": 5},
            {"id": "v1", "unit_id": "u1", "version_number": 1, "answer_text": "She is diligent.",
             "server_word_count": 3},
        ],
        "writing_evaluations": [
            {"id": "e1", "unit_version_id": "v2", "evaluation_revision": 1,
             "overall_status": "completed", "deterministic_status": "completed",
             "language_status": "completed",
             "language_result": {"issues": [{"issue_type": "word_choice", "quoted_text": "She"}]},
             "dimension_scores": {"clarity": 4}},
        ],
    }
    return session, _FakeSupabase(tables)


def test_resume_payload_includes_prompt_latest_version_and_issues():
    session, sb = _fixture()
    out = wp._session_payload(sb, session)

    assert out["prompt"]["prompt_text"] == "Use the word diligent."
    assert out["prompt"]["required_words"] == ["diligent"]
    # Never the live (divergent) writing_prompts row — proves the snapshot wins.
    assert "EDITED" not in out["prompt"]["prompt_text"]
    assert out["prompt"]["min_words"] == 4 and out["prompt"]["max_words"] == 20
    assert out["feedback_released"] is True

    unit = out["units"][0]
    # Latest version is v2 (highest version_number), not the prior v1.
    assert unit["latest_version"]["id"] == "v2"
    assert unit["latest_version"]["version_number"] == 2
    assert unit["latest_version"]["answer_text"] == "She is a diligent scholar."
    # Released evaluation carries language issues.
    assert unit["latest_evaluation"]["id"] == "e1"
    assert unit["latest_evaluation"]["language_result"]["issues"][0]["quoted_text"] == "She"


def test_resume_payload_gates_feedback_when_not_released():
    session, sb = _fixture(feedback_released=False, mode="exam")
    out = wp._session_payload(sb, session)

    assert out["feedback_released"] is False
    ev = out["units"][0]["latest_evaluation"]
    # Statuses remain (for polling) but the feedback body is withheld.
    assert ev["id"] == "e1"
    assert ev["overall_status"] == "completed"
    assert "language_result" not in ev
    assert "dimension_scores" not in ev


def test_resume_payload_includes_previous_version_for_diff():
    session, sb = _fixture()
    out = wp._session_payload(sb, session)

    unit = out["units"][0]
    # Latest is still the highest version.
    assert unit["latest_version"]["version_number"] == 2
    # Previous version is the one immediately before the latest (v1), so the
    # accepted before->after diff is reconstructable on reload.
    assert unit["previous_version"]["id"] == "v1"
    assert unit["previous_version"]["version_number"] == 1
    assert unit["previous_version"]["answer_text"] == "She is diligent."


def test_resume_payload_previous_version_none_with_single_version():
    session, sb = _fixture()
    # Collapse to a single version for the unit.
    sb._tables["writing_unit_versions"] = [
        {"id": "v1", "unit_id": "u1", "version_number": 1,
         "answer_text": "She is diligent.", "server_word_count": 3},
    ]
    sb._tables["writing_evaluations"] = [
        {"id": "e1", "unit_version_id": "v1", "evaluation_revision": 1,
         "overall_status": "completed", "deterministic_status": "completed",
         "language_status": "completed", "language_result": {"issues": []},
         "dimension_scores": {"clarity": 4}},
    ]
    out = wp._session_payload(sb, session)

    unit = out["units"][0]
    assert unit["latest_version"]["version_number"] == 1
    assert unit["previous_version"] is None


def test_resume_payload_exam_released_shows_feedback():
    # Exam mode with a PAST feedback_released_at (set by _fixture) — the
    # time-comparison branch resolves released=True, so feedback is shown.
    session, sb = _fixture(feedback_released=True, mode="exam")
    out = wp._session_payload(sb, session)

    assert out["feedback_released"] is True
    ev = out["units"][0]["latest_evaluation"]
    assert ev["id"] == "e1"
    assert ev["language_result"]["issues"][0]["quoted_text"] == "She"


def test_resume_payload_exam_future_release_still_gates():
    # Exam mode with a FUTURE feedback_released_at — the time-comparison branch
    # fails closed (ts > now), so the feedback body stays withheld while the id
    # and statuses remain present for polling.
    session, sb = _fixture(feedback_released=True, mode="exam")
    session["feedback_released_at"] = "2999-01-01T00:00:00+00:00"
    out = wp._session_payload(sb, session)

    assert out["feedback_released"] is False
    ev = out["units"][0]["latest_evaluation"]
    assert ev["id"] == "e1"
    assert ev["overall_status"] == "completed"
    assert "language_result" not in ev
    assert "dimension_scores" not in ev


def test_resume_payload_latest_evaluation_none_when_no_evaluation():
    # Latest version exists but carries no evaluation row.
    session, sb = _fixture()
    sb._tables["writing_evaluations"] = []
    out = wp._session_payload(sb, session)

    unit = out["units"][0]
    assert unit["latest_version"]["id"] == "v2"
    assert unit["latest_evaluation"] is None
