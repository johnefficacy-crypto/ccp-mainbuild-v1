"""Tests for J3 PR 4 — evidence-derived exam_topic_coverage projection.

Covers docs/status/J3-Evidence-Coverage-Scoring-Gate-2026-07-02.md Section I
acceptance criteria: determinism/idempotency, bucket totality (§5.1), the
§5.2 conflict-rule matrix, scope isolation, lifecycle/provenance fields, and
fail-closed reads. The break-the-edge invariant (OD-3) is tested separately
in test_score_snapshots.py against the real scoring module.
"""
from __future__ import annotations

import itertools

import pytest

from tests.persona_questions._stub import SBStub, _Exec, _Query
from app.exam_intelligence.coverage_derivation import (
    DERIVATION_VERSION,
    bucket_coverage_depth,
    derive_topic_coverage,
)


def _snapshot_row(**overrides):
    row = {
        "id": "snap-t1",
        "exam_id": "exam-1",
        "exam_phase_id": None,
        "topic_id": "t1",
        "status": "locked",
        "model_version": "v1.0",
        "exam_priority_score": 72.5,
        "is_high_yield": True,
        "confidence_score": 0.81,
        "evidence_count": 6,
        "computed_at": "2026-01-01T00:00:00Z",
    }
    row.update(overrides)
    return row


# ── I.6 Bucket totality (OD-2 / §5.1) ───────────────────────────────────────


@pytest.mark.parametrize(
    "evidence_count,syllabus_mentions,is_high_yield,expected",
    [
        (0, 0, False, None),
        (0, 0, True, None),
        (0, 1, False, "mentioned"),
        (0, 5, True, "mentioned"),
        (1, 0, False, "light"),
        (2, 3, True, "light"),
        (3, 0, False, "normal"),
        (5, 2, True, "normal"),
        (6, 0, False, "deep"),
        (9, 5, True, "deep"),
        (10, 1, True, "core"),
        (25, 4, True, "core"),
        (10, 0, True, "deep"),       # fails core: no syllabus mention
        (10, 1, False, "deep"),      # fails core: not high yield
        (10, 0, False, "deep"),      # fails core on both counts
        (100, 0, False, "deep"),     # deep fallback at high volume
    ],
)
def test_bucket_totality(evidence_count, syllabus_mentions, is_high_yield, expected):
    assert bucket_coverage_depth(evidence_count, syllabus_mentions, is_high_yield) == expected


def test_bucket_is_total_over_grid():
    """Every combination in a bounded grid maps to exactly one of the five
    named buckets or None — never raises, never falls through."""
    valid_buckets = {None, "mentioned", "light", "normal", "core", "deep"}
    for evidence_count in range(0, 15):
        for syllabus_mentions in range(0, 4):
            for is_high_yield in (True, False):
                result = bucket_coverage_depth(evidence_count, syllabus_mentions, is_high_yield)
                assert result in valid_buckets


# ── I.1 Determinism / idempotency (PD-2) ────────────────────────────────────


def _sb_with_snapshot(**snap_overrides):
    return SBStub({
        "exam_topic_score_snapshots": [_snapshot_row(**snap_overrides)],
    })


def test_determinism_identical_inputs_produce_identical_draft():
    sb1 = _sb_with_snapshot()
    sb2 = _sb_with_snapshot()

    r1 = derive_topic_coverage(sb1, "exam-1")
    r2 = derive_topic_coverage(sb2, "exam-1")

    row1 = sb1.db["exam_topic_coverage"][0]
    row2 = sb2.db["exam_topic_coverage"][0]

    assert r1["written"] == r2["written"] == 1
    for field in ("exam_priority_score", "is_high_yield", "confidence_score", "coverage_depth"):
        assert row1[field] == row2[field]
    assert row1["metadata"]["evidence"]["fingerprint"] == row2["metadata"]["evidence"]["fingerprint"]


def test_rerun_with_unchanged_snapshot_writes_nothing_new():
    sb = _sb_with_snapshot()
    derive_topic_coverage(sb, "exam-1")
    assert len(sb.db["exam_topic_coverage"]) == 1

    result = derive_topic_coverage(sb, "exam-1")
    assert result["written"] == 0
    assert result["updated"] == 0
    assert result["skipped"] == 1
    assert len(sb.db["exam_topic_coverage"]) == 1  # no duplicate row


def test_changing_locked_snapshot_changes_derived_draft_on_next_run():
    sb = _sb_with_snapshot()
    derive_topic_coverage(sb, "exam-1")
    original = dict(sb.db["exam_topic_coverage"][0])

    # A new locked snapshot for the same topic (new snapshot id via new row,
    # simulating an operator locking a fresh compute).
    sb.db["exam_topic_score_snapshots"] = [
        _snapshot_row(id="snap-2", exam_priority_score=91.0, evidence_count=12)
    ]

    result = derive_topic_coverage(sb, "exam-1")
    assert result["updated"] == 1
    updated = sb.db["exam_topic_coverage"][0]
    assert updated["exam_priority_score"] == 91.0
    assert updated["metadata"]["evidence"]["fingerprint"] != original["metadata"]["evidence"]["fingerprint"]


# ── I.2 Evidence-only + primary-only inheritance ────────────────────────────


def test_no_snapshot_no_mentions_writes_nothing():
    sb = SBStub({})
    result = derive_topic_coverage(sb, "exam-1")
    assert result == {
        "written": 0, "updated": 0, "skipped": 0, "triaged": 0, "no_row": 0,
        "errors": 0, "total_topics": 0, "read_error": False, "invalid_scope": False,
        "deltas": [], "triage": [], "stale_reconciled": 0, "stale_rows": [],
    }


def test_draft_reviewed_rejected_snapshots_do_not_influence_derivation():
    """locked_score_snapshots only returns status='locked' rows — a draft or
    rejected snapshot for the same topic must never leak into the derived
    coverage row's priority/confidence numbers."""
    sb = SBStub({
        "exam_topic_score_snapshots": [
            _snapshot_row(status="draft", exam_priority_score=5.0, id="draft-row"),
            _snapshot_row(status="locked", exam_priority_score=72.5, id="locked-row"),
        ],
    })
    derive_topic_coverage(sb, "exam-1")
    row = sb.db["exam_topic_coverage"][0]
    assert row["exam_priority_score"] == 72.5


def test_syllabus_mention_only_topic_gets_mentioned_bucket_with_zero_evidence():
    sb = SBStub({
        "syllabus_topic_mentions": [
            {"exam_id": "exam-1", "exam_phase_id": None, "topic_id": "t9", "reviewer_status": "verified"},
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["written"] == 1
    row = sb.db["exam_topic_coverage"][0]
    assert row["coverage_depth"] == "mentioned"
    assert row["exam_priority_score"] == 0
    assert row["is_high_yield"] is False


def test_unverified_syllabus_mentions_excluded():
    sb = SBStub({
        "syllabus_topic_mentions": [
            {"exam_id": "exam-1", "exam_phase_id": None, "topic_id": "t9", "reviewer_status": "pending"},
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["total_topics"] == 0
    assert "exam_topic_coverage" not in sb.db or sb.db["exam_topic_coverage"] == []


# ── I.3 Conflict rules — complete §5.2 matrix ───────────────────────────────


_HUMAN_BASES = ("manual", "admin_review", "official_syllabus", "pyq_analysis", "hybrid")
_ANY_STATUS = ("draft", "pending_review", "reviewed", "locked", "rejected")


@pytest.mark.parametrize("basis,status", list(itertools.product(_HUMAN_BASES, _ANY_STATUS)))
def test_human_authored_rows_always_skipped_with_delta(basis, status):
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row()],
        "exam_topic_coverage": [
            {
                "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None, "exam_phase_id": None,
                "topic_id": "t1", "source_basis": basis, "reviewer_status": status,
                "exam_priority_score": 1.0, "is_high_yield": False, "confidence_score": 0.1,
                "coverage_depth": "light", "metadata": {},
            }
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["written"] == 0
    assert result["updated"] == 0
    assert result["triaged"] == 0
    assert result["skipped"] == 1
    assert len(result["deltas"]) == 1
    # Row untouched.
    row = sb.db["exam_topic_coverage"][0]
    assert row["source_basis"] == basis
    assert row["reviewer_status"] == status
    assert row["exam_priority_score"] == 1.0


@pytest.mark.parametrize("status", _ANY_STATUS)
def test_model_generated_rows_always_skipped_and_flagged_for_triage(status):
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row()],
        "exam_topic_coverage": [
            {
                "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None, "exam_phase_id": None,
                "topic_id": "t1", "source_basis": "model_generated", "reviewer_status": status,
                "exam_priority_score": 1.0, "is_high_yield": False, "confidence_score": 0.1,
                "coverage_depth": "light", "metadata": {},
            }
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["written"] == 0
    assert result["updated"] == 0
    assert result["skipped"] == 0
    assert result["triaged"] == 1
    assert result["triage"] == [{"topic_id": "t1", "row_id": "row-1"}]
    row = sb.db["exam_topic_coverage"][0]
    assert row["source_basis"] == "model_generated"  # never overwritten


def test_evidence_derived_draft_is_recomputed():
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row(exam_priority_score=88.0)],
        "exam_topic_coverage": [
            {
                "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None, "exam_phase_id": None,
                "topic_id": "t1", "source_basis": "evidence_derived", "reviewer_status": "draft",
                "model_version": DERIVATION_VERSION,
                "exam_priority_score": 1.0, "is_high_yield": False, "confidence_score": 0.1,
                "coverage_depth": "light",
                "metadata": {"evidence": {"fingerprint": "stale-fp"}},
            }
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["updated"] == 1
    row = sb.db["exam_topic_coverage"][0]
    assert row["exam_priority_score"] == 88.0
    assert row["reviewer_status"] == "draft"


def test_evidence_derived_pending_review_is_skipped():
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row()],
        "exam_topic_coverage": [
            {
                "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None, "exam_phase_id": None,
                "topic_id": "t1", "source_basis": "evidence_derived", "reviewer_status": "pending_review",
                "model_version": DERIVATION_VERSION,
                "exam_priority_score": 1.0, "is_high_yield": False, "confidence_score": 0.1,
                "coverage_depth": "light", "metadata": {},
            }
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["skipped"] == 1
    assert result["updated"] == 0
    row = sb.db["exam_topic_coverage"][0]
    assert row["reviewer_status"] == "pending_review"
    assert row["exam_priority_score"] == 1.0


@pytest.mark.parametrize("status", ("reviewed", "locked"))
def test_evidence_derived_reviewed_or_locked_left_unchanged(status):
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row()],
        "exam_topic_coverage": [
            {
                "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None, "exam_phase_id": None,
                "topic_id": "t1", "source_basis": "evidence_derived", "reviewer_status": status,
                "model_version": DERIVATION_VERSION,
                "exam_priority_score": 1.0, "is_high_yield": False, "confidence_score": 0.1,
                "coverage_depth": "light", "metadata": {},
            }
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["skipped"] == 1
    assert result["updated"] == 0
    row = sb.db["exam_topic_coverage"][0]
    assert row["reviewer_status"] == status
    assert row["exam_priority_score"] == 1.0  # never mutated


def test_evidence_derived_rejected_is_recomputed_back_to_draft():
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row(exam_priority_score=55.0)],
        "exam_topic_coverage": [
            {
                "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None, "exam_phase_id": None,
                "topic_id": "t1", "source_basis": "evidence_derived", "reviewer_status": "rejected",
                "model_version": DERIVATION_VERSION,
                "exam_priority_score": 1.0, "is_high_yield": False, "confidence_score": 0.1,
                "coverage_depth": "light", "metadata": {},
            }
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["updated"] == 1
    row = sb.db["exam_topic_coverage"][0]
    assert row["reviewer_status"] == "draft"
    assert row["exam_priority_score"] == 55.0


def test_no_shadow_row_ever_created_when_skipping():
    """PD-4b / OD-5: a skip must never create a second (shadow) coverage row
    for the same scope/topic — the comparison lives only in the delta."""
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row()],
        "exam_topic_coverage": [
            {
                "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None, "exam_phase_id": None,
                "topic_id": "t1", "source_basis": "manual", "reviewer_status": "locked",
                "exam_priority_score": 1.0, "is_high_yield": False, "confidence_score": 0.1,
                "coverage_depth": "light", "metadata": {},
            }
        ],
    })
    derive_topic_coverage(sb, "exam-1")
    assert len(sb.db["exam_topic_coverage"]) == 1


# ── I.5 Lifecycle + provenance ──────────────────────────────────────────────


def test_derived_draft_carries_required_provenance_fields():
    sb = _sb_with_snapshot()
    derive_topic_coverage(sb, "exam-1")
    row = sb.db["exam_topic_coverage"][0]
    assert row["source_basis"] == "evidence_derived"
    assert row["model_version"] == DERIVATION_VERSION
    assert row["reviewer_status"] == "draft"
    evidence = row["metadata"]["evidence"]
    assert evidence["snapshot_id"] is not None
    assert "derivation_basis" in evidence
    assert "fingerprint" in evidence


# ── I.7 Scope isolation (OD-4 / OD-6) ───────────────────────────────────────


def test_exam_wide_and_phase_scoped_derivation_do_not_collide():
    sb = SBStub({
        "exam_phases": [{"id": "phase-1", "exam_id": "exam-1"}],
        "exam_topic_score_snapshots": [
            _snapshot_row(exam_phase_id=None, exam_priority_score=40.0),
            _snapshot_row(exam_phase_id="phase-1", exam_priority_score=70.0),
        ],
    })
    exam_wide = derive_topic_coverage(sb, "exam-1")
    phase_scoped = derive_topic_coverage(sb, "exam-1", exam_phase_id="phase-1")

    assert exam_wide["written"] == 1
    assert phase_scoped["written"] == 1
    rows = sb.db["exam_topic_coverage"]
    assert len(rows) == 2
    by_phase = {r["exam_phase_id"]: r for r in rows}
    assert by_phase[None]["exam_priority_score"] == 40.0
    assert by_phase["phase-1"]["exam_priority_score"] == 70.0


def test_invalid_phase_scope_rejected():
    sb = SBStub({"exam_phases": [{"id": "other-phase", "exam_id": "other-exam"}]})
    result = derive_topic_coverage(sb, "exam-1", exam_phase_id="other-phase")
    assert result["invalid_scope"] is True
    assert sb.db.get("exam_topic_coverage", []) == []


# ── Fail-closed on read error ────────────────────────────────────────────────


class _RaisingTable:
    def __getattr__(self, _name):
        raise RuntimeError("boom")


class _RaisingSB:
    def table(self, name):
        if name == "exam_topic_score_snapshots":
            raise RuntimeError("simulated read failure")
        return SBStub().table(name)


def test_read_error_is_fail_closed_no_partial_write():
    result = derive_topic_coverage(_RaisingSB(), "exam-1")
    assert result["read_error"] is True
    assert result["written"] == 0
    assert result["updated"] == 0


# ── Reviewer-found bug fix: CAS guard on the read-then-write update path ────
# (docs/status/J3-Evidence-Coverage-Scoring-Gate-2026-07-02.md PD-3 / PD-4a)


class _RaceQuery(_Query):
    """Wraps the stub's update-path to simulate a reviewer moving the row
    from draft/rejected to a protected status *between* the derivation's
    initial read and its UPDATE — i.e. the exact TOCTOU window the CAS guard
    must close. The mutation happens lazily, inside `execute()`, so it lands
    after `derive_topic_coverage` has already read `existing` into memory."""

    def __init__(self, name, db, race_row_id, race_to_status):
        super().__init__(name, db)
        self._race_row_id = race_row_id
        self._race_to_status = race_to_status

    def execute(self):
        if self.name == "exam_topic_coverage" and self._pending_update is not None:
            for row in self.db.get(self.name, []):
                if row.get("id") == self._race_row_id:
                    row["reviewer_status"] = self._race_to_status
        return super().execute()


class _RaceSB(SBStub):
    """SBStub variant whose single UPDATE on exam_topic_coverage races a
    reviewer status-change into the row immediately before the UPDATE's
    WHERE clause is evaluated."""

    def __init__(self, db, race_row_id, race_to_status):
        super().__init__(db)
        self._race_row_id = race_row_id
        self._race_to_status = race_to_status

    def table(self, name):
        if name == "exam_topic_coverage":
            return _RaceQuery(name, self.db, self._race_row_id, self._race_to_status)
        return super().table(name)


@pytest.mark.parametrize("race_to_status", ("pending_review", "reviewed", "locked"))
def test_concurrent_reviewer_promotion_wins_cas_race_not_clobbered(race_to_status):
    """A reviewer promotes the row out of draft/rejected in the window
    between the derivation's read and its UPDATE. The CAS-guarded UPDATE
    (id + source_basis + model_version + reviewer_status IN (draft,
    rejected)) must affect zero rows, and the derivation must treat that as
    a conflict — skip + delta, never clobber the promoted row back to
    draft."""
    sb = _RaceSB(
        {
            "exam_topic_score_snapshots": [_snapshot_row(exam_priority_score=99.0)],
            "exam_topic_coverage": [
                {
                    "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None,
                    "exam_phase_id": None, "topic_id": "t1",
                    "source_basis": "evidence_derived", "reviewer_status": "draft",
                    "model_version": DERIVATION_VERSION,
                    "exam_priority_score": 1.0, "is_high_yield": False,
                    "confidence_score": 0.1, "coverage_depth": "light",
                    "metadata": {"evidence": {"fingerprint": "stale-fp"}},
                }
            ],
        },
        race_row_id="row-1",
        race_to_status=race_to_status,
    )
    result = derive_topic_coverage(sb, "exam-1")
    assert result["updated"] == 0
    assert result["skipped"] == 1
    assert len(result["deltas"]) == 1
    row = sb.db["exam_topic_coverage"][0]
    # The row must retain the reviewer's promoted status and NOT be reset
    # to draft or have its scoring fields clobbered with the derivation's
    # proposed values.
    assert row["reviewer_status"] == race_to_status
    assert row["exam_priority_score"] == 1.0


def test_zero_rows_affected_on_update_is_treated_as_conflict_not_success():
    """Even if the in-memory `existing` snapshot still says draft, if the
    UPDATE's own WHERE clause matches zero rows (simulated here by pointing
    the update at a row id that no longer satisfies the CAS predicate), the
    derivation must not count it as `updated` — it must fall back to
    skip+delta."""

    class _ZeroAffectedQuery(_Query):
        def execute(self):
            if self.name == "exam_topic_coverage" and self._pending_update is not None:
                return _Exec([])  # simulate PostgREST returning 0 affected rows
            return super().execute()

    class _ZeroAffectedSB(SBStub):
        def table(self, name):
            if name == "exam_topic_coverage":
                return _ZeroAffectedQuery(name, self.db)
            return super().table(name)

    sb = _ZeroAffectedSB(
        {
            "exam_topic_score_snapshots": [_snapshot_row(exam_priority_score=77.0)],
            "exam_topic_coverage": [
                {
                    "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None,
                    "exam_phase_id": None, "topic_id": "t1",
                    "source_basis": "evidence_derived", "reviewer_status": "draft",
                    "model_version": DERIVATION_VERSION,
                    "exam_priority_score": 1.0, "is_high_yield": False,
                    "confidence_score": 0.1, "coverage_depth": "light",
                    "metadata": {"evidence": {"fingerprint": "stale-fp"}},
                }
            ],
        }
    )
    result = derive_topic_coverage(sb, "exam-1")
    assert result["updated"] == 0
    assert result["errors"] == 0
    assert result["skipped"] == 1
    row = sb.db["exam_topic_coverage"][0]
    assert row["exam_priority_score"] == 1.0  # not clobbered despite 0-row response


# ── Reviewer-found bug fix: ownership requires source_basis AND model_version
# (PD-4a — a row must NOT be treated as derivation-owned just because
# source_basis == 'evidence_derived'; model_version must also be recognized)


@pytest.mark.parametrize(
    "bad_model_version",
    [None, "", "v0.9", "v2.0-future", "not-a-real-version"],
)
def test_evidence_derived_row_with_unowned_model_version_is_never_overwritten(bad_model_version):
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row(exam_priority_score=99.0)],
        "exam_topic_coverage": [
            {
                "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None, "exam_phase_id": None,
                "topic_id": "t1", "source_basis": "evidence_derived", "reviewer_status": "draft",
                "model_version": bad_model_version,
                "exam_priority_score": 1.0, "is_high_yield": False, "confidence_score": 0.1,
                "coverage_depth": "light", "metadata": {},
            }
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["updated"] == 0
    assert result["written"] == 0
    assert result["triaged"] == 1
    assert result["triage"] == [{"topic_id": "t1", "row_id": "row-1"}]
    row = sb.db["exam_topic_coverage"][0]
    # Never overwritten — retains its original (non-owned) values.
    assert row["exam_priority_score"] == 1.0
    assert row["model_version"] == bad_model_version


# ── Checkpost P1-1: fingerprint must use the SNAPSHOT'S OWN input
# fingerprint, not its model_version (docs/status/J3-Evidence-Coverage-
# Scoring-Gate-2026-07-02.md Section C: fingerprint over (snapshot_id,
# snapshot's own input fingerprint, syllabus_mentions, DERIVATION_VERSION)).


def test_same_snapshot_id_and_model_version_different_input_fingerprint_recomputes():
    """model_version does not change on a re-score of the same formula
    version over a DIFFERENT verified-evidence corpus — only the snapshot's
    own input_summary.fingerprint changes. Before the P1-1 fix, the
    derivation fingerprint was built from model_version, so this scenario
    was silently idempotent-skipped instead of recomputed."""
    sb = _sb_with_snapshot(input_summary={"fingerprint": "fp-A"})
    derive_topic_coverage(sb, "exam-1")
    original = dict(sb.db["exam_topic_coverage"][0])
    original_fp = original["metadata"]["evidence"]["fingerprint"]

    # Same snapshot id + same model_version — only the snapshot's OWN input
    # fingerprint and priority changed (simulating a re-score whose
    # underlying verified evidence corpus changed).
    sb.db["exam_topic_score_snapshots"][0]["input_summary"] = {"fingerprint": "fp-B"}
    sb.db["exam_topic_score_snapshots"][0]["exam_priority_score"] = 99.0

    result = derive_topic_coverage(sb, "exam-1")
    assert result["updated"] == 1
    assert result["skipped"] == 0
    updated = sb.db["exam_topic_coverage"][0]
    assert updated["exam_priority_score"] == 99.0
    assert updated["metadata"]["evidence"]["fingerprint"] != original_fp


# ── Checkpost P1-2: insert-vs-insert race (unique-violation superseded) ────


class _UniqueViolation(Exception):
    code = "23505"


class _InsertConflictQuery(_Query):
    """Simulates a concurrent derivation run that already won the INSERT
    race for this scope/topic by the time this run's own insert executes."""

    def execute(self):
        if self.name == "exam_topic_coverage" and self._pending_insert is not None:
            self.db.setdefault(self.name, []).append(
                {
                    "id": "winner-row",
                    "exam_id": "exam-1",
                    "exam_cycle_id": None,
                    "exam_phase_id": None,
                    "topic_id": "t1",
                    "source_basis": "evidence_derived",
                    "model_version": DERIVATION_VERSION,
                    "reviewer_status": "draft",
                    "exam_priority_score": 50.0,
                    "is_high_yield": False,
                    "confidence_score": 0.5,
                    "coverage_depth": "light",
                    "metadata": {"evidence": {"fingerprint": "winner-fp"}},
                }
            )
            raise _UniqueViolation("duplicate key value violates unique constraint")
        return super().execute()


class _InsertConflictSB(SBStub):
    def table(self, name):
        if name == "exam_topic_coverage":
            return _InsertConflictQuery(name, self.db)
        return super().table(name)


def test_insert_unique_violation_superseded_by_concurrent_owned_insert_is_skipped_cleanly():
    sb = _InsertConflictSB({"exam_topic_score_snapshots": [_snapshot_row()]})
    result = derive_topic_coverage(sb, "exam-1")
    assert result["written"] == 0
    assert result["errors"] == 0
    assert result["skipped"] == 1
    assert len(sb.db["exam_topic_coverage"]) == 1
    assert sb.db["exam_topic_coverage"][0]["id"] == "winner-row"


# ── Checkpost P1-2: update-vs-update race from DIFFERENT competing
# snapshots (different fingerprints), not just a reviewer status change ────


class _FingerprintRaceQuery(_Query):
    """A competing derivation run (computed from a DIFFERENT locked
    snapshot, hence a different fingerprint) commits its own UPDATE in the
    window between this run's read and this run's UPDATE."""

    def __init__(self, name, db, race_row_id, new_fp):
        super().__init__(name, db)
        self._race_row_id = race_row_id
        self._new_fp = new_fp

    def execute(self):
        if self.name == "exam_topic_coverage" and self._pending_update is not None:
            for row in self.db.get(self.name, []):
                if row.get("id") == self._race_row_id:
                    row.setdefault("metadata", {}).setdefault("evidence", {})[
                        "fingerprint"
                    ] = self._new_fp
        return super().execute()


class _FingerprintRaceSB(SBStub):
    def __init__(self, db, race_row_id, new_fp):
        super().__init__(db)
        self._race_row_id = race_row_id
        self._new_fp = new_fp

    def table(self, name):
        if name == "exam_topic_coverage":
            return _FingerprintRaceQuery(name, self.db, self._race_row_id, self._new_fp)
        return super().table(name)


def test_concurrent_derivation_from_different_snapshot_does_not_clobber_newer_commit():
    """Two derivation runs race for the SAME topic from DIFFERENT locked
    snapshots (different fingerprints/snapshot ids) — not merely a reviewer
    status change. A coarser CAS predicate (id + source_basis +
    model_version + status) would let both writers' updates through
    identically; the fingerprint predicate must observe that the row's
    fingerprint no longer matches what this run read and refuse to
    overwrite the competing commit."""
    sb = _FingerprintRaceSB(
        {
            "exam_topic_score_snapshots": [_snapshot_row(exam_priority_score=10.0)],
            "exam_topic_coverage": [
                {
                    "id": "row-1",
                    "exam_id": "exam-1",
                    "exam_cycle_id": None,
                    "exam_phase_id": None,
                    "topic_id": "t1",
                    "source_basis": "evidence_derived",
                    "reviewer_status": "draft",
                    "model_version": DERIVATION_VERSION,
                    "exam_priority_score": 1.0,
                    "is_high_yield": False,
                    "confidence_score": 0.1,
                    "coverage_depth": "light",
                    "metadata": {"evidence": {"fingerprint": "stale-fp"}},
                }
            ],
        },
        race_row_id="row-1",
        new_fp="winner-fp",
    )
    result = derive_topic_coverage(sb, "exam-1")
    assert result["updated"] == 0
    assert result["skipped"] == 1
    row = sb.db["exam_topic_coverage"][0]
    # The competing commit's content must survive untouched — this run's
    # stale exam_priority_score=10.0 must NEVER land in the row.
    assert row["exam_priority_score"] == 1.0
    assert row["metadata"]["evidence"]["fingerprint"] == "winner-fp"


# ── Checkpost P1-3: stale derivation-owned rows reconciled when their
# evidence/mentions disappear from the current input set ───────────────────


def _owned_row(**overrides):
    row = {
        "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None, "exam_phase_id": None,
        "topic_id": "t9", "source_basis": "evidence_derived", "reviewer_status": "draft",
        "model_version": DERIVATION_VERSION,
        "exam_priority_score": 0, "is_high_yield": False, "confidence_score": 0,
        "coverage_depth": "mentioned", "metadata": {"evidence": {"fingerprint": "fp-old"}},
    }
    row.update(overrides)
    return row


def test_stale_reconcile_a_verified_mention_revoked_last_evidence_gone():
    """(a) The topic's last verified syllabus mention is revoked and it has
    no locked snapshot — the topic drops out of the current input set
    entirely, so the pre-existing derivation-owned draft must be flagged
    stale rather than left untouched forever."""
    sb = SBStub({"exam_topic_coverage": [_owned_row()]})
    result = derive_topic_coverage(sb, "exam-1")
    assert result["stale_reconciled"] == 1
    assert result["stale_rows"] == [{"topic_id": "t9", "row_id": "row-1"}]
    row = sb.db["exam_topic_coverage"][0]
    assert row["metadata"]["stale"] is True
    assert row["reviewer_status"] == "draft"  # lifecycle untouched
    assert row["coverage_depth"] == "mentioned"  # scoring fields untouched


def test_stale_reconcile_b_last_locked_snapshot_unlocked_or_removed():
    """(b) Same shape but the row is `rejected` (still mutable/owned) and
    the topic previously had PYQ evidence via a locked snapshot that has
    since been unlocked/removed — no snapshot, no mentions, so it too must
    be reconciled."""
    sb = SBStub({
        "exam_topic_coverage": [
            _owned_row(
                topic_id="t1", reviewer_status="rejected",
                exam_priority_score=50.0, is_high_yield=True, confidence_score=0.5,
                coverage_depth="deep",
            )
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["stale_reconciled"] == 1
    row = sb.db["exam_topic_coverage"][0]
    assert row["metadata"]["stale"] is True


@pytest.mark.parametrize("status", ("reviewed", "locked"))
def test_stale_reconcile_c_reviewed_or_locked_evidence_derived_row_not_touched(status):
    """(c) A reviewed/locked evidence_derived row with zero current inputs
    must NEVER be touched by reconciliation — only draft/rejected
    derivation-owned rows are in scope."""
    sb = SBStub({
        "exam_topic_coverage": [
            _owned_row(topic_id="t1", reviewer_status=status, coverage_depth="deep")
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["stale_reconciled"] == 0
    row = sb.db["exam_topic_coverage"][0]
    assert "stale" not in row["metadata"]
    assert row["reviewer_status"] == status


def test_stale_reconcile_d_human_authored_draft_row_not_touched():
    """(d) A human-authored (manual) draft row with zero current inputs is
    NEVER touched by reconciliation — only derivation-owned rows are ever
    reconciled here, matching the main loop's ownership rules."""
    sb = SBStub({
        "exam_topic_coverage": [
            {
                "id": "row-1", "exam_id": "exam-1", "exam_cycle_id": None, "exam_phase_id": None,
                "topic_id": "t1", "source_basis": "manual", "reviewer_status": "draft",
                "exam_priority_score": 50.0, "is_high_yield": True, "confidence_score": 0.5,
                "coverage_depth": "deep", "metadata": {},
            }
        ],
    })
    result = derive_topic_coverage(sb, "exam-1")
    assert result["stale_reconciled"] == 0
    row = sb.db["exam_topic_coverage"][0]
    assert "stale" not in row["metadata"]


def test_stale_reconcile_is_idempotent_across_reruns():
    """A topic already flagged stale=true must not be re-flagged/re-written
    on every subsequent run (avoids redundant writes forever)."""
    sb = SBStub({"exam_topic_coverage": [_owned_row()]})
    r1 = derive_topic_coverage(sb, "exam-1")
    assert r1["stale_reconciled"] == 1
    r2 = derive_topic_coverage(sb, "exam-1")
    assert r2["stale_reconciled"] == 0


def test_stale_reconcile_does_not_flag_topics_still_in_current_input_set():
    """A derivation-owned draft whose topic IS still in the current
    evidence/mentions input set must not be flagged stale — it goes through
    the normal recompute/idempotency path instead."""
    sb = _sb_with_snapshot(topic_id="t1")
    result = derive_topic_coverage(sb, "exam-1")
    assert result["stale_reconciled"] == 0
    assert "stale" not in sb.db["exam_topic_coverage"][0].get("metadata", {})
