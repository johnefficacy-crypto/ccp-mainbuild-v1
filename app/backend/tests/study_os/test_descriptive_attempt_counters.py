"""Elapsed time and pasted characters: two monotonic, client-reported counters.

WHY. `time_spent_seconds` was always 0 on demo. The client only advanced its
clock while the OPTIONAL timer was running, and the timer is only offered for a
question carrying marks (~13% of the corpus) and only if the aspirant pressed
Start. So the number was not "time spent"; it was "time spent with the
stopwatch running", which for almost every attempt is none.

Both counters are running totals sent with every autosave. The server keeps the
max, because requests do not arrive in the order they were sent and a reloaded
tab starts its own count from wherever it resumed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.persona_questions._stub import SBStub

from app.study_os import descriptive as d

EXAM = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
USER = "user-a"
QID = "q-1"


def _seed(attempt: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "pyq_papers": [
            {"id": "p-1", "exam_id": EXAM, "year": 2025, "paper_code": "P1",
             "trust_status": "pending",
             "metadata": {"paper_kind": "optional", "optional_paper_number": 1}},
        ],
        "pyq_questions": [
            {"id": QID, "pyq_paper_id": "p-1", "question_number": 1,
             "question_text": "Examine sovereignty.", "question_type": "descriptive",
             "reviewer_status": "verified",
             "metadata": {"optional_subject": "PSIR", "marks": 10}},
        ],
        "descriptive_attempts": [attempt] if attempt else [],
    }


def _attempt(**over) -> dict[str, Any]:
    row = {
        "id": "att-1",
        "user_id": USER,
        "pyq_question_id": QID,
        "status": "draft",
        "answer_text": "",
        "word_count": 0,
        "time_spent_seconds": 0,
        "timer_target_seconds": 720,
        "pasted_chars": 0,
        "self_scores": None,
        "self_total": None,
        "notes": None,
        "started_at": "2026-09-21T00:00:00Z",
        "submitted_at": None,
        "updated_at": "2026-09-21T00:00:00Z",
    }
    row.update(over)
    return row


# ── the max rule ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("existing,incoming,expected", [
    (0, 30, 30),
    (30, 45, 45),
    # Out of order: a 10s save overtaking a 45s one must not rewind the clock.
    (45, 10, 45),
    # A reloaded tab counting from zero again.
    (600, 0, 600),
    (None, 12, 12),
    (12, None, None),      # nothing sent → nothing written
    (12, "not a number", None),
    (12, -5, 12),          # a negative can only ever be ignored
])
def test_monotonic_counter(existing, incoming, expected):
    assert d.monotonic_counter(existing, incoming) == expected


def test_autosave_advances_time_spent():
    sb = SBStub(_seed(_attempt()))
    out = d.save_attempt(sb, USER, "att-1", answer_text="One.", time_spent_seconds=30)
    assert out["time_spent_seconds"] == 30

    out = d.save_attempt(sb, USER, "att-1", answer_text="One. Two.", time_spent_seconds=75)
    assert out["time_spent_seconds"] == 75


def test_a_late_autosave_never_rewinds_time():
    sb = SBStub(_seed(_attempt(time_spent_seconds=75)))
    out = d.save_attempt(sb, USER, "att-1", time_spent_seconds=30)
    assert out["time_spent_seconds"] == 75


def test_autosave_without_a_time_leaves_the_stored_one_alone():
    sb = SBStub(_seed(_attempt(time_spent_seconds=90)))
    out = d.save_attempt(sb, USER, "att-1", answer_text="Text only.")
    assert out["time_spent_seconds"] == 90


def test_submit_carries_the_final_counters():
    """The last autosave can be ten seconds stale, and submit is the one moment
    the elapsed time has to be right."""
    sb = SBStub(_seed(_attempt(time_spent_seconds=100, answer_text="An answer.")))
    scores = {k: 1 for k in d.RUBRIC_KEYS}
    out = d.submit_attempt(
        sb, USER, "att-1", self_scores=scores, time_spent_seconds=118, pasted_chars=40
    )
    assert out["time_spent_seconds"] == 118
    assert out["pasted_chars"] == 40
    assert out["status"] == "submitted"


def test_submit_does_not_rewind_either_counter():
    sb = SBStub(_seed(_attempt(time_spent_seconds=300, pasted_chars=90,
                               answer_text="An answer.")))
    scores = {k: 2 for k in d.RUBRIC_KEYS}
    out = d.submit_attempt(
        sb, USER, "att-1", self_scores=scores, time_spent_seconds=5, pasted_chars=0
    )
    assert out["time_spent_seconds"] == 300
    assert out["pasted_chars"] == 90


# ── pasted_chars round trip ──────────────────────────────────────────────


def test_pasted_chars_round_trips_through_autosave():
    sb = SBStub(_seed(_attempt()))
    out = d.save_attempt(sb, USER, "att-1", answer_text="Pasted.", pasted_chars=120)
    assert out["pasted_chars"] == 120

    out = d.save_attempt(sb, USER, "att-1", answer_text="Pasted more.", pasted_chars=200)
    assert out["pasted_chars"] == 200


def test_a_new_attempt_starts_at_zero_pasted_not_null():
    """0 and null mean different things. A fresh attempt measured nothing
    pasted; a pre-migration attempt was never measured at all."""
    sb = SBStub(_seed())
    out = d.open_attempt(sb, USER, QID)
    assert out["pasted_chars"] == 0
    assert out["time_spent_seconds"] == 0


def test_an_attempt_from_before_paste_tracking_reads_as_null():
    sb = SBStub(_seed(_attempt(pasted_chars=None)))
    out = d.list_attempts(sb, USER)
    assert out["items"][0]["pasted_chars"] is None


# ── migration 295 ────────────────────────────────────────────────────────

_MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "app" / "supabase" / "migrations"
    / "295_descriptive_attempts_pasted_chars.sql"
)


def _executable_sql() -> str:
    """The statements actually run — prose in the header is not a grant."""
    lines = [
        line for line in _MIGRATION.read_text().splitlines()
        if not line.lstrip().startswith("--")
    ]
    return "\n".join(lines).lower()


def test_migration_adds_the_column_additively():
    sql = _executable_sql()
    assert "add column if not exists pasted_chars integer null" in sql
    assert "pasted_chars >= 0" in sql
    # Additive only: nullable, no backfill, nothing dropped or rewritten.
    ddl = sql[sql.index("alter table"):sql.index("comment on")]
    assert "not null" not in ddl
    assert "default" not in ddl
    assert "drop column" not in sql
    assert "update public.descriptive_attempts" not in sql


def test_migration_revokes_the_four_privileges():
    sql = _executable_sql()
    revoke = sql[sql.index("revoke"):]
    for privilege in ("delete", "truncate", "references", "trigger"):
        assert privilege in revoke, privilege
    assert "from authenticated" in revoke


def test_migration_keeps_select_insert_update():
    """Revoking too much would lock the aspirant out of their own answers."""
    sql = _executable_sql()
    revoke = sql[sql.index("revoke"):sql.index("notify pgrst")]
    for privilege in ("select", "insert", "update"):
        assert privilege not in revoke, privilege
    # And nothing here drops the owner policies 293 created.
    assert "drop policy" not in sql
