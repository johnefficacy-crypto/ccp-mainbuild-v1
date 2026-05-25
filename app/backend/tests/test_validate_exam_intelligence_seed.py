"""Schema-truth regression for ``scripts/validate_exam_intelligence_seed.py``.

Migration 030 (line 117) defines the notes column on
``exam_topic_coverage`` as ``review_notes``. The validator had drifted to
selecting ``reviewer_notes``, which PostgREST rejects with 42703
(``column ... does not exist``).

The shared ``SBStub`` ignores the SELECT column list, so it cannot catch
this class of bug. This suite uses a schema-aware stub that raises when a
SELECT references a column the table does not have — exactly how the real
client would fail — and asserts the validator runs clean against a valid
in-memory seed.
"""
from __future__ import annotations

import sys

import pytest

from scripts import validate_exam_intelligence_seed as validator


class SchemaError(Exception):
    """Mimics PostgREST 42703 for an unknown column in a SELECT."""


# Column allowlists grounded in the migrations the validator reads. Only the
# columns the validator actually selects need to be present, except for
# ``exam_topic_coverage`` which carries its full migration-030 schema so the
# absence of ``reviewer_notes`` is asserted, not assumed.
SCHEMAS: dict[str, set[str]] = {
    "exams": {"id", "slug", "name", "is_active"},
    "exam_cycles": {"id", "status", "exam_start", "exam_end", "exam_id"},
    "exam_phases": {"id", "phase_name", "status", "exam_id"},
    # Full schema from migration 030 — note: there is no ``reviewer_notes``.
    "exam_topic_coverage": {
        "id", "exam_id", "exam_cycle_id", "exam_phase_id", "section_id",
        "topic_id", "coverage_depth", "expected_difficulty",
        "exam_priority_score", "is_high_yield", "confidence_score",
        "source_basis", "model_version", "reviewer_status", "reviewed_by",
        "reviewed_at", "review_notes", "metadata", "created_at", "updated_at",
    },
    "topics": {"id", "is_active"},
    "subjects": {"id", "is_active"},
    "syllabus_topic_mentions": {"topic_id", "reviewer_status", "reviewer_notes", "exam_id"},
    "pyq_question_topic_tags": {"question_id", "topic_id", "reviewer_status"},
    "pyq_questions": {"id", "reviewer_status"},
    "exam_competition_metrics": {"id", "reviewer_status", "exam_id"},
    "exam_policy_updates": {
        "id", "source_type", "reviewer_status", "exam_id",
        "affects_plan", "affects_deadline", "affects_eligibility",
        "affects_documents", "affects_syllabus", "affects_vacancy",
    },
}


class _Exec:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table, rows):
        self.table = table
        self.rows = rows
        self.filters: list[tuple[str, object]] = []

    def select(self, select: str):
        allowed = SCHEMAS[self.table]
        for col in (c.strip() for c in select.split(",")):
            if col and col not in allowed:
                raise SchemaError(
                    f'column {self.table}.{col} does not exist'
                )
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, _n):
        return self

    def execute(self):
        out = [
            r for r in self.rows
            if all(r.get(k) == v for k, v in self.filters)
        ]
        return _Exec(out)


class SchemaAwareStub:
    def __init__(self, db: dict[str, list[dict]]):
        self.db = db

    def table(self, name: str):
        return _Query(name, self.db.get(name, []))


def _valid_seed() -> dict[str, list[dict]]:
    return {
        "exams": [
            {"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL", "is_active": True}
        ],
        "exam_cycles": [
            {"id": "cyc-1", "status": "open", "exam_start": None, "exam_end": None, "exam_id": "exam-1"}
        ],
        "exam_phases": [
            {"id": "ph-1", "phase_name": "Tier 1", "status": "active", "exam_id": "exam-1"}
        ],
        "exam_topic_coverage": [
            {
                "id": "cov-1",
                "exam_id": "exam-1",
                "topic_id": "topic-1",
                "source_basis": "admin_review",
                "reviewer_status": "locked",
                "review_notes": "verified against official syllabus",
            }
        ],
        "topics": [{"id": "topic-1", "is_active": True}],
        "subjects": [{"id": "subj-1", "is_active": True}],
        "syllabus_topic_mentions": [],
        "pyq_question_topic_tags": [],
        "pyq_questions": [],
        "exam_competition_metrics": [],
        "exam_policy_updates": [],
    }


@pytest.fixture
def _patch_client(monkeypatch):
    def _install(db):
        monkeypatch.setattr(validator, "get_supabase_admin", lambda: SchemaAwareStub(db))
    return _install


def test_validator_runs_without_schema_error(monkeypatch, _patch_client):
    """The validator must only select columns that exist. With the corrected
    ``review_notes`` column it runs to completion and reports a ready exam.
    """
    _patch_client(_valid_seed())
    monkeypatch.setattr(sys, "argv", ["validate", "--exam-slug", "ssc-cgl", "--strict"])
    assert validator.main() == 0


def test_exam_topic_coverage_select_rejects_legacy_reviewer_notes():
    """Pins the bug directly: selecting the drifted ``reviewer_notes`` from
    ``exam_topic_coverage`` raises, while ``review_notes`` is accepted. If the
    validator ever regresses, ``test_validator_runs_without_schema_error``
    fails for this reason.
    """
    q = _Query("exam_topic_coverage", [])
    with pytest.raises(SchemaError):
        q.select("id,topic_id,source_basis,reviewer_status,reviewer_notes")

    # Sanity: the corrected column passes.
    _Query("exam_topic_coverage", []).select(
        "id,topic_id,source_basis,reviewer_status,review_notes"
    )
