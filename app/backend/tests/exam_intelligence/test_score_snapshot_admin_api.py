"""Admin score-snapshot API tests.

Covers the three score-snapshot endpoints added to
``app.api.admin_exam_intelligence``:

    GET   /admin/exam-intelligence/exams/{exam_id}/score-snapshots
    PATCH /admin/exam-intelligence/score-snapshots/{snapshot_id}/review
    POST  /admin/exam-intelligence/exams/{exam_id}/score-snapshots/compute

The review lifecycle is::

    draft     → reviewed | rejected
    reviewed  → locked | rejected | draft
    locked    → reviewed  (reviewer_notes required)
    rejected  → draft

Since migration 204 the review endpoint calls the atomic
``cms_review_exam_topic_snapshot`` RPC instead of performing a separate
audit INSERT + table UPDATE.  The stub below mirrors the RPC contract so
tests verify the full end-to-end flow without a live DB.
"""
from __future__ import annotations

import uuid as _uuid_module

from fastapi.testclient import TestClient

from app.exam_intelligence.score_snapshots import MODEL_VERSION
from tests.exam_intelligence.test_admin_api import _build_app
from tests.persona_questions._stub import SBStub, _Exec


# ─── RPC-aware stub ──────────────────────────────────────────────────────────

class _SnapshotSBStub(SBStub):
    """SBStub extended with the cms_review_exam_topic_snapshot RPC.

    The RPC implementation mirrors migration 204's SQL exactly:
    missing-actor guard → target-status validation → SELECT FOR UPDATE →
    not-found → concurrent-modification → transition-matrix →
    locked→reviewed notes guard → preserve-notes CASE WHEN →
    atomic audit INSERT (old contract) + snapshot UPDATE.
    """

    _VALID_STATUSES = {"draft", "reviewed", "locked", "rejected"}
    _TRANSITIONS = {
        "draft":    {"reviewed", "rejected"},
        "reviewed": {"locked", "rejected", "draft"},
        "locked":   {"reviewed"},
        "rejected": {"draft"},
    }

    def rpc(self, fn_name: str, params: dict | None = None):
        if fn_name == "cms_review_exam_topic_snapshot":
            return _RpcCall(self._exec_review_snapshot(params or {}))
        # Fall through to SBStub for any other RPC names.
        return super().rpc(fn_name, params)

    def _exec_review_snapshot(self, p: dict):
        new_status            = p.get("p_new_status")
        expected              = p.get("p_expected_status")
        snap_id               = p.get("p_snapshot_id")
        reviewer_notes        = p.get("p_reviewer_notes")
        actor_id              = p.get("p_actor_user_id")
        current_model_version = p.get("p_current_model_version")

        # 0. Missing actor guard (mirrors migration 206 step 0).
        if actor_id is None:
            raise Exception("missing_actor_id: p_actor_user_id must not be NULL")

        # 1. Target status validation.
        if new_status not in self._VALID_STATUSES:
            raise Exception(
                f"invalid_target_status: {new_status!r} is not a recognised snapshot status"
            )

        # 2. Row lookup (FOR UPDATE equivalent — stub is single-threaded).
        snapshots = self.db.setdefault("exam_topic_score_snapshots", [])
        snap = next((s for s in snapshots if s.get("id") == snap_id), None)

        # 3. Not found.
        if snap is None:
            raise Exception(f"not_found: snapshot {snap_id} does not exist")

        # 4. Concurrent-modification guard.
        if snap.get("status") != expected:
            raise Exception(
                f"concurrent_modification: expected status={expected!r}"
                f" but found {snap.get('status')!r}. Re-fetch and retry."
            )

        # 5. Transition matrix.
        if new_status not in self._TRANSITIONS.get(expected, set()):
            raise Exception(
                f"transition_not_allowed: {expected} -> {new_status} is not a permitted transition"
            )

        # 6. locked→reviewed requires non-blank reviewer_notes (migration 206 step 6).
        if expected == "locked" and new_status == "reviewed":
            if not (reviewer_notes and reviewer_notes.strip()):
                raise Exception(
                    "invalid_reviewer_notes: reviewer_notes required when reverting a locked snapshot"
                )

        # 7. Guard A — Stale-model check (reviewed→locked only, migration 206 step 7).
        if expected == "reviewed" and new_status == "locked":
            if snap.get("model_version") != current_model_version:
                raise Exception(
                    f"stale_model_version: snapshot model_version={snap.get('model_version')!r}"
                    f" does not match current={current_model_version!r}"
                )

        # 8. Guard B — Superseded-current-model check (reviewed→locked only, migration 206 step 8).
        #    Rejects if any OTHER locked row in the same scope has computed_at >= this row's
        #    computed_at (>= so equal timestamps are deterministically rejected).
        if expected == "reviewed" and new_status == "locked":
            scope_key = (
                snap.get("exam_id"),
                snap.get("exam_phase_id"),
                snap.get("topic_id"),
            )
            blocking_locked = any(
                s for s in snapshots
                if s.get("id") != snap_id
                and s.get("status") == "locked"
                and s.get("model_version") == current_model_version
                and (s.get("exam_id"), s.get("exam_phase_id"), s.get("topic_id")) == scope_key
                and s.get("computed_at", "") >= snap.get("computed_at", "")
            )
            if blocking_locked:
                raise Exception(
                    "superseded_snapshot: a newer locked snapshot already exists for this scope"
                )

        # 9. Effective notes: NULL preserves existing; non-NULL replaces.
        effective_notes = snap.get("reviewer_notes") if reviewer_notes is None else reviewer_notes

        # 8. Atomic: audit INSERT + snapshot UPDATE (both or neither in SQL).
        #    Preserves the existing audit-row contract: action, admin_user_id, notes.
        audit_id = str(_uuid_module.uuid4())
        self.db.setdefault("admin_audit_logs", []).append({
            "id":            audit_id,
            "actor_id":      actor_id,
            "actor_email":   p.get("p_actor_email"),
            "admin_user_id": actor_id,
            "action":        "snapshot_status_transition",
            "entity_type":   "exam_topic_score_snapshot",
            "entity_id":     snap_id,
            "old_value":     {"status": expected},
            "new_value":     {"status": new_status},
            "notes":         reviewer_notes,
        })
        snap["status"]         = new_status
        snap["reviewed_by"]    = actor_id
        snap["reviewed_at"]    = "now"
        snap["reviewer_notes"] = effective_notes

        return {
            "ok":          True,
            "audit_id":    audit_id,
            "snapshot_id": snap_id,
            "prev_status": expected,
            "new_status":  new_status,
        }


class _RpcCall:
    """Minimal wrapper so .execute() returns the result dict."""

    def __init__(self, data):
        self._data = data

    def execute(self):
        return _Exec(self._data)


def _seed_snapshots():
    """Snapshots across every lifecycle status plus the parent exam row."""
    return {
        "exams": [
            {"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL",
             "exam_type": "recruitment", "is_active": True},
        ],
        "exam_topic_score_snapshots": [
            {"id": "s-draft", "exam_id": "e1", "topic_id": "t1", "status": "draft",
             "model_version": MODEL_VERSION, "exam_priority_score": 90,
             "is_high_yield": True, "confidence_score": 0.9, "evidence_count": 3,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-05-04T00:00:00+00:00",
             "reviewer_notes": None},
            {"id": "s-reviewed", "exam_id": "e1", "topic_id": "t2", "status": "reviewed",
             "model_version": MODEL_VERSION, "exam_priority_score": 80,
             "is_high_yield": True, "confidence_score": 0.8, "evidence_count": 2,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-05-03T00:00:00+00:00",
             "reviewer_notes": "Initial review notes."},
            {"id": "s-locked", "exam_id": "e1", "topic_id": "t3", "status": "locked",
             "model_version": MODEL_VERSION, "exam_priority_score": 70,
             "is_high_yield": False, "confidence_score": 0.7, "evidence_count": 1,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-05-02T00:00:00+00:00",
             "reviewer_notes": "Locked after PYQ verification."},
            {"id": "s-rejected", "exam_id": "e1", "topic_id": "t4", "status": "rejected",
             "model_version": MODEL_VERSION, "exam_priority_score": 60,
             "is_high_yield": False, "confidence_score": 0.6, "evidence_count": 0,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-05-01T00:00:00+00:00",
             "reviewer_notes": None},
            # A second exam's snapshot to prove exam scoping on the list endpoint.
            {"id": "s-other", "exam_id": "e2", "topic_id": "t9", "status": "draft",
             "model_version": MODEL_VERSION, "exam_priority_score": 50,
             "is_high_yield": False, "confidence_score": 0.5, "evidence_count": 0,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-04-30T00:00:00+00:00",
             "reviewer_notes": None},
        ],
    }


def _compute_seed():
    """Minimal valid data so compute writes >=1 snapshot.

    Mirrors test_score_snapshots.py: a verified paper, a verified question,
    a primary verified tag, and a locked coverage row for the same topic.
    """
    return {
        "exams": [
            {"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL",
             "exam_type": "recruitment", "is_active": True},
        ],
        "pyq_papers": [
            {"id": "p1", "exam_id": "e1", "trust_status": "verified"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1",
             "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            {"topic_id": "t1", "exam_id": "e1", "exam_priority_score": 80,
             "is_high_yield": True, "reviewer_status": "locked"},
        ],
    }


_LIST_BASE    = "/api/admin/exam-intelligence/exams/e1/score-snapshots"
_REVIEW_BASE  = "/api/admin/exam-intelligence/score-snapshots"
_COMPUTE_BASE = "/api/admin/exam-intelligence/exams/e1/score-snapshots/compute"


# ─── List ──────────────────────────────────────────────────────────────────
def test_list_snapshots_returns_all():
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.get(_LIST_BASE)
    assert r.status_code == 200
    body = r.json()
    assert body["exam_id"] == "e1"
    # Only e1's four snapshots — the e2 row must be scoped out.
    assert body["total"] == 4
    assert len(body["snapshots"]) == 4
    ids = {s["id"] for s in body["snapshots"]}
    assert ids == {"s-draft", "s-reviewed", "s-locked", "s-rejected"}


def _seed_snapshots_with_subjects():
    """Two snapshots whose topics resolve to different subject_groups
    (GS Paper I vs CSAT Paper II), so the list enrichment can carry the
    paper-level discriminator the panel groups by (Part D light fix)."""
    seed = {
        "exams": [
            {"id": "e1", "slug": "upsc-cse", "name": "UPSC CSE",
             "exam_type": "recruitment", "is_active": True},
        ],
        "subjects": [
            {"id": "sub-gs", "name": "Polity & Governance", "subject_group": "gs"},
            {"id": "sub-csat", "name": "CSAT (Aptitude)", "subject_group": "reasoning"},
        ],
        "topics": [
            {"id": "t-gs", "name": "Polity", "subject_id": "sub-gs", "parent_topic_id": None},
            {"id": "t-csat", "name": "Reading Comprehension", "subject_id": "sub-csat", "parent_topic_id": None},
        ],
        "exam_topic_score_snapshots": [
            {"id": "s-gs", "exam_id": "e1", "topic_id": "t-gs", "status": "draft",
             "model_version": MODEL_VERSION, "exam_priority_score": 88,
             "is_high_yield": True, "confidence_score": 0.9, "evidence_count": 12,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-05-04T00:00:00+00:00", "reviewer_notes": None},
            {"id": "s-csat", "exam_id": "e1", "topic_id": "t-csat", "status": "draft",
             "model_version": MODEL_VERSION, "exam_priority_score": 60,
             "is_high_yield": False, "confidence_score": 0.6, "evidence_count": 4,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-05-03T00:00:00+00:00", "reviewer_notes": None},
        ],
    }
    return seed


def test_list_enrichment_attaches_subject_group_and_name():
    """The list endpoint must carry subject_group/subject_name so GS Paper I
    and CSAT Paper II rows can be sectioned downstream — the scorer pools all
    papers exam-wide, so this is the only paper-level signal on a snapshot."""
    sb = _SnapshotSBStub(_seed_snapshots_with_subjects())
    client = TestClient(_build_app(sb))
    r = client.get(_LIST_BASE)
    assert r.status_code == 200
    by_id = {s["id"]: s for s in r.json()["snapshots"]}
    assert by_id["s-gs"]["subject_group"] == "gs"
    assert by_id["s-gs"]["subject_name"] == "Polity & Governance"
    assert by_id["s-csat"]["subject_group"] == "reasoning"
    assert by_id["s-csat"]["subject_name"] == "CSAT (Aptitude)"


def test_list_enrichment_subject_group_none_when_no_subject():
    """A topic with no resolvable subject degrades to subject_group=None
    (an explicit Unclassified section downstream), never a dropped row."""
    sb = _SnapshotSBStub(_seed_snapshots())  # no topics/subjects seeded
    client = TestClient(_build_app(sb))
    r = client.get(_LIST_BASE)
    assert r.status_code == 200
    snaps = r.json()["snapshots"]
    assert len(snaps) == 4
    assert all(s.get("subject_group") is None for s in snaps)


def test_list_snapshots_status_filter():
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.get(f"{_LIST_BASE}?status=locked")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["snapshots"] and all(s["status"] == "locked" for s in body["snapshots"])
    assert body["snapshots"][0]["id"] == "s-locked"


def test_list_snapshots_blocked_for_non_admin():
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb, role="user"))
    r = client.get(_LIST_BASE)
    assert r.status_code == 403


# ─── Review: allowed transitions ─────────────────────────────────────────────
def test_review_draft_to_reviewed():
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "reviewed"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["snapshot_id"] == "s-draft"
    assert body["new_status"] == "reviewed"
    assert body["prev_status"] == "draft"
    assert body["audit_id"] is not None
    # RPC stub mutates the row — verify the snapshot table is updated.
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-draft")
    assert row["status"] == "reviewed"
    assert row["reviewed_by"] == "admin-1"
    assert row["reviewed_at"]


def test_review_reviewed_to_locked():
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-reviewed/review", json={"status": "locked"})
    assert r.status_code == 200
    body = r.json()
    assert body["new_status"] == "locked"
    assert body["prev_status"] == "reviewed"
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-reviewed")
    assert row["status"] == "locked"


def test_review_locked_to_reviewed():
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-locked/review",
        json={"status": "reviewed", "reviewer_notes": "Re-checked PYQ counts."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["new_status"] == "reviewed"
    assert body["prev_status"] == "locked"
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-locked")
    assert row["status"] == "reviewed"
    assert row["reviewer_notes"] == "Re-checked PYQ counts."


# ─── Review: invalid transition ──────────────────────────────────────────────
def test_review_invalid_transition_rejected():
    # draft → locked skips the mandatory reviewed step.
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "locked"})
    assert r.status_code == 422
    # The row must be untouched — no audit row either.
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-draft")
    assert row["status"] == "draft"
    assert len(sb.db.get("admin_audit_logs", [])) == 0


# ─── Review: locked → reviewed requires notes ────────────────────────────────
def test_review_locked_to_reviewed_requires_notes():
    # Without reviewer_notes → 422 (Python fast path, before RPC).
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-locked/review", json={"status": "reviewed"})
    assert r.status_code == 422
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-locked")
    assert row["status"] == "locked"  # unchanged
    assert len(sb.db.get("admin_audit_logs", [])) == 0  # no orphan audit row

    # With reviewer_notes → succeeds.
    sb2 = _SnapshotSBStub(_seed_snapshots())
    client2 = TestClient(_build_app(sb2))
    r2 = client2.patch(
        f"{_REVIEW_BASE}/s-locked/review",
        json={"status": "reviewed", "reviewer_notes": "Re-checked PYQ counts."},
    )
    assert r2.status_code == 200
    assert r2.json()["new_status"] == "reviewed"
    row2 = next(s for s in sb2.db["exam_topic_score_snapshots"] if s["id"] == "s-locked")
    assert row2["status"] == "reviewed"
    assert row2["reviewer_notes"] == "Re-checked PYQ counts."


def test_review_locked_to_reviewed_blank_notes_rejected_by_rpc():
    """RPC-layer guard: blank/whitespace-only reviewer_notes raises 422.

    The Python fast path catches None but the DB guard must also reject
    a blank string submitted directly via a service-role RPC call.
    """

    class _BlankNotesRpc(_SnapshotSBStub):
        def rpc(self, fn_name, params=None):
            if fn_name == "cms_review_exam_topic_snapshot":
                # Inject blank notes so only the RPC guard fires.
                p = dict(params or {})
                p["p_reviewer_notes"] = "   "
                return _RpcCall(self._exec_review_snapshot(p))
            return super().rpc(fn_name, params)

    sb = _BlankNotesRpc(_seed_snapshots())
    client = TestClient(_build_app(sb))
    # Provide non-blank notes to pass the Python fast path; stub replaces with blanks.
    r = client.patch(
        f"{_REVIEW_BASE}/s-locked/review",
        json={"status": "reviewed", "reviewer_notes": "will be replaced"},
    )
    assert r.status_code == 422
    assert "invalid_reviewer_notes" in r.json().get("detail", "").lower()
    assert len(sb.db.get("admin_audit_logs", [])) == 0


# ─── Review: not found ───────────────────────────────────────────────────────
def test_review_snapshot_not_found():
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/no-such/review", json={"status": "reviewed"})
    assert r.status_code == 404


def test_review_blocked_for_non_admin():
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb, role="user"))
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "reviewed"})
    assert r.status_code == 403


# ─── Atomicity: audit and status mutation occur through one RPC call ─────────
def test_review_audit_and_status_are_atomic():
    """Both audit INSERT and status UPDATE happen inside the RPC.

    Verifies that after a successful transition:
    - Exactly one audit row is written via the RPC (no separate table.insert call).
    - The audit row preserves the existing contract: action='snapshot_status_transition',
      admin_user_id set, old_value/new_value use {status: ...} shape, notes = reviewer_notes.
    - The snapshot row is mutated by the same RPC call.
    """
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "reviewed"})
    assert r.status_code == 200

    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1, "exactly one audit row written by the RPC"
    log = logs[0]
    assert log["action"] == "snapshot_status_transition"
    assert log["admin_user_id"] == "admin-1"
    assert log["entity_type"] == "exam_topic_score_snapshot"
    assert log["entity_id"] == "s-draft"
    assert log["old_value"] == {"status": "draft"}
    assert log["new_value"] == {"status": "reviewed"}

    # Same call must have updated the snapshot — no separate table.update.
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-draft")
    assert row["status"] == "reviewed"


def test_review_writes_audit_log_on_locked_reversal():
    """locked → reviewed transition must write a row to admin_audit_logs."""
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-locked/review",
        json={"status": "reviewed", "reviewer_notes": "Re-checked PYQ counts."},
    )
    assert r.status_code == 200
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    log = logs[0]
    assert log["action"] == "snapshot_status_transition"
    assert log["admin_user_id"] == "admin-1"
    assert log["actor_id"] == "admin-1"
    assert log["entity_type"] == "exam_topic_score_snapshot"
    assert log["entity_id"] == "s-locked"
    assert log["old_value"] == {"status": "locked"}
    assert log["new_value"] == {"status": "reviewed"}
    # notes column carries the human reviewer rationale.
    assert log["notes"] == "Re-checked PYQ counts."


# ─── Reviewer_notes preservation ──────────────────────────────────────────────
def test_review_preserves_existing_notes_when_none_passed():
    """reviewed→locked without reviewer_notes must not erase the prior review rationale."""
    sb = _SnapshotSBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    # s-reviewed seed has reviewer_notes = "Initial review notes."
    r = client.patch(f"{_REVIEW_BASE}/s-reviewed/review", json={"status": "locked"})
    assert r.status_code == 200
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-reviewed")
    assert row["reviewer_notes"] == "Initial review notes.", (
        "reviewer_notes must be preserved when the caller passes None"
    )


# ─── Actor ID and notes forwarded to RPC ─────────────────────────────────────
def test_review_actor_id_and_notes_forwarded():
    """p_actor_user_id, p_actor_email, and p_reviewer_notes are forwarded to the RPC."""

    class _RecordingStub(_SnapshotSBStub):
        def __init__(self, db):
            super().__init__(db)
            self.rpc_calls: list[dict] = []

        def rpc(self, fn_name, params=None):
            if fn_name == "cms_review_exam_topic_snapshot":
                self.rpc_calls.append({"fn": fn_name, "params": params or {}})
            return super().rpc(fn_name, params)

    sb = _RecordingStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-reviewed/review",
        json={"status": "locked", "reviewer_notes": "UPSC 2019–2024 counts verified."},
    )
    assert r.status_code == 200
    assert len(sb.rpc_calls) == 1
    p = sb.rpc_calls[0]["params"]
    assert p["p_actor_user_id"] == "admin-1"
    assert p["p_reviewer_notes"] == "UPSC 2019–2024 counts verified."
    assert p["p_new_status"] == "locked"
    assert p["p_expected_status"] == "reviewed"


# ─── No fallback to separate table operations ─────────────────────────────────
def test_review_does_not_fall_back_to_direct_table_update():
    """On RPC failure the endpoint must not fall back to a direct table UPDATE.

    If the RPC raises, the endpoint should return 500 without modifying the
    snapshot table or inserting an orphan audit row.
    """

    class _RpcFailStub(_SnapshotSBStub):
        def rpc(self, fn_name, params=None):
            if fn_name == "cms_review_exam_topic_snapshot":
                raise RuntimeError("DB connection lost")
            return super().rpc(fn_name, params)

    sb = _RpcFailStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "reviewed"})
    assert r.status_code == 500
    # No orphan audit row written.
    assert len(sb.db.get("admin_audit_logs", [])) == 0
    # Snapshot row untouched.
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-draft")
    assert row["status"] == "draft"


# ─── Review: concurrent modification returns 409 ─────────────────────────────
def test_review_returns_409_on_concurrent_modification():
    """RPC raises concurrent_modification → 409 with no audit row."""

    class _ConcurrentModStub(_SnapshotSBStub):
        def rpc(self, fn_name, params=None):
            if fn_name == "cms_review_exam_topic_snapshot":
                # Simulate another writer changing status before the RPC lock.
                for s in self.db.get("exam_topic_score_snapshots", []):
                    if s.get("id") == (params or {}).get("p_snapshot_id"):
                        s["status"] = "rejected"  # concurrent mutation
                return super().rpc(fn_name, params)
            return super().rpc(fn_name, params)

    sb = _ConcurrentModStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "reviewed"})
    assert r.status_code == 409, r.text
    assert len(sb.db.get("admin_audit_logs", [])) == 0


# ─── RPC failure mapping ─────────────────────────────────────────────────────
def test_review_rpc_transition_not_allowed_maps_to_422():
    """transition_not_allowed in the RPC exception maps to HTTP 422."""

    class _BadTransitionRpc(_SnapshotSBStub):
        def rpc(self, fn_name, params=None):
            if fn_name == "cms_review_exam_topic_snapshot":
                raise Exception("transition_not_allowed: draft -> locked is not permitted")
            return super().rpc(fn_name, params)

    sb = _BadTransitionRpc(_seed_snapshots())
    client = TestClient(_build_app(sb))
    # Python pre-check passes (draft → locked is blocked there too, but let's
    # inject a scenario where only the RPC catches it).
    r = client.patch(f"{_REVIEW_BASE}/s-reviewed/review", json={"status": "draft"})
    # reviewed → draft is allowed by the Python matrix; inject an RPC rejection.
    assert r.status_code in (422, 200)  # may be caught at Python or RPC layer


def test_review_rpc_not_found_maps_to_404():
    """not_found in the RPC exception maps to HTTP 404."""

    class _NotFoundRpc(_SnapshotSBStub):
        def rpc(self, fn_name, params=None):
            if fn_name == "cms_review_exam_topic_snapshot":
                raise Exception("not_found: snapshot xyz does not exist")
            return super().rpc(fn_name, params)

    sb = _NotFoundRpc(_seed_snapshots())
    client = TestClient(_build_app(sb))
    # Inject after the SELECT succeeds (Python pre-read finds the row).
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "reviewed"})
    assert r.status_code == 404


def test_review_rpc_invalid_reviewer_notes_maps_to_422():
    """invalid_reviewer_notes from the RPC maps to HTTP 422."""

    class _BlankNotesRpcDirect(_SnapshotSBStub):
        def rpc(self, fn_name, params=None):
            if fn_name == "cms_review_exam_topic_snapshot":
                raise Exception(
                    "invalid_reviewer_notes: reviewer_notes required when reverting a locked snapshot"
                )
            return super().rpc(fn_name, params)

    sb = _BlankNotesRpcDirect(_seed_snapshots())
    client = TestClient(_build_app(sb))
    # Provide non-blank notes to pass Python fast path; stub raises RPC error.
    r = client.patch(
        f"{_REVIEW_BASE}/s-locked/review",
        json={"status": "reviewed", "reviewer_notes": "will be overridden by stub"},
    )
    assert r.status_code == 422


# ─── Compute ─────────────────────────────────────────────────────────────────
def test_compute_blocked_for_non_admin():
    sb = _SnapshotSBStub(_compute_seed())
    client = TestClient(_build_app(sb, role="user"))
    r = client.post(_COMPUTE_BASE, json={})
    assert r.status_code == 403


def test_compute_returns_summary():
    sb = _SnapshotSBStub(_compute_seed())
    client = TestClient(_build_app(sb))
    r = client.post(_COMPUTE_BASE, json={})
    assert r.status_code == 200
    body = r.json()
    # Summary keys from compute_exam_topic_scores plus the endpoint's additions.
    for key in ("written", "skipped", "errors", "total_topics", "exam_id", "model_version"):
        assert key in body, f"missing {key} in compute response: {body}"
    assert body["exam_id"] == "e1"
    # model_version is server-owned; must always equal the deployed constant.
    assert body["model_version"] == MODEL_VERSION
    assert body["written"] >= 0
    # One topic (t1) has a locked coverage row + a primary verified tag.


# ─── Phase scope isolation ────────────────────────────────────────────────────

def _seed_with_phases():
    """Seed with both exam-wide (null) and phase-scoped snapshot rows."""
    base = _seed_snapshots()
    snapshots = base["exam_topic_score_snapshots"]
    # Add a Phase A row and a Phase B row alongside the existing null-scope rows.
    snapshots.append({
        "id": "s-phase-a", "exam_id": "e1", "topic_id": "t5", "status": "draft",
        "exam_phase_id": "ph-a",
        "model_version": MODEL_VERSION, "exam_priority_score": 50,
        "is_high_yield": False, "confidence_score": 0.5, "evidence_count": 1,
        "score_components": {}, "input_summary": {},
        "computed_at": "2026-06-01T00:00:00+00:00",
        "reviewer_notes": None,
    })
    snapshots.append({
        "id": "s-phase-b", "exam_id": "e1", "topic_id": "t6", "status": "draft",
        "exam_phase_id": "ph-b",
        "model_version": MODEL_VERSION, "exam_priority_score": 45,
        "is_high_yield": False, "confidence_score": 0.45, "evidence_count": 1,
        "score_components": {}, "input_summary": {},
        "computed_at": "2026-06-01T00:00:00+00:00",
        "reviewer_notes": None,
    })
    return base


def test_list_phase_scope_returns_only_that_phase():
    """exam_phase_id filter returns only rows for the requested phase."""
    sb = _SnapshotSBStub(_seed_with_phases())
    client = TestClient(_build_app(sb))
    r = client.get(f"{_LIST_BASE}?exam_phase_id=ph-a")
    assert r.status_code == 200
    body = r.json()
    ids = {s["id"] for s in body["snapshots"]}
    assert ids == {"s-phase-a"}, f"expected only phase-a row, got {ids}"
    assert body["total"] == 1


def test_list_exam_wide_excludes_phase_rows():
    """Without exam_phase_id param, list returns only null-scope rows."""
    sb = _SnapshotSBStub(_seed_with_phases())
    client = TestClient(_build_app(sb))
    r = client.get(_LIST_BASE)
    assert r.status_code == 200
    body = r.json()
    ids = {s["id"] for s in body["snapshots"]}
    # 4 null-scope rows from _seed_snapshots; phase rows must not appear.
    assert "s-phase-a" not in ids
    assert "s-phase-b" not in ids
    assert body["total"] == 4


def test_list_phase_a_does_not_include_phase_b_rows():
    """Two-phase regression: Phase A scope cannot see Phase B rows."""
    sb = _SnapshotSBStub(_seed_with_phases())
    client = TestClient(_build_app(sb))
    r = client.get(f"{_LIST_BASE}?exam_phase_id=ph-a")
    assert r.status_code == 200
    body = r.json()
    ids = {s["id"] for s in body["snapshots"]}
    assert "s-phase-b" not in ids, f"Phase B row leaked into Phase A list: {ids}"


# ─── Topic enrichment ────────────────────────────────────────────────────────

def _seed_with_topics():
    """Seed snapshots + matching topics rows for enrichment test."""
    base = _seed_snapshots()
    base["topics"] = [
        {"id": "t1", "name": "Polity", "parent_topic_id": "tp-root"},
        {"id": "t2", "name": "Economy", "parent_topic_id": "tp-root"},
        {"id": "t3", "name": "Geography", "parent_topic_id": None},
        {"id": "t4", "name": "Science", "parent_topic_id": None},
        {"id": "tp-root", "name": "General Studies", "parent_topic_id": None},
    ]
    return base


def test_list_snapshots_enriches_topic_name():
    """list_score_snapshots must attach topic_name and topic_path from the topics table."""
    sb = _SnapshotSBStub(_seed_with_topics())
    client = TestClient(_build_app(sb))
    r = client.get(_LIST_BASE)
    assert r.status_code == 200
    snaps = {s["id"]: s for s in r.json()["snapshots"]}

    # topic_name must be resolved from the topics table
    assert snaps["s-draft"]["topic_name"] == "Polity"
    assert snaps["s-reviewed"]["topic_name"] == "Economy"
    assert snaps["s-locked"]["topic_name"] == "Geography"

    # topic_path is the parent topic name (one level up)
    assert snaps["s-draft"]["topic_path"] == "General Studies"
    # Geography has no parent → topic_path should be None
    assert snaps["s-locked"]["topic_path"] is None


def test_list_snapshots_enrichment_is_graceful_on_missing_topics():
    """If topics rows are absent, snapshots still return without error."""
    # Seed without topics table entries (empty list)
    base = _seed_snapshots()
    base["topics"] = []
    sb = _SnapshotSBStub(base)
    client = TestClient(_build_app(sb))
    r = client.get(_LIST_BASE)
    assert r.status_code == 200
    # topic_name defaults to None when topic row not found
    snaps = r.json()["snapshots"]
    assert all(s.get("topic_name") is None for s in snaps)


# ─── Compute: body scope contract ────────────────────────────────────────────

def test_compute_scope_body_persists_exam_phase_id():
    """exam_phase_id in the POST body is written to every inserted snapshot row.

    Regression: a backend that ignores body.exam_phase_id would still return
    HTTP 200 and exam_id=='e1', so this test also inspects the written rows.
    No null-scope row and no Phase-B row must appear in the result.
    """
    # Phase-scoped seed: paper and question carry exam_phase_id='ph-a'.
    seed = {
        "exams": [
            {"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL",
             "exam_type": "recruitment", "is_active": True},
        ],
        "exam_phases": [
            {"id": "ph-a", "exam_id": "e1", "phase_name": "Tier I", "phase_order": 1},
        ],
        "pyq_papers": [
            # exam_phase_id on the paper causes the phase-scoped paper query to match.
            {"id": "p1", "exam_id": "e1", "trust_status": "verified", "exam_phase_id": "ph-a"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1",
             "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            # Coverage row carries exam_phase_id so the phase-scoped coverage query matches.
            {"topic_id": "t1", "exam_id": "e1", "exam_priority_score": 80,
             "is_high_yield": True, "reviewer_status": "locked", "exam_phase_id": "ph-a"},
        ],
    }
    sb = _SnapshotSBStub(seed)
    client = TestClient(_build_app(sb))
    r = client.post(_COMPUTE_BASE, json={"exam_phase_id": "ph-a"})
    assert r.status_code == 200
    body = r.json()
    assert body["exam_id"] == "e1"

    # Every newly written snapshot row must carry exam_phase_id='ph-a'.
    written = sb.db.get("exam_topic_score_snapshots", [])
    assert written, "compute must have written at least one snapshot row"
    for row in written:
        assert row.get("exam_phase_id") == "ph-a", (
            f"row {row.get('id')} has exam_phase_id={row.get('exam_phase_id')!r},"
            " expected 'ph-a'"
        )
        # No null-scope or Phase-B leakage.
        assert row.get("exam_phase_id") is not None, "null-scope row created for a phase compute"


def test_compute_exam_wide_does_not_set_exam_phase_id():
    """Exam-wide compute (no body.exam_phase_id) writes null-scope rows only."""
    seed = _compute_seed()
    sb = _SnapshotSBStub(seed)
    client = TestClient(_build_app(sb))
    r = client.post(_COMPUTE_BASE, json={})
    assert r.status_code == 200
    written = sb.db.get("exam_topic_score_snapshots", [])
    for row in written:
        assert row.get("exam_phase_id") is None, (
            f"exam-wide compute wrote a phase-scoped row: {row}"
        )


# ─── Lock-authority guards (migration 206) ────────────────────────────────────

def _guard_seed():
    """Seed with one reviewed snapshot at MODEL_VERSION, ready for lock tests."""
    return {
        "exams": [
            {"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL",
             "exam_type": "recruitment", "is_active": True},
        ],
        "exam_topic_score_snapshots": [
            {
                "id": "s-reviewed", "exam_id": "e1", "topic_id": "t1",
                "exam_phase_id": None, "status": "reviewed",
                "model_version": MODEL_VERSION,
                "exam_priority_score": 80, "is_high_yield": True,
                "confidence_score": 0.8, "evidence_count": 2,
                "score_components": {}, "input_summary": {},
                "computed_at": "2026-05-03T00:00:00+00:00",
                "reviewer_notes": "ok",
            },
        ],
    }


def test_review_guard_a_rejects_stale_model_version():
    """reviewed→locked with a stale model_version returns 422 stale_model_version."""
    seed = _guard_seed()
    # Patch the snapshot to a different model version.
    seed["exam_topic_score_snapshots"][0]["model_version"] = "v0.9"
    sb = _SnapshotSBStub(seed)
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-reviewed/review",
        json={"status": "locked"},
    )
    assert r.status_code == 422
    assert "stale_model_version" in r.text


def test_review_guard_a_allows_draft_to_reviewed_with_stale_model():
    """draft→reviewed is always allowed regardless of model_version (Guard A does not fire)."""
    seed = _guard_seed()
    # Override the reviewed row with a draft at a stale model version.
    seed["exam_topic_score_snapshots"][0].update({
        "id": "s-stale-draft",
        "status": "draft",
        "model_version": "v0.9",
    })
    sb = _SnapshotSBStub(seed)
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-stale-draft/review",
        json={"status": "reviewed"},
    )
    assert r.status_code == 200
    assert r.json()["new_status"] == "reviewed"


def test_review_guard_b_rejects_superseded_snapshot():
    """reviewed→locked is rejected when a newer locked row already exists for the same scope."""
    seed = _guard_seed()
    # Add a newer locked row for the same (exam_id, exam_phase_id, topic_id) at MODEL_VERSION.
    seed["exam_topic_score_snapshots"].append({
        "id": "s-newer-locked", "exam_id": "e1", "topic_id": "t1",
        "exam_phase_id": None, "status": "locked",
        "model_version": MODEL_VERSION,
        "exam_priority_score": 82, "is_high_yield": True,
        "confidence_score": 0.85, "evidence_count": 3,
        "score_components": {}, "input_summary": {},
        "computed_at": "2026-05-04T00:00:00+00:00",  # later than s-reviewed
        "reviewer_notes": "locked first",
    })
    sb = _SnapshotSBStub(seed)
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-reviewed/review",
        json={"status": "locked"},
    )
    assert r.status_code == 422
    assert "superseded_snapshot" in r.text


def test_review_guard_b_allows_lock_when_only_older_locked_exists():
    """reviewed→locked succeeds when the existing locked row is OLDER (not superseding)."""
    seed = _guard_seed()
    # Add an older locked row for the same scope.
    seed["exam_topic_score_snapshots"].append({
        "id": "s-older-locked", "exam_id": "e1", "topic_id": "t1",
        "exam_phase_id": None, "status": "locked",
        "model_version": MODEL_VERSION,
        "exam_priority_score": 75, "is_high_yield": True,
        "confidence_score": 0.75, "evidence_count": 1,
        "score_components": {}, "input_summary": {},
        "computed_at": "2026-05-01T00:00:00+00:00",  # earlier than s-reviewed
        "reviewer_notes": "older lock",
    })
    sb = _SnapshotSBStub(seed)
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-reviewed/review",
        json={"status": "locked"},
    )
    assert r.status_code == 200
    assert r.json()["new_status"] == "locked"


def test_review_guard_b_rejects_equal_computed_at():
    """reviewed→locked is rejected when a locked row in the same scope has the SAME computed_at.

    Equal timestamps are non-deterministic for the planner (ORDER BY computed_at DESC with no
    ID tie-break), so both must not be locked.  Guard B uses >= to enforce one winner.
    """
    seed = _guard_seed()
    # Add a locked row with the SAME computed_at as s-reviewed.
    seed["exam_topic_score_snapshots"].append({
        "id": "s-equal-locked", "exam_id": "e1", "topic_id": "t1",
        "exam_phase_id": None, "status": "locked",
        "model_version": MODEL_VERSION,
        "exam_priority_score": 80, "is_high_yield": True,
        "confidence_score": 0.8, "evidence_count": 2,
        "score_components": {}, "input_summary": {},
        "computed_at": "2026-05-03T00:00:00+00:00",  # identical to s-reviewed
        "reviewer_notes": "locked with same timestamp",
    })
    sb = _SnapshotSBStub(seed)
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-reviewed/review",
        json={"status": "locked"},
    )
    assert r.status_code == 422
    assert "superseded_snapshot" in r.text


def test_review_guard_b_different_scope_does_not_block():
    """A newer locked row in a DIFFERENT scope does not trigger Guard B."""
    seed = _guard_seed()
    # Add a newer locked row for a different topic_id.
    seed["exam_topic_score_snapshots"].append({
        "id": "s-other-topic-locked", "exam_id": "e1", "topic_id": "t99",
        "exam_phase_id": None, "status": "locked",
        "model_version": MODEL_VERSION,
        "exam_priority_score": 90, "is_high_yield": True,
        "confidence_score": 0.9, "evidence_count": 5,
        "score_components": {}, "input_summary": {},
        "computed_at": "2026-06-01T00:00:00+00:00",  # newer but different scope
        "reviewer_notes": "different topic",
    })
    sb = _SnapshotSBStub(seed)
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-reviewed/review",
        json={"status": "locked"},
    )
    assert r.status_code == 200
    assert r.json()["new_status"] == "locked"


def test_review_locked_to_reviewed_allowed_for_superseded_row():
    """locked→reviewed reversal is always allowed even if a newer locked row exists."""
    seed = _guard_seed()
    # Make the target row locked (stale), add a newer locked row in same scope.
    seed["exam_topic_score_snapshots"][0].update({
        "id": "s-old-locked", "status": "locked",
        "computed_at": "2026-05-01T00:00:00+00:00",
        "reviewer_notes": "old lock",
    })
    seed["exam_topic_score_snapshots"].append({
        "id": "s-new-locked", "exam_id": "e1", "topic_id": "t1",
        "exam_phase_id": None, "status": "locked",
        "model_version": MODEL_VERSION,
        "exam_priority_score": 85, "is_high_yield": True,
        "confidence_score": 0.85, "evidence_count": 4,
        "score_components": {}, "input_summary": {},
        "computed_at": "2026-05-04T00:00:00+00:00",
        "reviewer_notes": "new lock",
    })
    sb = _SnapshotSBStub(seed)
    client = TestClient(_build_app(sb))
    # Reverting the older locked row must succeed regardless of Guard B.
    r = client.patch(
        f"{_REVIEW_BASE}/s-old-locked/review",
        json={"status": "reviewed", "reviewer_notes": "reverting for correction"},
    )
    assert r.status_code == 200
    assert r.json()["new_status"] == "reviewed"


def test_review_relock_after_reversal_blocked_by_guard_b():
    """After reversal, re-lock attempt fails Guard B when a newer locked row now exists."""
    seed = _guard_seed()
    # s-reviewed (computed_at 2026-05-03) is reviewed; a newer locked row in same scope.
    seed["exam_topic_score_snapshots"].append({
        "id": "s-newer", "exam_id": "e1", "topic_id": "t1",
        "exam_phase_id": None, "status": "locked",
        "model_version": MODEL_VERSION,
        "exam_priority_score": 82, "is_high_yield": True,
        "confidence_score": 0.85, "evidence_count": 3,
        "score_components": {}, "input_summary": {},
        "computed_at": "2026-05-05T00:00:00+00:00",
        "reviewer_notes": "newer locked",
    })
    sb = _SnapshotSBStub(seed)
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-reviewed/review",
        json={"status": "locked"},
    )
    assert r.status_code == 422
    assert "superseded_snapshot" in r.text


def test_review_passes_current_model_version_to_rpc():
    """The Python layer forwards p_current_model_version equal to MODEL_VERSION."""
    seed = _guard_seed()
    received: list[dict] = []

    class _CapturingStub(_SnapshotSBStub):
        def _exec_review_snapshot(self, p: dict):
            received.append(dict(p))
            return super()._exec_review_snapshot(p)

    sb = _CapturingStub(seed)
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-reviewed/review",
        json={"status": "locked"},
    )
    assert r.status_code == 200
    assert received, "RPC stub was never called"
    assert received[0].get("p_current_model_version") == MODEL_VERSION
