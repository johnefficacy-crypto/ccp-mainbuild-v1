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


def test_update_nonidentity_field_allowed_when_coverage_locked():
    seed = _seed()
    seed["exam_topic_coverage"][0]["reviewer_status"] = "locked"
    sb = MngSBStub(seed)
    r = _client(sb).patch(
        f"{_BASE}/topics/t1?exam_id=E1",
        json={"reason": "annotate description only", "payload": {"description": "note"}},
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
