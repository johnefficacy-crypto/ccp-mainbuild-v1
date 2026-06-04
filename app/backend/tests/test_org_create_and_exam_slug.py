"""Tests for:
  - POST /admin/organizations (Concern 1)
  - exam conducting_organization_id passthrough (Concern 2)
  - server-side exam slug generation (Concern 3)

Written FAILING first, then made to pass.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api import admin_trust
from app.api import admin_exam_intel_cms as cms


# ─────────────────────────────────────────────────────────────────
# Shared stubs
# ─────────────────────────────────────────────────────────────────

class R:
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class _TableQ:
    """Chainable stub for supabase table queries."""

    def __init__(self, rows=None):
        self._rows = rows or []
        self._inserted = None

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def neq(self, *a, **k): return self
    def in_(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def ilike(self, *a, **k): return self
    def range(self, *a, **k): return self
    def execute(self): return R(list(self._rows))

    def insert(self, payload):
        self._inserted = payload
        # Return a new Q that will echo the payload as the inserted row.
        echo = dict(payload)
        echo.setdefault("id", "new-id-1")
        return _TableQ([echo])

    def update(self, *a, **k): return self
    def upsert(self, *a, **k): return self
    def delete(self, *a, **k): return self


# ─────────────────────────────────────────────────────────────────
# Concern 1 — org create endpoint
# ─────────────────────────────────────────────────────────────────

class _OrgCreateSB:
    """Supabase stub for create_organization tests."""

    def __init__(self, existing_rows=None, name_match_rows=None, raise_on_insert=None):
        self._existing = existing_rows or []   # rows from unique-index check
        self._name_match = name_match_rows or []  # rows from soft-name check
        self._raise_on_insert = raise_on_insert
        self.inserted = None

    def table(self, name):
        if name == "organizations":
            return _OrgTable(self)
        return _TableQ()

    def _do_insert(self, payload):
        if self._raise_on_insert:
            raise self._raise_on_insert
        self.inserted = payload
        echo = dict(payload)
        echo.setdefault("id", "org-new-1")
        return echo


class _OrgTable:
    def __init__(self, sb: _OrgCreateSB):
        self._sb = sb
        self._mode = None

    def select(self, *a, **k):
        self._mode = "select"
        return self

    def eq(self, col, val):
        return self

    def ilike(self, col, val):
        self._mode = "name_match"
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._mode == "name_match":
            return R(list(self._sb._name_match))
        return R(list(self._sb._existing))

    def insert(self, payload):
        self._sb._do_insert(payload)
        if self._sb._raise_on_insert:
            raise self._sb._raise_on_insert
        self._sb.inserted = payload
        echo = dict(payload)
        echo.setdefault("id", "org-new-1")
        return _EchoQ([echo])


class _EchoQ:
    def __init__(self, rows): self._rows = rows
    def execute(self): return R(list(self._rows))


def _org_admin():
    return {"id": "admin-1", "email": "admin@test.com"}


def test_org_create_forces_is_verified_false(monkeypatch):
    """Server must force is_verified=False regardless of client value."""
    sb = _OrgCreateSB()
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)

    body = {"name": "Test PSC", "type": "state_psc", "short_name": "TPSC",
            "state": "rajasthan", "is_verified": True, "trust_tier": "verified",
            "metadata": {"foo": "bar"}}

    result = admin_trust.create_organization(body, _org_admin())

    assert result["ok"] is True
    assert sb.inserted["is_verified"] is False
    assert sb.inserted["trust_tier"] == "unverified"
    assert sb.inserted["metadata"] == {}


def test_org_create_forces_trust_tier_unverified(monkeypatch):
    sb = _OrgCreateSB()
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)

    body = {"name": "Org X", "type": "central", "short_name": "OX",
            "trust_tier": "trusted"}
    result = admin_trust.create_organization(body, _org_admin())
    assert sb.inserted["trust_tier"] == "unverified"


def test_org_create_422_without_short_name(monkeypatch):
    sb = _OrgCreateSB()
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)

    body = {"name": "Org Y", "type": "central"}
    with pytest.raises(HTTPException) as exc_info:
        admin_trust.create_organization(body, _org_admin())
    assert exc_info.value.status_code == 422


def test_org_create_422_without_name(monkeypatch):
    sb = _OrgCreateSB()
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)

    body = {"type": "central", "short_name": "OY"}
    with pytest.raises(HTTPException) as exc_info:
        admin_trust.create_organization(body, _org_admin())
    assert exc_info.value.status_code == 422


def test_org_create_422_without_type(monkeypatch):
    sb = _OrgCreateSB()
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)

    body = {"name": "Org Z", "short_name": "OZ"}
    with pytest.raises(HTTPException) as exc_info:
        admin_trust.create_organization(body, _org_admin())
    assert exc_info.value.status_code == 422


def test_org_create_409_on_dup_short_name(monkeypatch):
    """Simulate the DB raising a unique-constraint violation."""

    class _DupError(Exception):
        pass

    sb = _OrgCreateSB(raise_on_insert=_DupError("duplicate key value"))
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)

    body = {"name": "Another PSC", "type": "state_psc", "short_name": "APSC", "state": "assam"}
    with pytest.raises(HTTPException) as exc_info:
        admin_trust.create_organization(body, _org_admin())
    assert exc_info.value.status_code == 409


def test_org_create_201_with_soft_name_warning(monkeypatch):
    """Same-name (different short_name) triggers non-blocking warnings[]."""
    existing_row = {"id": "org-old-1", "name": "Test PSC"}
    sb = _OrgCreateSB(name_match_rows=[existing_row])
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)

    body = {"name": "Test PSC", "type": "state_psc", "short_name": "TPSC2", "state": "rajasthan"}
    result = admin_trust.create_organization(body, _org_admin())

    assert result["ok"] is True
    assert len(result["warnings"]) >= 1
    assert result["warnings"][0]["existing_id"] == "org-old-1"


# ─────────────────────────────────────────────────────────────────
# Concern 2 — conducting_organization_id in _EXAM_FIELDS
# ─────────────────────────────────────────────────────────────────

def test_conducting_organization_id_in_exam_fields():
    """conducting_organization_id must be present in _EXAM_FIELDS."""
    assert "conducting_organization_id" in cms._EXAM_FIELDS


# ─────────────────────────────────────────────────────────────────
# Concern 3 — server-side exam slug
# ─────────────────────────────────────────────────────────────────

class _ExamSB:
    """Stub for exam create tests."""

    def __init__(self, org_row=None, existing_slug_rows=None, raise_on_insert=None):
        self._org = org_row          # returned when querying organizations
        self._slug_rows = existing_slug_rows or []  # returned for slug uniqueness check
        self._raise_on_insert = raise_on_insert
        self.inserted = None

    def table(self, name):
        return _ExamTable(self, name)


class _ExamTable:
    def __init__(self, sb: _ExamSB, name: str):
        self._sb = sb
        self._name = name
        self._filters = {}

    def select(self, *a, **k): return self
    def eq(self, col, val):
        self._filters[col] = val
        return self
    def limit(self, *a, **k): return self
    def range(self, *a, **k): return self
    def order(self, *a, **k): return self
    def execute(self):
        if self._name == "organizations":
            return R([self._sb._org] if self._sb._org else [])
        if self._name == "exams":
            if "slug" in self._filters:
                return R(list(self._sb._slug_rows))
            return R([])
        if self._name == "exam_families":
            return R([])
        return R([])

    def insert(self, payload):
        # Only capture exam inserts (not audit log or other tables)
        if self._name == "exams":
            if self._sb._raise_on_insert:
                raise self._sb._raise_on_insert
            self._sb.inserted = payload
            echo = dict(payload)
            echo.setdefault("id", "exam-new-1")
            return _EchoQ([echo])
        # For admin_audit_logs and other tables: no-op
        echo = dict(payload)
        echo.setdefault("id", "other-id")
        return _EchoQ([echo])


def _make_cms_body(payload: dict):
    return cms.WriteEnvelope(reason="test reason for slug", payload=payload)


def _cms_admin():
    return {"id": "admin-1", "email": "admin@test.com"}


def _patch_cms(monkeypatch, sb):
    monkeypatch.setattr(cms, "get_supabase_admin", lambda: sb)
    monkeypatch.setattr(cms, "_flag_enabled", lambda: None)
    monkeypatch.setattr(cms, "invalidate_exam_lookup_cache", lambda: None)


def test_exam_create_ignores_payload_slug(monkeypatch):
    """Slug supplied in payload must be ignored; server generates it from name."""
    sb = _ExamSB()
    _patch_cms(monkeypatch, sb)

    body = _make_cms_body({"name": "SSC CGL", "slug": "SHOULD-BE-IGNORED"})
    result = cms.create_exam(body, _cms_admin())

    assert result["ok"] is True
    assert sb.inserted["slug"] == "ssc-cgl"
    assert sb.inserted["slug"] != "SHOULD-BE-IGNORED"


def test_exam_create_slug_from_name_only(monkeypatch):
    """No conducting org → slug = slugify(name)."""
    sb = _ExamSB()
    _patch_cms(monkeypatch, sb)

    body = _make_cms_body({"name": "RBI Grade B"})
    result = cms.create_exam(body, _cms_admin())

    assert result["ok"] is True
    assert sb.inserted["slug"] == "rbi-grade-b"


def test_exam_create_slug_state_psc_prefix(monkeypatch):
    """state_psc org with state → slug = slugify(state)-slugify(name)."""
    org = {"id": "org-1", "type": "state_psc", "state": "Rajasthan"}
    sb = _ExamSB(org_row=org)
    _patch_cms(monkeypatch, sb)

    body = _make_cms_body({"name": "RPSC RAS", "conducting_organization_id": "org-1"})
    result = cms.create_exam(body, _cms_admin())

    assert result["ok"] is True
    assert sb.inserted["slug"] == "rajasthan-rpsc-ras"


def test_exam_create_slug_non_state_psc_no_prefix(monkeypatch):
    """Non-state_psc org → no state prefix, slug = slugify(name)."""
    org = {"id": "org-2", "type": "central", "state": "maharashtra"}
    sb = _ExamSB(org_row=org)
    _patch_cms(monkeypatch, sb)

    body = _make_cms_body({"name": "UPSC CSE", "conducting_organization_id": "org-2"})
    result = cms.create_exam(body, _cms_admin())

    assert result["ok"] is True
    assert sb.inserted["slug"] == "upsc-cse"


def test_exam_create_slug_state_psc_no_state_no_prefix(monkeypatch):
    """state_psc but org has no state → fall back to slugify(name) only."""
    org = {"id": "org-3", "type": "state_psc", "state": None}
    sb = _ExamSB(org_row=org)
    _patch_cms(monkeypatch, sb)

    body = _make_cms_body({"name": "Some Exam", "conducting_organization_id": "org-3"})
    result = cms.create_exam(body, _cms_admin())

    assert result["ok"] is True
    assert sb.inserted["slug"] == "some-exam"


def test_exam_create_409_on_slug_collision(monkeypatch):
    """Duplicate slug → 409 with slug in message, no silent suffix."""
    # Simulate the DB raising a unique violation
    class _UniqueViolation(Exception):
        pass

    sb = _ExamSB(raise_on_insert=_UniqueViolation("duplicate key value violates unique constraint"))
    _patch_cms(monkeypatch, sb)

    body = _make_cms_body({"name": "SSC CGL"})
    with pytest.raises(HTTPException) as exc_info:
        cms.create_exam(body, _cms_admin())
    assert exc_info.value.status_code == 409
    # Colliding slug must appear in the detail message
    assert "ssc-cgl" in str(exc_info.value.detail)


def test_exam_create_persists_conducting_organization_id(monkeypatch):
    """conducting_organization_id must be written to the insert payload."""
    org = {"id": "org-1", "type": "central", "state": None}
    sb = _ExamSB(org_row=org)
    _patch_cms(monkeypatch, sb)

    body = _make_cms_body({"name": "IBPS PO", "conducting_organization_id": "org-1"})
    result = cms.create_exam(body, _cms_admin())

    assert result["ok"] is True
    assert sb.inserted.get("conducting_organization_id") == "org-1"


# ─────────────────────────────────────────────────────────────────
# Concern 1 extras — empty-warnings + dedup normalization
# ─────────────────────────────────────────────────────────────────

def test_org_create_no_warning_when_no_same_name(monkeypatch):
    """No existing name match → warnings list is empty."""
    sb = _OrgCreateSB(name_match_rows=[])
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)

    body = {"name": "Unique Org", "type": "central", "short_name": "UNQ"}
    result = admin_trust.create_organization(body, _org_admin())

    assert result["ok"] is True
    assert result["warnings"] == []


def test_org_create_dedup_normalizes_short_name_case(monkeypatch):
    """short_name 'rpsc' and 'RPSC' with same type/state → second is 409."""
    existing_org = {"id": "org-exist-1", "name": "Rajasthan PSC",
                    "type": "state_psc", "short_name": "RPSC", "state": None}

    # Stub that returns the existing row on the pre-insert check
    class _DedupSB:
        def __init__(self, existing):
            self._existing = existing
            self.inserted = None
            self._check_done = False

        def table(self, name):
            return _DedupTable(self, name)

    class _DedupTable:
        def __init__(self, sb, name):
            self._sb = sb
            self._name = name
            self._filters = {}
            self._mode = None

        def select(self, *a, **k):
            return self

        def eq(self, col, val):
            self._filters[col] = val
            return self

        def ilike(self, col, val):
            self._mode = "name_match"
            return self

        def limit(self, *a, **k):
            return self

        def execute(self):
            if self._mode == "name_match":
                return R([])
            # pre-insert existence check: return existing row
            if self._name == "organizations" and not self._sb._check_done:
                self._sb._check_done = True
                return R([self._sb._existing])
            return R([])

        def insert(self, payload):
            self._sb.inserted = payload
            echo = dict(payload)
            echo.setdefault("id", "org-new-2")
            return _EchoQ([echo])

    sb = _DedupSB(existing_org)
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)

    body = {"name": "Rajasthan PSC 2", "type": "state_psc", "short_name": "rpsc"}
    with pytest.raises(HTTPException) as exc_info:
        admin_trust.create_organization(body, _org_admin())
    assert exc_info.value.status_code == 409
    assert "org-exist-1" in str(exc_info.value.detail)


def test_org_create_dedup_normalizes_spaces(monkeypatch):
    """'AP PSC' and 'APPSC' with same type/state must collide → 409."""
    existing_org = {"id": "org-exist-2", "name": "AP PSC",
                    "type": "state_psc", "short_name": "APPSC", "state": "Andhra Pradesh"}

    class _SpaceSB:
        def __init__(self, existing):
            self._existing = existing
            self.inserted = None
            self._check_done = False

        def table(self, name):
            return _SpaceTable(self, name)

    class _SpaceTable:
        def __init__(self, sb, name):
            self._sb = sb
            self._name = name
            self._mode = None

        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def ilike(self, *a, **k):
            self._mode = "name_match"
            return self
        def limit(self, *a, **k): return self

        def execute(self):
            if self._mode == "name_match":
                return R([])
            if self._name == "organizations" and not self._sb._check_done:
                self._sb._check_done = True
                return R([self._sb._existing])
            return R([])

        def insert(self, payload):
            self._sb.inserted = payload
            echo = dict(payload)
            echo.setdefault("id", "org-new-3")
            return _EchoQ([echo])

    sb = _SpaceSB(existing_org)
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)

    body = {"name": "AP PSC Alt", "type": "state_psc", "short_name": "AP PSC",
            "state": "Andhra Pradesh"}
    with pytest.raises(HTTPException) as exc_info:
        admin_trust.create_organization(body, _org_admin())
    assert exc_info.value.status_code == 409


def test_org_create_dedup_different_state_both_succeed(monkeypatch):
    """Same type+short_name but different non-null states → both are distinct → no 409."""
    # This stub never returns an existing row for the dedup check.
    class _NoDupSB:
        def __init__(self):
            self.inserted = None

        def table(self, name):
            return _NoDupTable(self, name)

    class _NoDupTable:
        def __init__(self, sb, name):
            self._sb = sb
            self._name = name
            self._mode = None

        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def ilike(self, *a, **k):
            self._mode = "name_match"
            return self
        def limit(self, *a, **k): return self

        def execute(self):
            # No existing rows — distinct states never collide
            return R([])

        def insert(self, payload):
            self._sb.inserted = payload
            echo = dict(payload)
            echo.setdefault("id", "org-new-4")
            return _EchoQ([echo])

    sb = _NoDupSB()
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)

    # Different state → should succeed (no 409)
    body = {"name": "Punjab PSC", "type": "state_psc", "short_name": "PPSC",
            "state": "Punjab"}
    result = admin_trust.create_organization(body, _org_admin())
    assert result["ok"] is True
