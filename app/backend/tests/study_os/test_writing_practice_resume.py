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
    session = {"id": "S1", "prompt_id": "P1", "mode": mode}
    if mode == "exam" and feedback_released:
        session["feedback_released_at"] = "2000-01-01T00:00:00+00:00"
    tables = {
        "writing_prompts": [
            {
                "id": "P1",
                "exercise_type": "sentence_construction",
                "prompt_text": "Use the word diligent.",
                "source_text": None,
                "required_words": ["diligent"],
                "required_sentence_count": 1,
                "difficulty_level": 3,
                "min_words": 4,
                "max_words": 20,
            }
        ],
        "writing_session_units": [
            {"id": "u1", "session_id": "S1", "unit_number": 1, "status": "rewrite_required",
             "practice_microtopic_id": "m1", "unit_constraints": {}},
        ],
        "writing_unit_versions": [
            {"id": "v1", "unit_id": "u1", "version_number": 1, "answer_text": "She is diligent.",
             "server_word_count": 3},
            {"id": "v0", "unit_id": "u1", "version_number": 0, "answer_text": "old", "server_word_count": 1},
        ],
        "writing_evaluations": [
            {"id": "e1", "unit_version_id": "v1", "evaluation_revision": 1,
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
    assert out["feedback_released"] is True

    unit = out["units"][0]
    # Latest version is v1 (version_number 1), not the stale v0.
    assert unit["latest_version"]["id"] == "v1"
    assert unit["latest_version"]["version_number"] == 1
    assert unit["latest_version"]["answer_text"] == "She is diligent."
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
