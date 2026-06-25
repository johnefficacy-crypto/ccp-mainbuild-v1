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


class _RpcQuery:
    """Stub for supabase.rpc(fn_name, params).execute() used by the review endpoint."""

    def __init__(self, fn_name: str, params: dict, db: dict):
        self._fn_name = fn_name
        self._params = params
        self._db = db

    def execute(self) -> "_Exec":
        if self._fn_name == "review_pyq_paper":
            return self._exec_review_pyq_paper()
        if self._fn_name == "cms_set_pyq_paper_provenance":
            return self._exec_cms_set_pyq_paper_provenance()
        if self._fn_name == "cms_link_document_to_pyq_paper":
            return self._exec_cms_link_document_to_pyq_paper()
        raise NotImplementedError(f"RPC {self._fn_name!r} not stubbed in TaxSBStub")

    def _exec_review_pyq_paper(self) -> "_Exec":
        """Mirror every check in migration 185's review_pyq_paper() function.

        Order of checks deliberately matches the SQL: reason → target_status →
        lock/not_found → concurrent_modification → transition → provenance →
        atomic writes.  Ensures any bypass of Python prechecks is caught here
        exactly as it would be at the DB level.
        """
        import uuid as _uuid

        p = self._params

        # 1. Reason validation — mirrors SQL step 1.
        #    Explicit None guard: Python's `or ""` would silently coerce None to
        #    an empty string, masking the null path that bypasses SQL's length check
        #    (trim(NULL)=NULL, length(NULL)=NULL, condition evaluates to NULL/unknown).
        reason = p.get("p_reason")
        if reason is None:
            raise Exception("invalid_reason: reason must not be null")
        reason_trimmed = reason.strip()
        if not (8 <= len(reason_trimmed) <= 500):
            raise Exception(
                f"invalid_reason: reason must be 8-500 characters (got {len(reason_trimmed)})"
            )

        # 2. Target status must be a known value.
        if p.get("p_target_status") not in ("verified", "rejected", "pending"):
            raise Exception(
                f"invalid_target_status: {p.get('p_target_status')!r} is not a recognised trust_status"
            )

        papers = self._db.setdefault("pyq_papers", [])
        paper = next((r for r in papers if r.get("id") == p["p_paper_id"]), None)

        # 3. Not found.
        if paper is None:
            raise Exception(f"not_found: paper {p['p_paper_id']} does not exist")

        # 4. Concurrent-modification guard (FOR UPDATE equivalent).
        if paper.get("trust_status") != p["p_expected_status"]:
            raise Exception(
                f"concurrent_modification: expected trust_status={p['p_expected_status']!r}"
                f" but found {paper.get('trust_status')!r}. Re-fetch and retry."
            )

        # 5. Transition validation on the locked row's actual status.
        _allowed: dict[str, tuple[str, ...]] = {
            "pending":  ("verified", "rejected"),
            "verified": ("rejected",),
            "rejected": ("pending",),
        }
        current = paper.get("trust_status")
        target  = p["p_target_status"]
        if target not in _allowed.get(current, ()):
            raise Exception(
                f"transition_not_allowed: {current} -> {target} is not a permitted transition"
            )

        # 6. Provenance gate re-validated on the locked row values.
        #    Mirrors migration 186's updated step 6: source_type required;
        #    at least one anchor (source_url or source_document_id); if
        #    source_document_id is set, validate the document_assets row.
        if current == "pending" and target == "verified":
            blocking = []

            # (a) source_type must be known
            if paper.get("source_type") in (None, "", "unknown"):
                blocking.append("source_type")

            # (b) at least one provenance anchor required
            if (not (paper.get("source_url") and str(paper.get("source_url")).strip())
                    and paper.get("source_document_id") is None):
                blocking.append("source_url")

            # (c) validate attached document if present
            doc_id = paper.get("source_document_id")
            if doc_id is not None:
                docs = self._db.get("document_assets", [])
                doc = next((d for d in docs if d.get("id") == doc_id), None)
                if doc is None:
                    blocking.append("source_document_id_not_found")
                else:
                    if doc.get("scope") != "admin_exam_intelligence":
                        blocking.append("source_document_id_wrong_scope")
                    if doc.get("document_kind") != "pyq_paper":
                        blocking.append("source_document_id_wrong_kind")
                    if doc.get("status") in ("failed", "archived"):
                        blocking.append("source_document_id_bad_status")
                    if not doc.get("storage_bucket") or not doc.get("storage_path"):
                        blocking.append("source_document_id_no_storage")
                    doc_exam = (doc.get("metadata") or {}).get("exam_id")
                    if doc_exam and doc_exam != paper.get("exam_id"):
                        blocking.append("source_document_id_exam_mismatch")

            if blocking:
                raise Exception(
                    f"provenance_incomplete: blocking_fields={','.join(blocking)}"
                )

        # 7+8. Atomic: audit row INSERT + paper UPDATE (both or neither).
        audit_id = str(_uuid.uuid4())
        self._db.setdefault("admin_audit_logs", []).append({
            "id":          audit_id,
            "actor_id":    p["p_actor_id"],
            "actor_email": p["p_actor_email"],
            "action":      "exam_intel.cms.pyq_paper.review",
            "entity_type": "pyq_paper",
            "entity_id":   p["p_paper_id"],
            "new_value": {
                "from_status":  p["p_expected_status"],
                "to_status":    p["p_target_status"],
                "reason":       reason_trimmed,
                "reviewed_by":  p["p_actor_email"],
                "reviewed_at":  "now",
            },
            "notes": "admin_exam_intel_cms",
        })
        paper["trust_status"] = p["p_target_status"]
        paper["updated_at"]   = "now"
        return _Exec({"ok": True, "audit_id": audit_id, "row": dict(paper)})

    def _exec_cms_set_pyq_paper_provenance(self) -> "_Exec":
        """Mirror the atomic UPDATE + audit INSERT of migration 191.

        Mirrors SQL order: compute merged provenance first, then validate the
        merged source_document_id (patch or locked row), then pyq_source_id
        (patch only), then the completeness gate with trim semantics.
        """
        import uuid as _uuid

        p = self._params
        papers = self._db.setdefault("pyq_papers", [])
        paper = next((r for r in papers if str(r.get("id")) == str(p["p_paper_id"])), None)
        if paper is None:
            raise Exception(f"not_found: paper {p['p_paper_id']} does not exist")

        patch = p.get("p_patch", {})

        # Compute merged provenance first (matches new SQL order).
        merged_source_type = patch.get("source_type", paper.get("source_type"))
        merged_source_url  = patch.get("source_url",  paper.get("source_url"))
        merged_source_doc  = patch.get("source_document_id", paper.get("source_document_id"))

        # Validate the merged source_document_id regardless of whether it came
        # from the patch or the locked row.
        if merged_source_doc is not None:
            doc_id = str(merged_source_doc)
            docs = self._db.get("document_assets", [])
            doc = next((d for d in docs if str(d.get("id")) == doc_id), None)
            blocking: list[str] = []
            if doc is None:
                blocking.append("source_document_id_not_found")
            else:
                if doc.get("scope") != "admin_exam_intelligence":
                    blocking.append("source_document_id_wrong_scope")
                if doc.get("document_kind") != "pyq_paper":
                    blocking.append("source_document_id_wrong_kind")
                if doc.get("status") in ("failed", "archived"):
                    blocking.append("source_document_id_bad_status")
                if not doc.get("storage_bucket") or not doc.get("storage_path"):
                    blocking.append("source_document_id_no_storage")
                doc_exam = (doc.get("metadata") or {}).get("exam_id")
                paper_exam = str(paper.get("exam_id") or "")
                if doc_exam and paper_exam and doc_exam != paper_exam:
                    blocking.append("source_document_id_exam_mismatch")
            if blocking:
                raise Exception(
                    f"provenance_incomplete: blocking_fields={','.join(blocking)}"
                )

        # Validate pyq_source_id when present in patch.
        if "pyq_source_id" in patch and patch["pyq_source_id"] is not None:
            src_id = str(patch["pyq_source_id"])
            sources = self._db.get("pyq_sources", [])
            src = next((s for s in sources if str(s.get("id")) == src_id), None)
            blocking: list[str] = []
            if src is None:
                blocking.append("pyq_source_id_not_found")
            else:
                paper_exam = str(paper.get("exam_id") or "")
                src_exam   = str(src.get("exam_id") or "")
                if src_exam and paper_exam and src_exam != paper_exam:
                    blocking.append("pyq_source_id_exam_mismatch")
            if blocking:
                raise Exception(
                    f"provenance_incomplete: blocking_fields={','.join(blocking)}"
                )

        # Capture pre-mutation state from the locked paper (mirrors SQL locked row).
        was_verified = paper.get("trust_status") == "verified"
        previous_provenance = {
            "source_type":        paper.get("source_type"),
            "source_url":         paper.get("source_url"),
            "source_document_id": paper.get("source_document_id"),
            "pyq_source_id":      paper.get("pyq_source_id"),
        }

        # Completeness gate with trim semantics matching SQL and Python pre-check:
        # source_type must be non-null, non-blank (after strip), and not 'unknown';
        # at least one anchor (source_url with non-blank content, or source_document_id).
        merged_url_stripped = (merged_source_url or "").strip()
        merged_type_stripped = (merged_source_type or "").strip()
        gate_ok = (
            merged_source_type is not None
            and merged_type_stripped != ""
            and merged_source_type != "unknown"
            and (merged_url_stripped != "" or merged_source_doc is not None)
        )
        if not gate_ok:
            gate_blocking: list[str] = []
            if (merged_source_type is None
                    or merged_type_stripped == ""
                    or merged_source_type == "unknown"):
                gate_blocking.append("source_type")
            if merged_url_stripped == "" and merged_source_doc is None:
                gate_blocking.append("source_url")
            raise Exception(
                f"provenance_incomplete: blocking_fields={','.join(gate_blocking)}"
            )

        for field in ("source_url", "source_type", "source_document_id", "pyq_source_id"):
            if field in patch:
                paper[field] = patch[field]
        if was_verified:
            paper["trust_status"] = "pending"
        trust_status_after = paper["trust_status"]

        audit_id = str(_uuid.uuid4())
        self._db.setdefault("admin_audit_logs", []).append({
            "id": audit_id,
            "actor_id": p.get("p_actor_id"),
            "actor_email": p.get("p_actor_email"),
            "action": "exam_intel.cms.pyq_paper.set_provenance",
            "entity_type": "pyq_paper",
            "entity_id": p["p_paper_id"],
            "new_value": {
                "reason": p.get("p_reason"),
                "patch": patch,
                "previous_provenance": previous_provenance,
                "demoted_from_verified": was_verified,
            },
            "notes": "admin_exam_intel_cms",
        })
        return _Exec({
            "audit_id": audit_id,
            "demoted_from_verified": was_verified,
            "previous_provenance": previous_provenance,
            "trust_status_after": trust_status_after,
        })

    def _exec_cms_link_document_to_pyq_paper(self) -> "_Exec":
        """Mirror the atomic UPDATE + audit INSERT of migration 189 Part B.

        Includes paper lock + unconditional document lock + six invariant checks,
        mirroring the FOR UPDATE + validation added in migration 189.
        """
        import uuid as _uuid

        p = self._params
        papers = self._db.setdefault("pyq_papers", [])
        paper = next((r for r in papers if str(r.get("id")) == str(p["p_paper_id"])), None)
        if paper is None:
            raise Exception(f"not_found: paper {p['p_paper_id']} does not exist")

        # Always validate the document_assets row.
        doc_id = str(p["p_document_id"])
        docs = self._db.get("document_assets", [])
        doc = next((d for d in docs if str(d.get("id")) == doc_id), None)
        blocking: list[str] = []
        if doc is None:
            blocking.append("source_document_id_not_found")
        else:
            if doc.get("scope") != "admin_exam_intelligence":
                blocking.append("source_document_id_wrong_scope")
            if doc.get("document_kind") != "pyq_paper":
                blocking.append("source_document_id_wrong_kind")
            if doc.get("status") in ("failed", "archived"):
                blocking.append("source_document_id_bad_status")
            if not doc.get("storage_bucket") or not doc.get("storage_path"):
                blocking.append("source_document_id_no_storage")
            doc_exam = (doc.get("metadata") or {}).get("exam_id")
            paper_exam = str(paper.get("exam_id") or "")
            if doc_exam and paper_exam and doc_exam != paper_exam:
                blocking.append("source_document_id_exam_mismatch")
        if blocking:
            raise Exception(
                f"document_not_linkable: blocking_fields={','.join(blocking)}"
            )

        paper["source_document_id"] = p["p_document_id"]
        if p.get("p_was_verified"):
            paper["trust_status"] = "pending"

        audit_id = str(_uuid.uuid4())
        self._db.setdefault("admin_audit_logs", []).append({
            "id": audit_id,
            "actor_id": p.get("p_actor_id"),
            "actor_email": p.get("p_actor_email"),
            "action": "exam_intel.cms.document.link_pyq_paper",
            "entity_type": "pyq_paper",
            "entity_id": p["p_paper_id"],
            "new_value": {
                "reason": p.get("p_reason"),
                "document_asset_id": p["p_document_id"],
                "demoted_from_verified": p.get("p_was_verified"),
            },
            "notes": "admin_exam_intel_cms",
        })
        return _Exec({"audit_id": audit_id, "demoted_from_verified": p.get("p_was_verified")})


class TaxSBStub(SBStub):
    def table(self, name: str):
        return _TaxQuery(name, self.db)

    def rpc(self, fn_name: str, params: dict | None = None) -> _RpcQuery:
        return _RpcQuery(fn_name, params or {}, self.db)


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


# ── bulk import topics: upsert by slug, idempotent re-import ───────────────


def test_bulk_import_topics_upserts_by_slug_no_duplicates_on_reimport():
    sb = TaxSBStub({"subjects": [{"id": "s1", "slug": "quant", "name": "Quant", "is_active": True}]})
    client = _client(sb)
    rows = [
        {"subject_id": "s1", "slug": f"topic-{i}", "name": f"Topic {i}", "level": "topic"}
        for i in range(10)
    ]
    body = {"reason": "bulk seeding ten topics", "entity": "topics", "rows": rows}

    first = client.post(f"{_BASE}/bulk-import", json=body)
    assert first.status_code == 200, first.text
    assert first.json()["ok_count"] == 10
    assert len(sb.db["topics"]) == 10

    # Re-importing the same slugs upserts in place — no duplicate rows.
    second = client.post(f"{_BASE}/bulk-import", json=body)
    assert second.status_code == 200, second.text
    assert second.json()["ok_count"] == 10


# ── audit atomicity: audit INSERT failure rolls back pyq_papers UPDATE ────────


class _AuditFailRpcQuery(_RpcQuery):
    """Simulates a DB-level audit INSERT failure (e.g., constraint violation on
    admin_audit_logs).  In production the SQL function's transaction rolls back
    the pyq_papers UPDATE atomically — no partial mutation is committed.  This
    stub reproduces the observable effect: the RPC raises before performing any
    in-memory writes, so the endpoint returns 500 and the paper row is unchanged.
    """

    def _exec_cms_set_pyq_paper_provenance(self):
        raise Exception(
            "audit_insert_failure: simulated constraint violation on admin_audit_logs"
        )

    def _exec_cms_link_document_to_pyq_paper(self):
        raise Exception(
            "audit_insert_failure: simulated constraint violation on admin_audit_logs"
        )


class _AuditFailSBStub(TaxSBStub):
    def rpc(self, fn_name: str, params: dict | None = None) -> _RpcQuery:
        return _AuditFailRpcQuery(fn_name, params or {}, self.db)


# ── document lock race: document mutated before RPC validation ────────────────


class _DocRaceRpcQuery(_RpcQuery):
    """Simulates a concurrent document_assets mutation occurring between the
    Python pre-check and the review_pyq_paper RPC document-validation step.

    In production, FOR UPDATE on document_assets (migration 187) prevents this
    race: the concurrent writer must wait until review_pyq_paper releases its
    transaction.  This test verifies that the RPC stub faithfully rejects a
    document that was invalidated before the RPC's validation step runs —
    exactly what FOR UPDATE prevents at the DB level.
    """

    def _exec_review_pyq_paper(self):
        # Simulate concurrent mutation: archive the document_assets row just
        # before the RPC's provenance validation runs.
        for doc in self._db.get("document_assets", []):
            doc["status"] = "archived"
        return super()._exec_review_pyq_paper()


class _DocRaceSBStub(TaxSBStub):
    def rpc(self, fn_name: str, params: dict | None = None) -> _RpcQuery:
        return _DocRaceRpcQuery(fn_name, params or {}, self.db)


class _SetProvenanceDocRaceRpcQuery(_RpcQuery):
    """Simulates a concurrent document_assets mutation occurring between the
    Python pre-check and the cms_set_pyq_paper_provenance RPC validation step.

    In production, FOR UPDATE on document_assets (migration 189) prevents this
    race: the concurrent writer must wait until the RPC releases its transaction.
    This stub archives the document before the RPC's own validation runs —
    exactly what FOR UPDATE prevents at the DB level.
    """

    def _exec_cms_set_pyq_paper_provenance(self):
        for doc in self._db.get("document_assets", []):
            doc["status"] = "archived"
        return super()._exec_cms_set_pyq_paper_provenance()


class _SetProvenanceDocRaceSBStub(TaxSBStub):
    def rpc(self, fn_name: str, params: dict | None = None) -> _RpcQuery:
        return _SetProvenanceDocRaceRpcQuery(fn_name, params or {}, self.db)


class _SetProvenanceBlankSourceTypeRaceRpcQuery(_RpcQuery):
    """Concurrent write blanks source_type between Python pre-check and RPC lock.
    The gate must reject '' (blank) even when Python's pre-check saw a valid value."""

    def _exec_cms_set_pyq_paper_provenance(self):
        for p in self._db.get("pyq_papers", []):
            p["source_type"] = ""
        return super()._exec_cms_set_pyq_paper_provenance()


class _SetProvenanceBlankSourceTypeRaceSBStub(TaxSBStub):
    def rpc(self, fn_name: str, params: dict | None = None) -> _RpcQuery:
        return _SetProvenanceBlankSourceTypeRaceRpcQuery(fn_name, params or {}, self.db)


class _SetProvenanceWhitespaceSourceUrlRaceRpcQuery(_RpcQuery):
    """Concurrent write replaces source_url with whitespace-only between Python
    pre-check and RPC lock.  The gate must reject whitespace-only URLs."""

    def _exec_cms_set_pyq_paper_provenance(self):
        for p in self._db.get("pyq_papers", []):
            p["source_url"] = "   "
        return super()._exec_cms_set_pyq_paper_provenance()


class _SetProvenanceWhitespaceSourceUrlRaceSBStub(TaxSBStub):
    def rpc(self, fn_name: str, params: dict | None = None) -> _RpcQuery:
        return _SetProvenanceWhitespaceSourceUrlRaceRpcQuery(fn_name, params or {}, self.db)


class _SetProvenanceRetainedDocArchiveRaceRpcQuery(_RpcQuery):
    """Concurrent write archives a retained source_document_id (not in the patch)
    between Python pre-check and RPC lock.  The RPC must re-validate the merged
    doc even when it came from the locked row (not the patch)."""

    def _exec_cms_set_pyq_paper_provenance(self):
        for doc in self._db.get("document_assets", []):
            doc["status"] = "archived"
        return super()._exec_cms_set_pyq_paper_provenance()


class _SetProvenanceRetainedDocArchiveRaceSBStub(TaxSBStub):
    def rpc(self, fn_name: str, params: dict | None = None) -> _RpcQuery:
        return _SetProvenanceRetainedDocArchiveRaceRpcQuery(fn_name, params or {}, self.db)


class _SetProvenanceUnpatchedFieldChangeRpcQuery(_RpcQuery):
    """After the RPC commits, a concurrent write changes an unpatched field
    (source_type).  Python's re-select after the RPC must return the new value,
    not the stale pre-lock value."""

    def _exec_cms_set_pyq_paper_provenance(self):
        result = super()._exec_cms_set_pyq_paper_provenance()
        for p in self._db.get("pyq_papers", []):
            p["source_type"] = "unofficial"
        return result


class _SetProvenanceUnpatchedFieldChangeSBStub(TaxSBStub):
    def rpc(self, fn_name: str, params: dict | None = None) -> _RpcQuery:
        return _SetProvenanceUnpatchedFieldChangeRpcQuery(fn_name, params or {}, self.db)


def _pyq_review_client(sb, user=None):
    from app.core.auth import get_current_user as _gcu
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[_gcu] = lambda: user or {
        "id": "rev-1", "email": "rev@example.com",
        "role": "admin", "permissions": [cms_api.PERM_REVIEW],
    }
    return TestClient(app, raise_server_exceptions=False)


def test_review_document_lock_catches_concurrent_status_change():
    """Documents archived concurrently (between Python pre-check and RPC) are
    caught by the RPC's validation step.  In production this is enforced via
    FOR UPDATE on document_assets (migration 187).
    """
    db = {
        "pyq_papers": [{
            "id": "p1", "exam_id": "e1", "year": 2024,
            "trust_status": "pending",
            "source_url": None,
            "source_type": "official",
            "source_document_id": "doc-1",
        }],
        "document_assets": [{
            "id": "doc-1",
            "scope": "admin_exam_intelligence",
            "document_kind": "pyq_paper",
            "status": "processed",
            "storage_bucket": "exam-docs",
            "storage_path": "upsc/2024.pdf",
            "metadata": {"exam_id": "e1"},
        }],
        "admin_audit_logs": [],
    }
    sb = _DocRaceSBStub(db)
    client = _pyq_review_client(sb)
    r = client.post(
        f"{_BASE}/pyq-papers/p1/review",
        json={"status": "verified", "reason": "operator verified source document ok"},
    )
    # The RPC mutates the doc to 'archived' before its own check — should block.
    assert r.status_code == 422, r.text
    detail = r.json().get("detail", "")
    assert "source_document_id_bad_status" in str(detail)
