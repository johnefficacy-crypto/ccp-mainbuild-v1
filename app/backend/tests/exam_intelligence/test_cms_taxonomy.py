"""Backend CMS endpoints for the subject/topic taxonomy (migration 029).

Covers the create/list/validation contract for subjects, topics,
topic-aliases, and topic-prerequisites added under
``/api/admin/exam-intelligence-cms``. The shared SBStub keeps a tight
surface, so a small local subclass adds the ``ilike`` / ``range`` /
``count="exact"`` features the list endpoints use — same approach the
admin_study_os tests take, without polluting the shared stub.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core import config as core_config
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub, _Exec, _Query

_BASE = "/api/admin/exam-intelligence-cms"


class _TaxQuery(_Query):
    """Adds ilike / range / count='exact' on the read path only."""

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
        # Writes (insert/update/upsert/delete) use the base behaviour.
        if (
            self._pending_insert is not None
            or self._pending_update is not None
            or self._pending_upsert is not None
        ):
            return super().execute()
        # Base _matches ignores unknown ops, so strip ilike out and apply it
        # here after the eq/in/etc. filters have run.
        ilikes = [(k, v) for (k, op, v) in self.filters if op == "ilike"]
        self.filters = [f for f in self.filters if f[1] != "ilike"]
        res = super().execute()
        data = list(res.data)
        for k, needle in ilikes:
            data = [r for r in data if isinstance(r.get(k), str) and needle in r[k].lower()]
        out = _Exec(data)
        if self._count_exact:
            out.count = len(data)  # total before pagination, like PostgREST
        if self._range:
            lo, hi = self._range
            out.data = data[lo : hi + 1]
        return out


class TaxSBStub(SBStub):
    def table(self, name: str):
        return _TaxQuery(name, self.db)


def _client(sb: TaxSBStub, *, flag: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    if flag:
        app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    else:
        core_config.get_settings.cache_clear()
        core_config.get_settings().ADMIN_STUDY_OS_ENABLED = False
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1",
        "role": "super_admin",
        "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed() -> dict:
    return {
        "subjects": [
            {"id": "s1", "slug": "quant", "name": "Quantitative Aptitude", "is_active": True},
            {"id": "s2", "slug": "reasoning", "name": "Logical Reasoning", "is_active": True},
        ],
        "topics": [
            {"id": "t1", "subject_id": "s1", "parent_topic_id": None, "slug": "percentages",
             "name": "Percentages", "level": "topic", "is_active": True},
            {"id": "t2", "subject_id": "s1", "parent_topic_id": None, "slug": "ratios",
             "name": "Ratios", "level": "topic", "is_active": True},
        ],
    }


# ── 1. subjects create ───────────────────────────────────────────────────


def test_post_subject_creates_row_with_default_active():
    sb = TaxSBStub({})
    r = _client(sb).post(
        f"{_BASE}/subjects",
        json={"reason": "seeding a subject", "payload": {"slug": "english", "name": "English", "subject_group": "language"}},
    )
    assert r.status_code == 200, r.text
    row = sb.db["subjects"][0]
    assert row["slug"] == "english"
    assert row["subject_group"] == "language"
    assert row["is_active"] is True


def test_post_subject_rejects_unknown_field_422():
    sb = TaxSBStub({})
    r = _client(sb).post(
        f"{_BASE}/subjects",
        json={"reason": "bad field attempt", "payload": {"slug": "x", "name": "X", "priority": 3}},
    )
    assert r.status_code == 422, r.text
    assert "priority" in str(r.json().get("detail"))


def test_post_subject_upsert_by_slug_is_idempotent():
    sb = TaxSBStub({})
    client = _client(sb)
    body = {"reason": "idempotent reimport", "payload": {"slug": "english", "name": "English"}}
    assert client.post(f"{_BASE}/subjects", json=body).status_code == 200
    assert client.post(f"{_BASE}/subjects", json={**body, "payload": {"slug": "english", "name": "English (updated)"}}).status_code == 200
    rows = [s for s in sb.db["subjects"] if s["slug"] == "english"]
    assert len(rows) == 1
    assert rows[0]["name"] == "English (updated)"


# ── 2 & 3. topics create + parent/subject + level rules ───────────────────


def test_post_topic_with_parent_of_wrong_subject_422():
    sb = TaxSBStub(_seed())
    # t1 belongs to s1; creating a topic under s2 with parent t1 must fail.
    r = _client(sb).post(
        f"{_BASE}/topics",
        json={"reason": "mismatched parent subject", "payload": {
            "subject_id": "s2", "parent_topic_id": "t1", "slug": "child", "name": "Child"}},
    )
    assert r.status_code == 422, r.text
    assert "different subject" in str(r.json().get("detail"))


def test_post_microtopic_without_parent_is_allowed():
    """Migration 029 has no constraint tying level to parent_topic_id, so a
    parentless microtopic is permitted."""
    sb = TaxSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/topics",
        json={"reason": "parentless microtopic", "payload": {
            "subject_id": "s1", "slug": "simple-interest", "name": "Simple Interest", "level": "microtopic"}},
    )
    assert r.status_code == 200, r.text
    created = [t for t in sb.db["topics"] if t["slug"] == "simple-interest"][0]
    assert created["level"] == "microtopic"
    assert created.get("parent_topic_id") in (None, "")


def test_post_topic_rejects_bad_level_422():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/topics",
        json={"reason": "bad level value", "payload": {
            "subject_id": "s1", "slug": "x", "name": "X", "level": "chapter"}},
    )
    assert r.status_code == 422, r.text


# ── 4 & 5. topic-prerequisites self-ref + cycle ───────────────────────────


def test_post_prerequisite_self_reference_422():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/topic-prerequisites",
        json={"reason": "self reference attempt", "payload": {
            "topic_id": "t1", "prerequisite_topic_id": "t1"}},
    )
    assert r.status_code == 422, r.text
    assert "own prerequisite" in str(r.json().get("detail"))


def test_post_prerequisite_cycle_422():
    sb = TaxSBStub({
        **_seed(),
        "topic_prerequisites": [
            {"id": "p1", "topic_id": "t1", "prerequisite_topic_id": "t2", "relation_type": "requires"}
        ],
    })
    # t1 already requires t2; making t2 require t1 would close a 2-node cycle.
    r = _client(sb).post(
        f"{_BASE}/topic-prerequisites",
        json={"reason": "would create a cycle", "payload": {
            "topic_id": "t2", "prerequisite_topic_id": "t1"}},
    )
    assert r.status_code == 422, r.text
    assert "cycle" in str(r.json().get("detail")).lower()


def test_post_prerequisite_happy_path_persists():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/topic-prerequisites",
        json={"reason": "t2 requires t1 first", "payload": {
            "topic_id": "t2", "prerequisite_topic_id": "t1", "relation_type": "requires"}},
    )
    assert r.status_code == 200, r.text
    assert sb.db["topic_prerequisites"][0]["prerequisite_topic_id"] == "t1"


# ── topic-aliases derive normalized_alias ─────────────────────────────────


def test_post_topic_alias_derives_normalized_alias():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/topic-aliases",
        json={"reason": "adding an alias", "payload": {"topic_id": "t1", "alias": "  Percent  "}},
    )
    assert r.status_code == 200, r.text
    row = sb.db["topic_aliases"][0]
    assert row["alias"] == "  Percent  "
    assert row["normalized_alias"] == "percent"


def test_post_topic_alias_rejects_legacy_alias_text_422():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/topic-aliases",
        json={"reason": "stale field name", "payload": {"topic_id": "t1", "alias_text": "Percent"}},
    )
    assert r.status_code == 422, r.text
    assert "alias_text" in str(r.json().get("detail"))


# ── 6. flag gating ────────────────────────────────────────────────────────


def test_flag_disabled_returns_404():
    sb = TaxSBStub(_seed())
    try:
        r = _client(sb, flag=False).get(f"{_BASE}/subjects")
        assert r.status_code == 404, r.text
    finally:
        # Reset the cached settings so other tests see a clean flag.
        core_config.get_settings.cache_clear()


# ── 7. list filters ───────────────────────────────────────────────────────


def test_list_subjects_q_filter():
    sb = TaxSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/subjects?q=logical")
    assert r.status_code == 200, r.text
    slugs = [s["slug"] for s in r.json()["items"]]
    assert slugs == ["reasoning"]


def test_list_topics_filters_by_subject_and_level():
    sb = TaxSBStub({
        **_seed(),
        "topics": [
            {"id": "t1", "subject_id": "s1", "slug": "a", "name": "A", "level": "topic", "is_active": True},
            {"id": "t2", "subject_id": "s2", "slug": "b", "name": "B", "level": "topic", "is_active": True},
            {"id": "t3", "subject_id": "s1", "slug": "c", "name": "C", "level": "microtopic", "is_active": True},
        ],
    })
    client = _client(sb)
    by_subject = client.get(f"{_BASE}/topics?subject_id=s1")
    assert by_subject.status_code == 200
    assert {t["id"] for t in by_subject.json()["items"]} == {"t1", "t3"}

    by_level = client.get(f"{_BASE}/topics?subject_id=s1&level=microtopic")
    assert {t["id"] for t in by_level.json()["items"]} == {"t3"}
