"""Tests for the contextual PYQ onboarding endpoint.

POST /admin/exam-intelligence-cms/pyq-onboarding

Backed by the atomic SECURITY DEFINER RPC ``cms_pyq_onboarding`` (migration
192).  The stub below mirrors that RPC's single-transaction semantics: it
builds the source / paper / link / audit rows in locals and commits them only
at the very end, so any mid-flow ``raise`` leaves the in-memory store untouched
(modelling the SQL transaction rollback — OD-6).

Covers Section D of the APPROVED gate
(PYQ-Source-and-Paper-Onboarding-Gate-2026-06-25.md):

- new source + paper created pending; source.created=true
- existing_pyq_source_id reused (created=false); trust_status not mutated
- paper.pyq_source_id set to the resolved/created source id
- source-less paper permitted when source_type valid + (source_url|document)
- failed document validation rolls back: no orphan source/paper/audit; 422
- missing/unresolved exam_id -> 422; reason < 8 -> 422; bad source_type -> 422
- audits written (source, paper, envelope)
- caller cannot create a verified source or paper (forced pending)
- cycle / phase ownership validated
"""
from __future__ import annotations

import uuid as _uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub
from tests.persona_questions._stub import _Exec

_BASE = "/api/admin/exam-intelligence-cms"

_CMS = {
    "id": "cms-1", "email": "cms@example.com",
    "role": "admin", "permissions": [cms_api.PERM_CMS],
}
_SUPER = {
    "id": "sup-1", "email": "super@example.com",
    "role": "super_admin", "permissions": [],
}

_VALID_DOC = {
    "id": "doc-1",
    "scope": "admin_exam_intelligence",
    "document_kind": "pyq_paper",
    "status": "processed",
    "storage_bucket": "exam-docs",
    "storage_path": "upsc/2024-paper.pdf",
    "metadata": {"exam_id": "e1"},
}

_SOURCE_TYPES = ("official", "memory_based", "coaching", "community", "aggregator", "unknown")


class _OnboardingRpc:
    """Mirror migration 192's cms_pyq_onboarding() with commit-at-end semantics."""

    def __init__(self, params: dict, db: dict):
        self._p = params
        self._db = db

    def execute(self) -> "_Exec":
        p = self._p
        db = self._db

        # ── reason guard ──
        reason = p.get("p_reason")
        if reason is None or not (8 <= len(reason.strip()) <= 500):
            raise Exception("invalid_reason: reason must be 8-500 characters")

        # ── 1. exam exists ──
        exam_id = p.get("p_exam_id")
        exam = next((e for e in db.get("exams", []) if str(e.get("id")) == str(exam_id)), None)
        if exam is None:
            raise Exception(f"exam_not_found: exam {exam_id} does not exist")

        # ── 1b. cycle / phase ownership ──
        cycle_id = p.get("p_exam_cycle_id")
        if cycle_id is not None:
            cyc = next((c for c in db.get("exam_cycles", []) if str(c.get("id")) == str(cycle_id)), None)
            if cyc is None:
                raise Exception(f"exam_cycle_not_found: cycle {cycle_id} does not exist")
            if str(cyc.get("exam_id")) != str(exam_id):
                raise Exception("exam_cycle_exam_mismatch")

        phase_id = p.get("p_exam_phase_id")
        if phase_id is not None:
            ph = next((c for c in db.get("exam_phases", []) if str(c.get("id")) == str(phase_id)), None)
            if ph is None:
                raise Exception(f"exam_phase_not_found: phase {phase_id} does not exist")
            if str(ph.get("exam_id")) != str(exam_id):
                raise Exception("exam_phase_exam_mismatch")
            # Phase↔cycle consistency (migration 219, fail-closed): a supplied
            # phase must be bound to exactly the supplied cycle. Rejects
            # cross-cycle, cycle-agnostic, and phase-without-cycle combinations.
            if cycle_id is None or str(ph.get("exam_cycle_id")) != str(cycle_id):
                raise Exception("exam_phase_cycle_mismatch")

        # ── 2. source resolution (locals only; commit at end) ──
        src = p.get("p_source")
        resolved_source_id = None
        source_created = False
        source_trust_status = None
        new_source_row = None
        source_audit = None

        if src is not None and src.get("existing_pyq_source_id") is not None:
            existing_id = src["existing_pyq_source_id"]
            existing = next(
                (s for s in db.get("pyq_sources", []) if str(s.get("id")) == str(existing_id)),
                None,
            )
            if existing is None:
                raise Exception(f"pyq_source_not_found: source {existing_id} does not exist")
            if str(existing.get("exam_id")) != str(exam_id):
                raise Exception("pyq_source_exam_mismatch")
            resolved_source_id = existing.get("id")
            source_created = False
            source_trust_status = existing.get("trust_status")
        elif src is not None and any(
            src.get(k) is not None for k in ("source_type", "source_id", "source_url", "title")
        ):
            source_type = src.get("source_type") or "unknown"
            if source_type not in _SOURCE_TYPES:
                raise Exception(f"invalid_source_type: {source_type}")
            new_source_row = {
                "id": str(_uuid.uuid4()),
                "exam_id": exam_id,
                "source_id": src.get("source_id") or None,
                "source_type": source_type,
                "source_url": src.get("source_url") or None,
                "title": src.get("title") or None,
                "trust_status": "pending",
                "metadata": src.get("metadata") or {},
            }
            resolved_source_id = new_source_row["id"]
            source_created = True
            source_trust_status = "pending"
            source_audit = {
                "id": str(_uuid.uuid4()),
                "actor_id": p.get("p_actor_id"),
                "actor_email": p.get("p_actor_email"),
                "action": "exam_intel.cms.pyq_source.create",
                "entity_type": "pyq_source",
                "entity_id": resolved_source_id,
                "new_value": {
                    "reason": reason,
                    "via": "pyq_onboarding",
                    "source_type": source_type,
                    "trust_status": "pending",
                },
                "notes": "admin_exam_intel_cms",
            }

        # ── 3. paper (locals) ──
        paper = p.get("p_paper") or {}
        if paper.get("year") in (None, ""):
            raise Exception("invalid_paper: paper.year is required")
        paper_source_type = paper.get("source_type") or None
        if paper_source_type is not None and paper_source_type not in _SOURCE_TYPES:
            raise Exception(f"invalid_source_type: {paper_source_type}")

        paper_id = str(_uuid.uuid4())
        new_paper_row = {
            "id": paper_id,
            "pyq_source_id": resolved_source_id,
            "exam_id": exam_id,
            "exam_cycle_id": cycle_id,
            "exam_phase_id": phase_id,
            "year": paper.get("year"),
            "paper_date": paper.get("paper_date") or None,
            "shift": paper.get("shift") or None,
            "paper_code": paper.get("paper_code") or None,
            "source_url": paper.get("source_url") or None,
            "source_type": paper_source_type or "unknown",
            "source_document_id": None,
            "trust_status": "pending",
            "metadata": paper.get("metadata") or {},
        }
        paper_audit = {
            "id": str(_uuid.uuid4()),
            "actor_id": p.get("p_actor_id"),
            "actor_email": p.get("p_actor_email"),
            "action": "exam_intel.cms.pyq_paper.create",
            "entity_type": "pyq_paper",
            "entity_id": paper_id,
            "new_value": {
                "reason": reason,
                "via": "pyq_onboarding",
                "year": paper.get("year"),
                "pyq_source_id": resolved_source_id,
                "trust_status": "pending",
            },
            "notes": "admin_exam_intel_cms",
        }

        # ── 4. optional document link (six invariants) ──
        document_id = p.get("p_document_id")
        document_linked = False
        if document_id is not None:
            doc = next(
                (d for d in db.get("document_assets", []) if str(d.get("id")) == str(document_id)),
                None,
            )
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
                if doc_exam and str(doc_exam) != str(exam_id):
                    blocking.append("source_document_id_exam_mismatch")
            if blocking:
                # Raise BEFORE any commit -> full rollback.
                raise Exception(
                    f"document_not_linkable: blocking_fields={','.join(blocking)}"
                )
            new_paper_row["source_document_id"] = document_id
            document_linked = True

        # ── 5. envelope audit ──
        envelope_audit_id = str(_uuid.uuid4())
        envelope_audit = {
            "id": envelope_audit_id,
            "actor_id": p.get("p_actor_id"),
            "actor_email": p.get("p_actor_email"),
            "action": "exam_intel.cms.pyq_onboarding",
            "entity_type": "pyq_paper",
            "entity_id": paper_id,
            "new_value": {
                "reason": reason,
                "exam_id": exam_id,
                "exam_cycle_id": cycle_id,
                "exam_phase_id": phase_id,
                "pyq_source_id": resolved_source_id,
                "source_created": source_created,
                "pyq_paper_id": paper_id,
                "document_id": document_id,
                "document_linked": document_linked,
            },
            "notes": "admin_exam_intel_cms",
        }

        # ── COMMIT (all or nothing) ──
        if new_source_row is not None:
            db.setdefault("pyq_sources", []).append(new_source_row)
        db.setdefault("pyq_papers", []).append(new_paper_row)
        audits = db.setdefault("admin_audit_logs", [])
        if source_audit is not None:
            audits.append(source_audit)
        audits.append(paper_audit)
        audits.append(envelope_audit)

        return _Exec({
            "audit_id": envelope_audit_id,
            "source": (
                None if resolved_source_id is None
                else {
                    "id": resolved_source_id,
                    "created": source_created,
                    "trust_status": source_trust_status,
                }
            ),
            "paper": {
                "id": paper_id,
                "trust_status": "pending",
                "pyq_source_id": resolved_source_id,
            },
            "document_link": (
                {"document_id": document_id, "linked": True} if document_linked else None
            ),
        })


class OnboardingSBStub(TaxSBStub):
    def rpc(self, fn_name: str, params: dict | None = None):
        if fn_name == "cms_pyq_onboarding":
            return _OnboardingRpc(params or {}, self.db)
        return super().rpc(fn_name, params)


def _client(sb, user=_CMS):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def _base_db(**extra):
    db = {
        "exams": [{"id": "e1"}],
        "pyq_sources": [],
        "pyq_papers": [],
        "admin_audit_logs": [],
        "document_assets": [],
        "exam_cycles": [],
        "exam_phases": [],
    }
    db.update(extra)
    return db


def _onboard(client, body):
    return client.post(f"{_BASE}/pyq-onboarding", json=body)


def _body(**over):
    b = {
        "reason": "Added official 2024 paper from commission archive",
        "exam_id": "e1",
        "paper": {"year": 2024, "source_type": "official", "source_url": "https://upsc.gov.in/2024.pdf"},
    }
    b.update(over)
    return b


# ── Source + paper creation ────────────────────────────────────────────────


def test_new_source_and_paper_created_pending_source_created_true():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb), _body(source={
        "source_type": "official", "title": "UPSC Registry",
        "source_url": "https://upsc.gov.in/registry",
    }))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["source"]["created"] is True
    assert body["source"]["trust_status"] == "pending"
    assert body["paper"]["trust_status"] == "pending"
    # Persisted both rows pending.
    assert len(sb.db["pyq_sources"]) == 1
    assert sb.db["pyq_sources"][0]["trust_status"] == "pending"
    assert len(sb.db["pyq_papers"]) == 1
    assert sb.db["pyq_papers"][0]["trust_status"] == "pending"


def test_paper_pyq_source_id_set_to_created_source_id():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb), _body(source={"source_type": "official"}))
    assert r.status_code == 200, r.text
    body = r.json()
    src_id = body["source"]["id"]
    assert body["paper"]["pyq_source_id"] == src_id
    assert sb.db["pyq_papers"][0]["pyq_source_id"] == src_id


# ── Existing source reuse (no trust mutation) ──────────────────────────────


def test_existing_pyq_source_id_reused_not_mutated():
    src = {"id": "src-1", "exam_id": "e1", "source_type": "official",
           "trust_status": "verified", "title": "Existing", "metadata": {}}
    sb = OnboardingSBStub(_base_db(pyq_sources=[src]))
    r = _onboard(_client(sb), _body(source={"existing_pyq_source_id": "src-1"}))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"]["created"] is False
    assert body["source"]["id"] == "src-1"
    # trust_status untouched (OD-2): still 'verified', NOT promoted/demoted.
    assert body["source"]["trust_status"] == "verified"
    assert sb.db["pyq_sources"][0]["trust_status"] == "verified"
    # No new source row created.
    assert len(sb.db["pyq_sources"]) == 1
    assert sb.db["pyq_papers"][0]["pyq_source_id"] == "src-1"


def test_existing_source_cross_exam_is_422():
    src = {"id": "src-1", "exam_id": "other-exam", "source_type": "official",
           "trust_status": "pending", "metadata": {}}
    sb = OnboardingSBStub(_base_db(pyq_sources=[src]))
    r = _onboard(_client(sb), _body(source={"existing_pyq_source_id": "src-1"}))
    assert r.status_code == 422, r.text
    # Nothing created.
    assert len(sb.db["pyq_papers"]) == 0


# ── Source-less paper (OD-1) ───────────────────────────────────────────────


def test_sourceless_paper_with_url_permitted():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb), _body(source=None))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] is None
    assert body["paper"]["pyq_source_id"] is None
    assert body["paper"]["trust_status"] == "pending"
    assert len(sb.db["pyq_sources"]) == 0
    assert len(sb.db["pyq_papers"]) == 1


def test_sourceless_paper_with_document_permitted():
    sb = OnboardingSBStub(_base_db(document_assets=[dict(_VALID_DOC)]))
    r = _onboard(_client(sb), _body(
        source=None,
        paper={"year": 2024, "source_type": "official"},
        document_id="doc-1",
    ))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] is None
    assert body["document_link"] == {"document_id": "doc-1", "linked": True}
    assert sb.db["pyq_papers"][0]["source_document_id"] == "doc-1"


# ── Document linking + rollback ────────────────────────────────────────────


def test_valid_document_linked():
    sb = OnboardingSBStub(_base_db(document_assets=[dict(_VALID_DOC)]))
    r = _onboard(_client(sb), _body(source={"source_type": "official"}, document_id="doc-1"))
    assert r.status_code == 200, r.text
    assert r.json()["document_link"]["linked"] is True


def test_failed_document_validation_rolls_back_everything():
    bad_doc = {**_VALID_DOC, "document_kind": "syllabus"}  # wrong kind
    sb = OnboardingSBStub(_base_db(document_assets=[bad_doc]))
    r = _onboard(_client(sb), _body(source={"source_type": "official", "title": "X"}, document_id="doc-1"))
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert detail["error"] == "document_not_linkable"
    assert "source_document_id_wrong_kind" in detail["blocking_fields"]
    # Atomicity: no orphan source, paper, or audit rows.
    assert len(sb.db["pyq_sources"]) == 0
    assert len(sb.db["pyq_papers"]) == 0
    assert len(sb.db["admin_audit_logs"]) == 0


def test_document_not_found_rolls_back():
    sb = OnboardingSBStub(_base_db())  # no document_assets
    r = _onboard(_client(sb), _body(source={"source_type": "official"}, document_id="missing"))
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert detail["error"] == "document_not_linkable"
    assert "source_document_id_not_found" in detail["blocking_fields"]
    assert len(sb.db["pyq_papers"]) == 0
    assert len(sb.db["admin_audit_logs"]) == 0


# ── Request validation ─────────────────────────────────────────────────────


def test_missing_exam_resolves_422():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb), _body(exam_id="does-not-exist"))
    assert r.status_code == 422, r.text
    assert len(sb.db["pyq_papers"]) == 0


def test_reason_too_short_422():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb), _body(reason="short"))
    assert r.status_code == 422, r.text


def test_bad_paper_source_type_enum_422():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb), _body(paper={"year": 2024, "source_type": "nonsense"}))
    assert r.status_code == 422, r.text
    assert len(sb.db["pyq_papers"]) == 0


def test_bad_source_block_source_type_enum_422():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb), _body(source={"source_type": "nonsense"}))
    assert r.status_code == 422, r.text
    assert len(sb.db["pyq_sources"]) == 0


# ── Caller cannot force verified ───────────────────────────────────────────


def test_caller_cannot_create_verified_source_or_paper():
    # Even if a client smuggles trust_status into metadata-adjacent fields, the
    # endpoint/RPC only ever write 'pending'.  The contract models do not expose
    # a trust_status input, so we assert the persisted + returned status is pending.
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb), _body(source={"source_type": "official"}))
    assert r.status_code == 200, r.text
    assert r.json()["source"]["trust_status"] == "pending"
    assert r.json()["paper"]["trust_status"] == "pending"
    assert sb.db["pyq_sources"][0]["trust_status"] == "pending"
    assert sb.db["pyq_papers"][0]["trust_status"] == "pending"


# ── Audits ─────────────────────────────────────────────────────────────────


def test_audits_written_source_paper_envelope():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb), _body(source={"source_type": "official"}))
    assert r.status_code == 200, r.text
    actions = [a["action"] for a in sb.db["admin_audit_logs"]]
    assert "exam_intel.cms.pyq_source.create" in actions
    assert "exam_intel.cms.pyq_paper.create" in actions
    assert "exam_intel.cms.pyq_onboarding" in actions
    # Envelope audit carries the reason + created ids.
    envelope = next(a for a in sb.db["admin_audit_logs"] if a["action"] == "exam_intel.cms.pyq_onboarding")
    assert envelope["new_value"]["reason"] == "Added official 2024 paper from commission archive"
    assert envelope["new_value"]["pyq_paper_id"] == r.json()["paper"]["id"]
    assert r.json()["audit_id"] == envelope["id"]


def test_sourceless_onboarding_writes_no_source_audit():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb), _body(source=None))
    assert r.status_code == 200, r.text
    actions = [a["action"] for a in sb.db["admin_audit_logs"]]
    assert "exam_intel.cms.pyq_source.create" not in actions
    assert actions.count("exam_intel.cms.pyq_paper.create") == 1
    assert actions.count("exam_intel.cms.pyq_onboarding") == 1


# ── Cycle / phase ownership ────────────────────────────────────────────────


def test_cycle_ownership_validated_ok():
    cyc = {"id": "cyc-1", "exam_id": "e1"}
    sb = OnboardingSBStub(_base_db(exam_cycles=[cyc]))
    r = _onboard(_client(sb), _body(exam_cycle_id="cyc-1"))
    assert r.status_code == 200, r.text
    assert sb.db["pyq_papers"][0]["exam_cycle_id"] == "cyc-1"


def test_cycle_cross_exam_is_422():
    cyc = {"id": "cyc-1", "exam_id": "other"}
    sb = OnboardingSBStub(_base_db(exam_cycles=[cyc]))
    r = _onboard(_client(sb), _body(exam_cycle_id="cyc-1"))
    assert r.status_code == 422, r.text
    assert len(sb.db["pyq_papers"]) == 0


def test_phase_cross_exam_is_422():
    ph = {"id": "ph-1", "exam_id": "other"}
    sb = OnboardingSBStub(_base_db(exam_phases=[ph]))
    r = _onboard(_client(sb), _body(exam_phase_id="ph-1"))
    assert r.status_code == 422, r.text
    assert len(sb.db["pyq_papers"]) == 0


def test_phase_with_matching_cycle_ok():
    # New contract (migration 219): a supplied phase must be accompanied by its
    # own cycle. Cycle-bound phase + matching cycle → persisted together.
    cyc = {"id": "cyc-1", "exam_id": "e1"}
    ph = {"id": "ph-1", "exam_id": "e1", "exam_cycle_id": "cyc-1"}
    sb = OnboardingSBStub(_base_db(exam_cycles=[cyc], exam_phases=[ph]))
    r = _onboard(_client(sb), _body(exam_cycle_id="cyc-1", exam_phase_id="ph-1"))
    assert r.status_code == 200, r.text
    assert sb.db["pyq_papers"][0]["exam_cycle_id"] == "cyc-1"
    assert sb.db["pyq_papers"][0]["exam_phase_id"] == "ph-1"


def test_phase_cross_cycle_same_exam_is_422_and_rolls_back():
    # Cycle A supplied, but the phase belongs to cycle B of the SAME exam.
    # This is the exact hole the review flagged — must fail closed, no writes.
    cyc_a = {"id": "cyc-A", "exam_id": "e1"}
    cyc_b = {"id": "cyc-B", "exam_id": "e1"}
    ph_b = {"id": "ph-B", "exam_id": "e1", "exam_cycle_id": "cyc-B"}
    sb = OnboardingSBStub(_base_db(exam_cycles=[cyc_a, cyc_b], exam_phases=[ph_b]))
    r = _onboard(_client(sb), _body(
        exam_cycle_id="cyc-A", exam_phase_id="ph-B",
        source={"source_type": "official"},
    ))
    assert r.status_code == 422, r.text
    assert "exam_phase_cycle_mismatch" in r.text
    # Transaction rollback: no paper, no source, no audit rows persisted.
    assert len(sb.db["pyq_papers"]) == 0
    assert len(sb.db["pyq_sources"]) == 0
    assert len(sb.db["admin_audit_logs"]) == 0


def test_phase_without_cycle_is_422():
    # Fail-closed: a phase supplied with no cycle at all is contradictory.
    ph = {"id": "ph-1", "exam_id": "e1", "exam_cycle_id": "cyc-1"}
    sb = OnboardingSBStub(_base_db(exam_phases=[ph]))
    r = _onboard(_client(sb), _body(exam_phase_id="ph-1"))
    assert r.status_code == 422, r.text
    assert "exam_phase_cycle_mismatch" in r.text
    assert len(sb.db["pyq_papers"]) == 0


def test_template_phase_no_cycle_binding_is_422():
    # A cycle-agnostic (template) phase cannot anchor a cycle-scoped paper.
    cyc = {"id": "cyc-1", "exam_id": "e1"}
    ph = {"id": "ph-tmpl", "exam_id": "e1", "exam_cycle_id": None}
    sb = OnboardingSBStub(_base_db(exam_cycles=[cyc], exam_phases=[ph]))
    r = _onboard(_client(sb), _body(exam_cycle_id="cyc-1", exam_phase_id="ph-tmpl"))
    assert r.status_code == 422, r.text
    assert "exam_phase_cycle_mismatch" in r.text
    assert len(sb.db["pyq_papers"]) == 0


# ── Authorization ──────────────────────────────────────────────────────────


def test_cms_permission_allowed():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb, _CMS), _body())
    assert r.status_code == 200, r.text


def test_super_admin_allowed():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb, _SUPER), _body())
    assert r.status_code == 200, r.text


def test_unauthenticated_rejected():
    sb = OnboardingSBStub(_base_db())
    r = _onboard(_client(sb, user=None), _body())
    assert r.status_code in (401, 403), r.text
