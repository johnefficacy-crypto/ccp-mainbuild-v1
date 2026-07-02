"""EWP-4 Error Lab endpoint-shaping tests.

The owner-scoping, feedback-release gating, `affects_current_state` filter, the
effective-review-decision fold (§4.10a) and the reclassification remap now live
in SQL — `public.ewp_error_lab` / `ewp_private.ewp_error_lab` (migration 213) —
so those behaviours are exercised against a real Postgres in
`test_writing_error_lab_read_model_behaviour.py` (EWP_PG_DSN-gated).

Here we test the thin Python endpoints (`error_lab` / `error_summary`) purely as
consumers of that read model: they call the RPC once (no session→unit→version
→evaluation ID fan-out) and shape the returned rows into microtopic groups /
counts, carrying the human `microtopic_name` + `microtopic_slug` through.

Skips if the module's optional deps are unavailable locally (present in CI).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("supabase")

from app.api import writing_practice as wp  # noqa: E402


class _Res:
    def __init__(self, data):
        self.data = data


class _FakeSupabase:
    """Fake service-role client whose only surface the endpoints use is rpc()."""

    def __init__(self, rows, *, spy=None):
        self._rows = rows
        self._spy = spy if spy is not None else []

    def rpc(self, name, params):
        self._spy.append((name, params))
        return _RpcCall(name, params, self._rows)


class _RpcCall:
    def __init__(self, name, params, rows):
        self._name = name
        self._params = params
        self._rows = rows

    def execute(self):
        assert self._name == "ewp_error_lab"
        return _Res(list(self._rows))


def _rows():
    """What ewp_error_lab returns: current-state, effective-decision-resolved
    issues with the microtopic name/slug already joined (no UUIDs to render)."""
    return [
        {"id": "i1", "issue_type": "subject_verb_agreement", "severity": "must_fix",
         "quoted_text": "they was", "explanation": "Use 'were'.",
         "suggested_text": "they were", "span_start_utf16": 0, "span_end_utf16": 8,
         "microtopic_id": "m1", "microtopic_name": "Subject-verb agreement",
         "microtopic_slug": "subject-verb-agreement",
         "created_at": "2026-06-01T00:00:00+00:00"},
        {"id": "i2", "issue_type": "subject_verb_agreement", "severity": "should_fix",
         "quoted_text": "he go", "explanation": "Use 'goes'.",
         "suggested_text": "he goes", "span_start_utf16": 10, "span_end_utf16": 15,
         "microtopic_id": "m1", "microtopic_name": "Subject-verb agreement",
         "microtopic_slug": "subject-verb-agreement",
         "created_at": "2026-06-03T00:00:00+00:00"},
        {"id": "i3", "issue_type": "word_choice", "severity": "advisory",
         "quoted_text": "big", "explanation": "Consider 'large'.",
         "suggested_text": "large", "span_start_utf16": 20, "span_end_utf16": 23,
         "microtopic_id": None, "microtopic_name": None, "microtopic_slug": None,
         "created_at": "2026-06-02T00:00:00+00:00"},
    ]


def _patch(monkeypatch, rows, spy=None):
    fake = _FakeSupabase(rows, spy=spy)
    monkeypatch.setattr(wp, "get_supabase_admin", lambda: fake)
    return fake


def test_error_lab_uses_the_rpc_read_model_once(monkeypatch):
    spy: list = []
    _patch(monkeypatch, _rows(), spy=spy)
    wp.error_lab(user={"id": "U1"})
    # Exactly one server-side call, owner-scoped — no per-hop ID fan-out.
    assert spy == [("ewp_error_lab", {"p_user": "U1"})]


def test_error_lab_groups_by_microtopic_with_names_and_ordering(monkeypatch):
    _patch(monkeypatch, _rows())
    out = wp.error_lab(user={"id": "U1"})
    items = out["items"]
    # Busiest microtopic first: m1 has 2, unmapped has 1.
    assert [g["issue_count"] for g in items] == [2, 1]
    m1 = items[0]
    assert m1["microtopic_id"] == "m1"
    assert m1["microtopic_name"] == "Subject-verb agreement"
    assert m1["microtopic_slug"] == "subject-verb-agreement"
    # Recency order within the group (i2 @06-03 before i1 @06-01).
    assert [i["id"] for i in m1["issues"]] == ["i2", "i1"]
    # Unmapped group carries a null id/name (frontend renders a generic label).
    unmapped = items[1]
    assert unmapped["microtopic_id"] is None
    assert unmapped["microtopic_name"] is None
    assert [i["id"] for i in unmapped["issues"]] == ["i3"]


def test_error_summary_counts_from_the_same_model(monkeypatch):
    _patch(monkeypatch, _rows())
    out = wp.error_summary(user={"id": "U1"})
    assert out["by_microtopic"] == {"m1": 2, "unmapped": 1}


def test_empty_model_yields_empty_surfaces(monkeypatch):
    _patch(monkeypatch, [])
    assert wp.error_lab(user={"id": "U1"}) == {"items": []}
    assert wp.error_summary(user={"id": "U1"}) == {"by_microtopic": {}}


def test_missing_user_short_circuits_without_calling_rpc(monkeypatch):
    spy: list = []
    _patch(monkeypatch, _rows(), spy=spy)
    assert wp._error_lab_rows(wp.get_supabase_admin(), None) == []
    assert spy == []
