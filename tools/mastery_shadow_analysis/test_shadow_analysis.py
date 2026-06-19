"""Tests for tools/mastery_shadow_analysis/shadow_analysis.py.

All tests use an in-memory stub; no live Supabase credentials are required.
"""
from __future__ import annotations

import json
import os
import sys
import types
from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Minimal Supabase stub
# ---------------------------------------------------------------------------

class _Exec:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, name, db):
        self.name = name
        self.db = db
        self.filters: list[tuple] = []
        self._order_col: str | None = None
        self._range_start: int | None = None
        self._range_end: int | None = None

    def select(self, *a, **kw):
        return self

    def eq(self, k, v):
        self.filters.append((k, "eq", v))
        return self

    def gte(self, k, v):
        self.filters.append((k, "gte", v))
        return self

    def in_(self, k, vals):
        self.filters.append((k, "in", list(vals)))
        return self

    def order(self, col, **kw):
        self._order_col = col
        return self

    def range(self, start, end):
        self._range_start = start
        self._range_end = end
        return self

    def _matches(self, row):
        for k, op, v in self.filters:
            cell = row.get(k)
            if op == "eq" and cell != v:
                return False
            if op == "gte" and (cell is None or cell < v):
                return False
            if op == "in" and cell not in v:
                return False
        return True

    def execute(self):
        rows = self.db.get(self.name, [])
        matched = [r for r in rows if self._matches(r)]
        if self._order_col:
            matched.sort(key=lambda r: (r.get(self._order_col) or ""))
        if self._range_start is not None and self._range_end is not None:
            matched = matched[self._range_start: self._range_end + 1]
        return _Exec(matched)


class _FailQuery(_Query):
    """Raises RuntimeError on execute() to simulate a query failure."""

    def execute(self):
        raise RuntimeError("network error")


class SBStub:
    def __init__(self, db: dict[str, list[dict[str, Any]]] | None = None):
        self.db: dict[str, list[dict[str, Any]]] = db or {}

    def table(self, name: str):
        return _Query(name, self.db)


class SBFailStub(SBStub):
    """Returns a failing query for mock_mastery_shadow."""

    def table(self, name: str):
        if name == "mock_mastery_shadow":
            return _FailQuery(name, self.db)
        return super().table(name)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _recent_iso() -> str:
    """ISO timestamp 1 day ago — always within any reasonable test window."""
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


def _shadow_row(attempt_id, topic_id, delta, current, would_be, trust="platform_verified", *, decided_at=None):
    return {
        "id": f"{attempt_id}-{topic_id}",
        "attempt_id": attempt_id,
        "topic_id": topic_id,
        "proposed_delta_db": str(delta),
        "current_mastery_db": str(current),
        "would_be_mastery_db": str(would_be),
        "trust_level": trust,
        "flag_state": "shadow",
        "decided_at": decided_at or _recent_iso(),
    }


def _correction_row(mock_test_id, user_id, category, topic, source_type="platform_attempt", *, created_at=None):
    return {
        "id": f"{mock_test_id}-{topic}-{category}",
        "mock_test_id": mock_test_id,
        "user_id": user_id,
        "category": category,
        "topic": topic,
        "state": "drafted",
        "created_at": created_at or _recent_iso(),
        "_source_type": source_type,  # used to set mock_tests row
    }


def _make_sb_with_corrections(rows: list[dict]) -> SBStub:
    task_rows = [{k: v for k, v in r.items() if k != "_source_type"} for r in rows]
    mock_test_rows = [
        {"id": r["mock_test_id"], "source_type": r["_source_type"]}
        for r in rows
    ]
    return SBStub({
        "mock_correction_tasks": task_rows,
        "mock_tests": mock_test_rows,
    })


# ---------------------------------------------------------------------------
# Monkey-patch _get_supabase
# ---------------------------------------------------------------------------

def _with_sb(sb, fn, *args, **kwargs):
    import tools.mastery_shadow_analysis.shadow_analysis as sa
    with patch.object(sa, "_get_supabase", return_value=sb):
        return fn(*args, **kwargs)


# ---------------------------------------------------------------------------
# shadow_replay tests
# ---------------------------------------------------------------------------

import tools.mastery_shadow_analysis.shadow_analysis as _sa


def test_shadow_replay_empty_window(capsys):
    sb = SBStub({"mock_mastery_shadow": []})
    _with_sb(sb, _sa.shadow_replay, 14)
    out = capsys.readouterr().out
    assert "INSUFFICIENT_SAMPLE" in out
    assert "no shadow rows" in out


def test_shadow_replay_arithmetic_consistent(capsys):
    """All rows consistent → arithmetic_violations=0, outliers=0."""
    sb = SBStub({"mock_mastery_shadow": [
        _shadow_row("a1", "t1", 5.0, 50.0, 55.0),
        _shadow_row("a1", "t2", -3.0, 40.0, 37.0),
    ]})
    _with_sb(sb, _sa.shadow_replay, 14)
    out = capsys.readouterr().out
    assert "arithmetic_violations=0" in out
    assert "outliers=0" in out


def test_shadow_replay_arithmetic_violation(capsys):
    """Row where would_be ≠ current+delta → arithmetic_violations=1."""
    sb = SBStub({"mock_mastery_shadow": [
        _shadow_row("a1", "t1", 5.0, 50.0, 60.0),  # wrong: should be 55.0
    ]})
    _with_sb(sb, _sa.shadow_replay, 14)
    out = capsys.readouterr().out
    assert "arithmetic_violations=1" in out


def test_shadow_replay_outlier(capsys):
    """Row with |delta| > 15 → outliers=1."""
    sb = SBStub({"mock_mastery_shadow": [
        _shadow_row("a1", "t1", 20.0, 50.0, 70.0),
    ]})
    _with_sb(sb, _sa.shadow_replay, 14)
    out = capsys.readouterr().out
    assert "outliers=1" in out


def test_shadow_replay_duplicate_keys(capsys):
    """Duplicate (attempt_id, topic_id, flag_state) → duplicate_keys=1."""
    sb = SBStub({"mock_mastery_shadow": [
        _shadow_row("a1", "t1", 5.0, 50.0, 55.0),
        {**_shadow_row("a1", "t1", 5.0, 50.0, 55.0), "id": "a1-t1-dup"},
    ]})
    _with_sb(sb, _sa.shadow_replay, 14)
    out = capsys.readouterr().out
    assert "duplicate_keys=1" in out


def test_shadow_replay_reference_sign_agreement_always_decision_required(capsys):
    """reference_sign_agreement is always DECISION_REQUIRED."""
    sb = SBStub({"mock_mastery_shadow": [
        _shadow_row("a1", "t1", 5.0, 50.0, 55.0),
    ]})
    _with_sb(sb, _sa.shadow_replay, 14)
    out = capsys.readouterr().out
    assert "DECISION_REQUIRED" in out


def test_shadow_replay_json_schema(capsys):
    """JSON output contains required keys."""
    sb = SBStub({"mock_mastery_shadow": [
        _shadow_row("a1", "t1", 5.0, 50.0, 55.0),
    ]})
    _with_sb(sb, _sa.shadow_replay, 14, output_json=True)
    out = json.loads(capsys.readouterr().out)
    assert out["command"] == "shadow_replay"
    assert "arithmetic_violations" in out
    assert "outliers" in out
    assert "duplicate_keys" in out
    assert out["reference_sign_agreement"] == "DECISION_REQUIRED"


def test_shadow_replay_clamping_at_boundary():
    """would_be = clamp(current+delta, 0, 100) — test at boundary 100."""
    sb = SBStub({"mock_mastery_shadow": [
        _shadow_row("a1", "t1", 10.0, 95.0, 100.0),  # clamped to 100
    ]})

    results = []
    import tools.mastery_shadow_analysis.shadow_analysis as sa

    orig_emit = sa._emit

    def capture(result, output_json, label):
        results.append(result)

    with patch.object(sa, "_emit", side_effect=capture):
        _with_sb(sb, sa.shadow_replay, 14)

    assert results[0]["arithmetic_violations"] == 0


def test_shadow_replay_trust_breakdown_included():
    """trust_breakdown is populated for known trust levels."""
    sb = SBStub({"mock_mastery_shadow": [
        _shadow_row("a1", "t1", 3.0, 50.0, 53.0, trust="platform_verified"),
        _shadow_row("a2", "t1", 2.0, 40.0, 42.0, trust="self_reported"),
    ]})

    results = []
    import tools.mastery_shadow_analysis.shadow_analysis as sa

    with patch.object(sa, "_emit", side_effect=lambda r, *a, **kw: results.append(r)):
        _with_sb(sb, sa.shadow_replay, 14)

    bd = results[0]["trust_breakdown"]
    assert "platform_verified" in bd
    assert "self_reported" in bd
    assert bd["platform_verified"]["count"] == 1
    assert bd["self_reported"]["count"] == 1


# ---------------------------------------------------------------------------
# live_audit_compare tests
# ---------------------------------------------------------------------------

def test_live_audit_compare_no_shadow(capsys):
    sb = SBStub({"mock_mastery_shadow": [], "user_topic_mastery_audit": []})
    _with_sb(sb, _sa.live_audit_compare, 14)
    out = capsys.readouterr().out
    assert "INSUFFICIENT_SAMPLE" in out


def test_live_audit_compare_no_audit_rows(capsys):
    """When shadow rows exist but no live audit rows, insufficient_sample=True."""
    sb = SBStub({
        "mock_mastery_shadow": [_shadow_row("a1", "t1", 5.0, 50.0, 55.0)],
        "user_topic_mastery_audit": [],
    })
    _with_sb(sb, _sa.live_audit_compare, 14)
    out = capsys.readouterr().out
    assert "INSUFFICIENT_SAMPLE" in out


def test_live_audit_compare_filters_reason_mock_submit():
    """Only audit rows with reason='mock_submit' are counted; rollback rows excluded."""
    audit_rows = [
        {"attempt_id": "a1", "topic_id": "t1", "delta_applied_db": 5.0, "reason": "mock_submit"},
        {"attempt_id": "a1", "topic_id": "t2", "delta_applied_db": -3.0, "reason": "rollback"},
    ]
    shadow_rows = [
        _shadow_row("a1", "t1", 5.0, 50.0, 55.0),
        _shadow_row("a1", "t2", -3.0, 40.0, 37.0),
    ]
    sb = SBStub({
        "mock_mastery_shadow": shadow_rows,
        "user_topic_mastery_audit": [r for r in audit_rows if r["reason"] == "mock_submit"],
    })

    results = []
    import tools.mastery_shadow_analysis.shadow_analysis as sa

    with patch.object(sa, "_emit", side_effect=lambda r, *a, **kw: results.append(r)):
        _with_sb(sb, sa.live_audit_compare, 14)

    # Only t1 matched (reason='mock_submit'); t2 not included
    # With only 1 match, insufficient_sample=True (MIN_SAMPLE=10)
    assert results[0]["matched_with_audit"] == 1
    assert results[0]["insufficient_sample"] is True


def test_live_audit_compare_sign_agreement_sufficient_sample():
    """With ≥10 matching rows, sign_agreement_pct is computed."""
    import tools.mastery_shadow_analysis.shadow_analysis as sa

    shadow = []
    audit = []
    for i in range(12):
        aid = f"a{i}"
        tid = f"t{i}"
        delta = 5.0 if i % 2 == 0 else -3.0
        current = 50.0
        would_be = min(100.0, max(0.0, current + delta))
        shadow.append(_shadow_row(aid, tid, delta, current, would_be))
        audit.append({
            "attempt_id": aid,
            "topic_id": tid,
            "delta_applied_db": delta,
            "reason": "mock_submit",
        })

    sb = SBStub({"mock_mastery_shadow": shadow, "user_topic_mastery_audit": audit})
    results = []
    with patch.object(sa, "_emit", side_effect=lambda r, *a, **kw: results.append(r)):
        _with_sb(sb, sa.live_audit_compare, 14)

    assert results[0]["sign_agreement_pct"] == 100.0
    assert results[0]["insufficient_sample"] is False


# ---------------------------------------------------------------------------
# tasks_overlap tests
# ---------------------------------------------------------------------------

def test_tasks_overlap_empty(capsys):
    sb = SBStub({"mock_correction_tasks": [], "mock_tests": []})
    _with_sb(sb, _sa.tasks_overlap, 14)
    out = capsys.readouterr().out
    assert "INSUFFICIENT_SAMPLE" in out


def test_tasks_overlap_unknown_source():
    """Tasks with no matching mock_tests row are counted in unknown_source."""
    sb = SBStub({
        "mock_correction_tasks": [
            {"id": "c1", "mock_test_id": "mt-missing", "user_id": "u1",
             "category": "concept_gap", "topic": "t1", "state": "drafted",
             "created_at": _recent_iso()},
        ],
        "mock_tests": [],
    })

    results = []
    import tools.mastery_shadow_analysis.shadow_analysis as sa
    with patch.object(sa, "_emit", side_effect=lambda r, *a, **kw: results.append(r)):
        _with_sb(sb, sa.tasks_overlap, 14)

    assert results[0]["unknown_source"] == 1
    assert results[0]["pr5_tasks"] == 0
    assert results[0]["rule_tasks"] == 0


def test_tasks_overlap_semantic_note_present(capsys):
    """topic_semantics_note is always present in output."""
    rows = [
        _correction_row("mt1", "u1", "concept_gap", "topic-uuid-1", "platform_attempt"),
        _correction_row("mt2", "u1", "speed_issue", "Polity", "manual_log"),
    ]
    sb = _make_sb_with_corrections(rows)
    _with_sb(sb, _sa.tasks_overlap, 14)
    out = capsys.readouterr().out
    assert "NOT MEANINGFUL" in out


def test_tasks_overlap_pr5_uses_canonical_topic_id():
    """PR5 corrections (platform_attempt) use topic as canonical UUID key."""
    rows = [
        _correction_row("mt1", "u1", "concept_gap", "uuid-topic-1", "platform_attempt"),
        _correction_row("mt1", "u1", "concept_gap", "uuid-topic-1", "platform_attempt"),  # dup
    ]
    sb = _make_sb_with_corrections(rows)

    results = []
    import tools.mastery_shadow_analysis.shadow_analysis as sa
    with patch.object(sa, "_emit", side_effect=lambda r, *a, **kw: results.append(r)):
        _with_sb(sb, sa.tasks_overlap, 14)

    # Deduped by set — two identical rows → 1 PR5 key
    assert results[0]["pr5_tasks"] == 1


def test_tasks_overlap_different_users_not_deduped():
    """Two platform corrections with same topic/category but different users → 2 PR5 keys."""
    rows = [
        _correction_row("mt1", "u1", "concept_gap", "uuid-topic-1", "platform_attempt"),
        _correction_row("mt2", "u2", "concept_gap", "uuid-topic-1", "platform_attempt"),
    ]
    sb = _make_sb_with_corrections(rows)

    results = []
    import tools.mastery_shadow_analysis.shadow_analysis as sa
    with patch.object(sa, "_emit", side_effect=lambda r, *a, **kw: results.append(r)):
        _with_sb(sb, sa.tasks_overlap, 14)

    assert results[0]["pr5_tasks"] == 2


def test_tasks_overlap_json_schema(capsys):
    rows = [_correction_row("mt1", "u1", "concept_gap", "uuid-t1", "platform_attempt")]
    sb = _make_sb_with_corrections(rows)
    _with_sb(sb, _sa.tasks_overlap, 14, output_json=True)
    out = json.loads(capsys.readouterr().out)
    assert out["command"] == "tasks_overlap"
    assert "topic_semantics_note" in out
    assert "NOT MEANINGFUL" in out["topic_semantics_note"]


# ---------------------------------------------------------------------------
# pagination tests
# ---------------------------------------------------------------------------

def test_pagination_fetches_multiple_batches():
    """_fetch_paginated returns all rows when a table exceeds batch_size."""
    rows = [{"id": str(i), "decided_at": "2026-06-01T00:00:00+00:00"} for i in range(15)]
    sb = SBStub({"test_table": rows})

    result = _sa._fetch_paginated(
        sb, "test_table",
        lambda q: q.gte("decided_at", "2000-01-01"),
        batch_size=7,
        order_by="id",
    )
    assert len(result) == 15


def test_pagination_empty_table():
    sb = SBStub({"test_table": []})
    result = _sa._fetch_paginated(sb, "test_table", lambda q: q, batch_size=100)
    assert result == []


# ---------------------------------------------------------------------------
# credential env var tests
# ---------------------------------------------------------------------------

def test_missing_url_exits(monkeypatch):
    monkeypatch.delenv("NEXT_PUBLIC_SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        _sa._get_supabase()
    assert exc.value.code != 0


def test_old_env_var_names_not_used(monkeypatch):
    """SUPABASE_URL and SUPABASE_SERVICE_KEY are NOT the expected vars."""
    monkeypatch.setenv("SUPABASE_URL", "http://example.com")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    monkeypatch.delenv("NEXT_PUBLIC_SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(SystemExit):
        _sa._get_supabase()


def test_correct_env_vars_accepted(monkeypatch):
    """NEXT_PUBLIC_SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are accepted."""
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_URL", "http://example.com")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "key")

    called_with = []

    def fake_create(url, key):
        called_with.append((url, key))
        return SBStub()

    with patch("tools.mastery_shadow_analysis.shadow_analysis.create_client", fake_create):
        _sa._get_supabase()

    assert called_with == [("http://example.com", "key")]
