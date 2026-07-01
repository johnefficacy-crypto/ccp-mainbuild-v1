"""Backend tests for J2-A Manage Exam operational editors.

Covers the `exam_intelligence.manage`-gated topic + alias editors under
`/api/admin/exam-intelligence-manage`, per the J2 gate
(docs/status/Manage-Exam-Operational-Editors-Gate-2026-07-01.md §D/§F):

- subject resolution via the exam_topic_coverage path (OD-4); empty
  coverage → empty list, never the global subject set (OD-5);
- every mutation gated on the single `exam_intelligence.manage` token;
  non-manage admins are denied, super_admin bypasses;
- endpoints enforce subject∈exam and topic∈subject integrity (OD-15);
- rule 4: identity edits on a topic with locked coverage → 409;
- rule 5: deleting a topic with dependencies → 409;
- writes create audit rows (notes=admin_exam_intel_manage).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_manage as mng
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub, _Exec, _Query

_BASE = "/api/admin/exam-intelligence-manage"
MANAGE = mng.PERM_MANAGE


class _MngQuery(_Query):
    """Adds ilike / range / count='exact' on the read path (like _TaxQuery)."""

    def __init__(self, name, db):
        super().__init__(name, db)
        self._count_exact = False
        self._range = None

    def select(self, *args, **kwargs):
        if kwargs.get("count") == "exact":
            self._count_exact = True
        return self

    def ilike(self, key, pattern):
        self.filters.append((key, "ilike", str(pattern).strip("%").lower()))
        return self

    def range(self, lo, hi):
        self._range = (lo, hi)
        return self

    def execute(self):
        if (
            self._pending_insert is not None
            or self._pending_update is not None
            or self._pending_upsert is not None
        ):
            return super().execute()
        ilikes = [(k, v) for (k, op, v) in self.filters if op == "ilike"]
        self.filters = [f for f in self.filters if f[1] != "ilike"]
        res = super().execute()
        data = list(res.data)
        for k, needle in ilikes:
            data = [r for r in data if isinstance(r.get(k), str) and needle in r[k].lower()]
        out = _Exec(data)
        if self._count_exact:
            out.count = len(data)
        if self._range:
            lo, hi = self._range
            out.data = data[lo : hi + 1]
        return out


class MngSBStub(SBStub):
    def table(self, name: str):
        return _MngQuery(name, self.db)


def _client(sb: MngSBStub, *, permissions=None, role="admin") -> TestClient:
    app = FastAPI()
    app.include_router(mng.router, prefix="/api")
    mng.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[mng._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1",
        "email": "op@example.com",
        "role": role,
        "permissions": permissions if permissions is not None else [MANAGE],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed() -> dict:
    """Exam E1 covers subject s1 (via coverage on t1); s2 is NOT covered."""
    return {
        "exams": [{"id": "E1", "name": "SSC CGL"}],
        "subjects": [
            {"id": "s1", "slug": "quant", "name": "Quantitative Aptitude", "is_active": True},
            {"id": "s2", "slug": "gk", "name": "General Knowledge", "is_active": True},
        ],
        "topics": [
            {"id": "t1", "subject_id": "s1", "parent_topic_id": None, "slug": "percentages",
             "name": "Percentages", "level": "topic", "is_active": True},
            {"id": "t2", "subject_id": "s1", "parent_topic_id": None, "slug": "ratios",
             "name": "Ratios", "level": "topic", "is_active": True},
            {"id": "t9", "subject_id": "s2", "parent_topic_id": None, "slug": "history",
             "name": "History", "level": "topic", "is_active": True},
        ],
        "exam_topic_coverage": [
            {"id": "c1", "exam_id": "E1", "topic_id": "t1", "reviewer_status": "reviewed"},
        ],
        "topic_aliases": [],
        "topic_prerequisites": [],
        "pyq_question_topic_tags": [],
        "syllabus_topic_mentions": [],
        "topic_relation_edges": [],
        "admin_audit_logs": [],
    }


# ── subject resolution (OD-4 / OD-5) ─────────────────────────────────────


def test_exam_subjects_resolved_via_coverage_path():
    sb = MngSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/exams/E1/subjects")
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    ids = {s["id"] for s in items}
    assert ids == {"s1"}  # s2 is not covered by E1


def test_exam_subjects_empty_when_no_coverage():
    seed = _seed()
    seed["exam_topic_coverage"] = []
    sb = MngSBStub(seed)
    r = _client(sb).get(f"{_BASE}/exams/E1/subjects")
    assert r.status_code == 200, r.text
    assert r.json() == {"items": [], "total": 0}


def test_exam_subjects_404_for_unknown_exam():
    sb = MngSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/exams/NOPE/subjects")
    assert r.status_code == 404


# ── permission gating (rule 1) ───────────────────────────────────────────


def test_topics_list_denied_without_manage():
    sb = MngSBStub(_seed())
    r = _client(sb, permissions=["exam_intelligence.review"]).get(
        f"{_BASE}/topics?exam_id=E1&subject_id=s1"
    )
    assert r.status_code == 403


def test_topics_list_allowed_for_super_admin_without_token():
    sb = MngSBStub(_seed())
    r = _client(sb, permissions=[], role="super_admin").get(
        f"{_BASE}/topics?exam_id=E1&subject_id=s1"
    )
    assert r.status_code == 200, r.text


# ── scope integrity (OD-15) ──────────────────────────────────────────────


def test_topics_list_rejects_subject_not_in_exam():
    sb = MngSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/topics?exam_id=E1&subject_id=s2")
    assert r.status_code == 422
    assert "coverage" in str(r.json()["detail"]).lower()


def test_topics_list_scoped_to_subject():
    sb = MngSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/topics?exam_id=E1&subject_id=s1")
    assert r.status_code == 200, r.text
    names = {t["name"] for t in r.json()["items"]}
    assert names == {"Percentages", "Ratios"}


def test_topics_search_filters_by_name():
    sb = MngSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/topics?exam_id=E1&subject_id=s1&q=perc")
    assert r.status_code == 200, r.text
    assert [t["name"] for t in r.json()["items"]] == ["Percentages"]


# ── topic create / update ────────────────────────────────────────────────


def test_create_topic_writes_row_and_audit():
    sb = MngSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/topics?exam_id=E1",
        json={"reason": "add operational topic", "payload": {
            "subject_id": "s1", "slug": "profit-loss", "name": "Profit and Loss", "level": "topic"}},
    )
    assert r.status_code == 200, r.text
    assert any(t["slug"] == "profit-loss" for t in sb.db["topics"])
    audit = sb.db["admin_audit_logs"]
    assert audit and audit[-1]["action"] == "exam_intel.manage.topic.create"
    assert audit[-1]["notes"] == "admin_exam_intel_manage"


def test_create_topic_rejects_duplicate_top_level_slug():
    """No import/upsert semantics: a duplicate (subject, NULL, slug) → 409."""
    sb = MngSBStub(_seed())  # t1 is (s1, NULL, percentages)
    r = _client(sb).post(
        f"{_BASE}/topics?exam_id=E1",
        json={"reason": "attempt duplicate top-level", "payload": {
            "subject_id": "s1", "slug": "percentages", "name": "Percentages 2", "level": "topic"}},
    )
    assert r.status_code == 409
    # The existing row must be untouched (not overwritten).
    assert next(t for t in sb.db["topics"] if t["id"] == "t1")["name"] == "Percentages"


def test_create_topic_rejects_duplicate_child_slug():
    seed = _seed()
    seed["topics"].append({"id": "tc", "subject_id": "s1", "parent_topic_id": "t1",
                           "slug": "basic", "name": "Basic", "level": "microtopic", "is_active": True})
    sb = MngSBStub(seed)
    r = _client(sb).post(
        f"{_BASE}/topics?exam_id=E1",
        json={"reason": "attempt duplicate child topic", "payload": {
            "subject_id": "s1", "parent_topic_id": "t1", "slug": "basic",
            "name": "Basic Again", "level": "microtopic"}},
    )
    assert r.status_code == 409


def test_create_topic_rejects_subject_outside_exam():
    sb = MngSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/topics?exam_id=E1",
        json={"reason": "sneaky cross-exam write", "payload": {
            "subject_id": "s2", "slug": "x", "name": "X", "level": "topic"}},
    )
    assert r.status_code == 422


def test_update_topic_happy_path():
    sb = MngSBStub(_seed())
    r = _client(sb).patch(
        f"{_BASE}/topics/t1?exam_id=E1",
        json={"reason": "fix the display name", "payload": {"description": "updated desc"}},
    )
    assert r.status_code == 200, r.text
    row = next(t for t in sb.db["topics"] if t["id"] == "t1")
    assert row["description"] == "updated desc"


def test_update_identity_field_blocked_when_coverage_locked():
    seed = _seed()
    seed["exam_topic_coverage"][0]["reviewer_status"] = "locked"
    sb = MngSBStub(seed)
    r = _client(sb).patch(
        f"{_BASE}/topics/t1?exam_id=E1",
        json={"reason": "rename a load-bearing topic", "payload": {"name": "Percent"}},
    )
    assert r.status_code == 409
    assert "locked" in str(r.json()["detail"]).lower()


def test_update_any_field_blocked_when_coverage_locked():
    """Rule 4: ALL canonical patches are rejected while coverage is locked."""
    seed = _seed()
    seed["exam_topic_coverage"][0]["reviewer_status"] = "locked"
    sb = MngSBStub(seed)
    r = _client(sb).patch(
        f"{_BASE}/topics/t1?exam_id=E1",
        json={"reason": "annotate description only", "payload": {"description": "note"}},
    )
    assert r.status_code == 409


def test_deactivate_blocked_when_coverage_locked():
    """is_active=false on a locked topic must be rejected (planner-impact)."""
    seed = _seed()
    seed["exam_topic_coverage"][0]["reviewer_status"] = "locked"
    sb = MngSBStub(seed)
    r = _client(sb).patch(
        f"{_BASE}/topics/t1?exam_id=E1",
        json={"reason": "deactivate a load-bearing topic", "payload": {"is_active": False}},
    )
    assert r.status_code == 409
    assert next(t for t in sb.db["topics"] if t["id"] == "t1")["is_active"] is True


def _seed_two_subjects_covered() -> dict:
    seed = _seed()
    # Cover s2 as well, and add a child under t1 in s1.
    seed["exam_topic_coverage"].append({"id": "c2", "exam_id": "E1", "topic_id": "t9", "reviewer_status": "reviewed"})
    seed["topics"].append({"id": "tc", "subject_id": "s1", "parent_topic_id": "t1",
                           "slug": "basic", "name": "Basic", "level": "microtopic", "is_active": True})
    return seed


def test_subject_move_with_retained_cross_subject_parent_rejected():
    """Moving a child to subject s2 while retaining its s1 parent → 422 (OD-15)."""
    sb = MngSBStub(_seed_two_subjects_covered())
    r = _client(sb).patch(
        f"{_BASE}/topics/tc?exam_id=E1",
        json={"reason": "move child across subjects", "payload": {"subject_id": "s2"}},
    )
    assert r.status_code == 422
    assert "different subject" in str(r.json()["detail"]).lower()


def test_subject_move_with_parent_cleared_allowed():
    """Moving a child to s2 and clearing the parent (explicit null) is allowed."""
    sb = MngSBStub(_seed_two_subjects_covered())
    r = _client(sb).patch(
        f"{_BASE}/topics/tc?exam_id=E1",
        json={"reason": "move child and clear parent", "payload": {"subject_id": "s2", "parent_topic_id": None}},
    )
    assert r.status_code == 200, r.text


# ── topic delete bounds (rule 5) ─────────────────────────────────────────


def test_delete_topic_blocked_by_coverage_dependency():
    sb = MngSBStub(_seed())  # t1 has coverage c1
    r = _client(sb).delete(f"{_BASE}/topics/t1?exam_id=E1&reason=cleanup attempt now")
    assert r.status_code == 409
    assert "coverage" in str(r.json()["detail"]).lower()


def test_delete_topic_blocked_by_alias_dependency():
    seed = _seed()
    seed["topic_aliases"].append({"id": "a1", "topic_id": "t2", "alias": "prop", "normalized_alias": "prop"})
    sb = MngSBStub(seed)
    r = _client(sb).delete(f"{_BASE}/topics/t2?exam_id=E1&reason=cleanup attempt now")
    assert r.status_code == 409
    assert "aliases" in str(r.json()["detail"]).lower()


def test_delete_topic_blocked_by_child_topics():
    """parent_topic_id is ON DELETE CASCADE — must not silently delete a subtree."""
    seed = _seed()
    seed["topics"].append({"id": "tc", "subject_id": "s1", "parent_topic_id": "t2",
                           "slug": "basic", "name": "Basic", "level": "microtopic", "is_active": True})
    sb = MngSBStub(seed)
    r = _client(sb).delete(f"{_BASE}/topics/t2?exam_id=E1&reason=would orphan a subtree")
    assert r.status_code == 409
    assert "child topics" in str(r.json()["detail"]).lower()


def test_delete_topic_blocked_by_pyq_question_tags():
    """pyq_question_topic_tags is ON DELETE RESTRICT — clean 409, not a 500."""
    seed = _seed()
    seed["pyq_question_topic_tags"].append({"id": "qt1", "question_id": "q1", "topic_id": "t2", "tag_role": "primary"})
    sb = MngSBStub(seed)
    r = _client(sb).delete(f"{_BASE}/topics/t2?exam_id=E1&reason=question tagged topic")
    assert r.status_code == 409
    assert "pyq question tags" in str(r.json()["detail"]).lower()


def test_delete_topic_blocked_by_target_side_relation_edge():
    """topic_relation_edges.target_topic_id is CASCADE — must also block (409)."""
    seed = _seed()
    seed["topic_relation_edges"].append(
        {"id": "re1", "source_topic_id": "t1", "target_topic_id": "t2", "relation_type": "leads_to"})
    sb = MngSBStub(seed)
    r = _client(sb).delete(f"{_BASE}/topics/t2?exam_id=E1&reason=target of a relation edge")
    assert r.status_code == 409
    assert "target" in str(r.json()["detail"]).lower()


def test_delete_topic_succeeds_when_no_dependencies():
    sb = MngSBStub(_seed())  # t2 has no coverage/aliases/prereqs
    r = _client(sb).delete(f"{_BASE}/topics/t2?exam_id=E1&reason=remove unused topic")
    assert r.status_code == 200, r.text
    assert not any(t["id"] == "t2" for t in sb.db["topics"])


# ── aliases ──────────────────────────────────────────────────────────────


def test_create_alias_derives_normalized_and_audits():
    sb = MngSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/topic-aliases?exam_id=E1",
        json={"reason": "add a known alias", "payload": {"topic_id": "t1", "alias": "  Percent  "}},
    )
    assert r.status_code == 200, r.text
    alias = sb.db["topic_aliases"][-1]
    assert alias["normalized_alias"] == "percent"
    assert sb.db["admin_audit_logs"][-1]["action"] == "exam_intel.manage.topic_alias.create"


def test_create_alias_rejects_topic_outside_exam():
    sb = MngSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/topic-aliases?exam_id=E1",
        json={"reason": "cross-exam alias write", "payload": {"topic_id": "t9", "alias": "hist"}},
    )
    assert r.status_code == 422


def test_delete_alias_happy_path():
    seed = _seed()
    seed["topic_aliases"].append({"id": "a1", "topic_id": "t1", "alias": "pct", "normalized_alias": "pct"})
    sb = MngSBStub(seed)
    r = _client(sb).delete(f"{_BASE}/topic-aliases/a1?exam_id=E1&reason=remove wrong alias")
    assert r.status_code == 200, r.text
    assert not any(a["id"] == "a1" for a in sb.db["topic_aliases"])
