"""Tests for tools/mastery_shadow_analysis/shadow_analysis.py.

All tests use an in-memory stub; no live Supabase credentials are required.
"""
from __future__ import annotations

import json
import os
import sys
import types
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Minimal Supabase stub
# ---------------------------------------------------------------------------


class _Exec:
    def __init__(self, data: list) -> None:
        self.data = data


class _Query:
    def __init__(self, name: str, db: dict) -> None:
        self.name = name
        self.db = db
        self.filters: list[tuple] = []
        self._order_col: str | None = None
        self._range_start: int | None = None
        self._range_end: int | None = None

    def select(self, *a: Any, **kw: Any) -> "_Query":
        return self

    def eq(self, k: str, v: Any) -> "_Query":
        self.filters.append((k, "eq", v))
        return self

    def gte(self, k: str, v: Any) -> "_Query":
        self.filters.append((k, "gte", v))
        return self

    def lte(self, k: str, v: Any) -> "_Query":
        self.filters.append((k, "lte", v))
        return self

    def in_(self, k: str, vals: list) -> "_Query":
        self.filters.append((k, "in", list(vals)))
        return self

    def order(self, col: str, **kw: Any) -> "_Query":
        self._order_col = col
        return self

    def range(self, start: int, end: int) -> "_Query":
        self._range_start = start
        self._range_end = end
        return self

    def _matches(self, row: dict) -> bool:
        for k, op, v in self.filters:
            cell = row.get(k)
            if op == "eq" and cell != v:
                return False
            if op == "gte" and (cell is None or cell < v):
                return False
            if op == "lte" and (cell is None or cell > v):
                return False
            if op == "in" and cell not in v:
                return False
        return True

    def execute(self) -> _Exec:
        rows = self.db.get(self.name, [])
        matched = [r for r in rows if self._matches(r)]
        if self._order_col:
            matched.sort(key=lambda r: (r.get(self._order_col) or ""))
        if self._range_start is not None and self._range_end is not None:
            matched = matched[self._range_start : self._range_end + 1]
        return _Exec(matched)


class _FailQuery(_Query):
    def execute(self) -> _Exec:
        raise RuntimeError("network error")


class SBStub:
    def __init__(self, db: dict[str, list[dict]] | None = None) -> None:
        self.db: dict[str, list[dict]] = db or {}
        self.write_calls: list[dict] = []

    def table(self, name: str) -> "_Query":
        return _Query(name, self.db)


class SBFailStub(SBStub):
    def table(self, name: str) -> "_Query":
        if name == "mock_mastery_shadow":
            return _FailQuery(name, self.db)
        return super().table(name)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _recent_iso() -> str:
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


def _shadow_row(
    attempt_id: str,
    topic_id: str,
    delta: float,
    current: float,
    would_be: float,
    trust: str = "platform_verified",
    *,
    decided_at: str | None = None,
    flag_state: str = "shadow",
    unweighted: float | None = None,
) -> dict:
    if unweighted is None:
        unweighted = delta
    return {
        "id": f"{attempt_id}-{topic_id}",
        "attempt_id": attempt_id,
        "topic_id": topic_id,
        "proposed_delta_db": str(delta),
        "proposed_delta_db_unweighted": str(unweighted),
        "current_mastery_db": str(current),
        "would_be_mastery_db": str(would_be),
        "trust_level": trust,
        "flag_state": flag_state,
        "decided_at": decided_at or _recent_iso(),
    }


def _live_row(attempt_id: str, topic_id: str, delta: float, current: float, would_be: float) -> dict:
    return _shadow_row(attempt_id, topic_id, delta, current, would_be, flag_state="live")


# ---------------------------------------------------------------------------
# Mock attempt_derivation module factory
# ---------------------------------------------------------------------------


def _make_mock_ad(
    replay_map: dict[str, dict[str, str]] | None = None,
    gen_corrections: dict[str, list[dict]] | None = None,
    topic_evidence: dict[str, list[dict]] | None = None,
) -> types.ModuleType:
    """Return a fake attempt_derivation module."""
    ad = types.ModuleType("attempt_derivation")
    rm = replay_map or {}
    gc = gen_corrections or {}
    te = topic_evidence or {}

    def replay_from_persisted_baseline(attempt_id: str) -> dict | None:
        return rm.get(attempt_id, {})

    def derive_attempt_evidence_corrections(attempt_id: str) -> list[dict]:
        return gc.get(attempt_id, [])

    def load_attempt_topic_evidence(attempt_id: str) -> list[dict]:
        return te.get(attempt_id, [])

    ad.replay_from_persisted_baseline = replay_from_persisted_baseline
    ad.derive_attempt_evidence_corrections = derive_attempt_evidence_corrections
    ad.load_attempt_topic_evidence = load_attempt_topic_evidence
    return ad


# ---------------------------------------------------------------------------
# Patch helpers
# ---------------------------------------------------------------------------

import tools.mastery_shadow_analysis.shadow_analysis as sa


def _run(fn: Any, *args: Any, mock_ad: Any = None, sb: Any = None, **kwargs: Any) -> None:
    patches: list[Any] = []
    if mock_ad is not None:
        patches.append(patch.object(sa, "_check_attempt_derivation", return_value=mock_ad))
    if sb is not None:
        patches.append(patch.object(sa, "_get_supabase", return_value=sb))

    def _apply(p_list: list, idx: int = 0) -> None:
        if idx >= len(p_list):
            fn(*args, **kwargs)
            return
        with p_list[idx]:
            _apply(p_list, idx + 1)

    _apply(patches)


# ---------------------------------------------------------------------------
# shadow_replay tests
# ---------------------------------------------------------------------------


def test_sr_empty_window(capsys: Any) -> None:
    """Empty shadow table → INSUFFICIENT_DATA, exit 3."""
    mock_ad = _make_mock_ad()
    sb = SBStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["status"] == "INSUFFICIENT_DATA"
    assert exc.value.code == 3


def test_sr_insufficient_thresholds(capsys: Any) -> None:
    """< 20 attempts or < 50 decisions → INSUFFICIENT_DATA, exit 3."""
    mock_ad = _make_mock_ad(replay_map={"a1": {"t1": "5.0"}})
    rows = [_shadow_row("a1", "t1", 5.0, 50.0, 55.0)]  # only 1 attempt, 1 decision
    sb = SBStub({"mock_mastery_shadow": rows})
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "INSUFFICIENT_DATA"
    assert exc.value.code == 3


def _make_sr_pass_data(n_attempts: int = 25, topics_per: int = 3) -> tuple[dict, SBStub]:
    """Build enough shadow rows + replay_map to reach gate thresholds and PASS."""
    rows = []
    replay_map: dict[str, dict[str, str]] = {}
    for i in range(n_attempts):
        aid = f"attempt-{i}"
        replay_map[aid] = {}
        for j in range(topics_per):
            tid = f"topic-{i}-{j}"
            delta = 3.0 if j % 2 == 0 else -2.0
            current = 50.0
            would_be = min(100.0, max(0.0, current + delta))
            rows.append(_shadow_row(aid, tid, delta, current, would_be))
            replay_map[aid][tid] = str(delta)
    sb = SBStub({"mock_mastery_shadow": rows})
    return replay_map, sb


def test_sr_pass(capsys: Any) -> None:
    """≥ 20 attempts, ≥ 50 decisions, all match → PASS, exit 0."""
    replay_map, sb = _make_sr_pass_data(25, 3)  # 25 attempts × 3 = 75 decisions
    mock_ad = _make_mock_ad(replay_map=replay_map)
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "PASS"
    assert data["exact_match_pct"] == 100.0
    assert data["coverage_pct"] == 100.0
    assert data["mismatch_count"] == 0
    assert exc.value.code == 0


def test_sr_mismatch_causes_fail(capsys: Any) -> None:
    """Any mismatch → FAIL, exit 0 (valid result)."""
    replay_map, sb = _make_sr_pass_data(25, 3)
    # Corrupt one replay value
    first_aid = "attempt-0"
    first_tid = "topic-0-0"
    replay_map[first_aid][first_tid] = "99.0"  # different from shadow's 3.0
    mock_ad = _make_mock_ad(replay_map=replay_map)
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "FAIL"
    assert data["mismatch_count"] >= 1
    assert exc.value.code == 0


def test_sr_missing_topic(capsys: Any) -> None:
    """Shadow has topic not in replay → missing_count > 0 → FAIL."""
    replay_map, sb = _make_sr_pass_data(25, 3)
    # Remove a topic from replay for attempt-0
    del replay_map["attempt-0"]["topic-0-0"]
    mock_ad = _make_mock_ad(replay_map=replay_map)
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["missing_count"] >= 1
    assert data["status"] == "FAIL"
    assert exc.value.code == 0


def test_sr_extra_topic(capsys: Any) -> None:
    """Replay has topic not in shadow → extra_count > 0 → FAIL."""
    replay_map, sb = _make_sr_pass_data(25, 3)
    # Add an extra topic in replay that isn't in shadow
    replay_map["attempt-0"]["extra-topic-not-in-shadow"] = "1.0"
    mock_ad = _make_mock_ad(replay_map=replay_map)
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["extra_count"] >= 1
    assert data["status"] == "FAIL"
    assert exc.value.code == 0


def test_sr_duplicate_shadow_key(capsys: Any) -> None:
    """Duplicate (attempt_id, topic_id, flag_state) → FAIL."""
    replay_map, sb = _make_sr_pass_data(25, 3)
    # Add a duplicate row (different id, same attempt+topic+flag_state)
    dup = dict(_shadow_row("attempt-0", "topic-0-0", 3.0, 50.0, 53.0))
    dup["id"] = "dup-row-id"
    sb.db["mock_mastery_shadow"].append(dup)
    mock_ad = _make_mock_ad(replay_map=replay_map)
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["duplicate_key_count"] >= 1
    assert data["status"] == "FAIL"
    assert exc.value.code == 0


def test_sr_classification_not_ready(capsys: Any) -> None:
    """Attempt where replay raises → classification_not_ready_count > 0 → FAIL."""
    replay_map, sb = _make_sr_pass_data(25, 3)

    def bad_replay(attempt_id: str) -> dict:
        if attempt_id == "attempt-0":
            raise RuntimeError("classification_not_ready")
        return replay_map.get(attempt_id, {})

    ad = _make_mock_ad(replay_map=replay_map)
    ad.replay_from_persisted_baseline = bad_replay
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["classification_not_ready_count"] >= 1
    assert data["status"] == "FAIL"
    assert exc.value.code == 0


def test_sr_invariant_unweighted_cap_violation(capsys: Any) -> None:
    """Row with |unweighted_delta| > 15 → invariant_violations non-empty → exit 4."""
    replay_map, sb = _make_sr_pass_data(25, 3)
    # Add row with unweighted cap violation
    row = _shadow_row("attempt-0", "topic-0-0", 15.0, 50.0, 65.0, unweighted=20.0)
    row["id"] = "cap-violation"
    sb.db["mock_mastery_shadow"].append(row)
    mock_ad = _make_mock_ad(replay_map=replay_map)
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert len(data["invariant_violations"]) >= 1
    assert "proposed_delta_db_unweighted" in data["invariant_violations"][0]
    assert exc.value.code == 4


def test_sr_invariant_clamp_violation(capsys: Any) -> None:
    """Row where would_be ≠ clamp(current + weighted_delta) → invariant violation."""
    replay_map, sb = _make_sr_pass_data(25, 3)
    bad_row = _shadow_row("attempt-0", "topic-0-0", 5.0, 50.0, 99.0)  # 99 != 55
    bad_row["id"] = "clamp-violation"
    sb.db["mock_mastery_shadow"].append(bad_row)
    mock_ad = _make_mock_ad(replay_map=replay_map)
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert any("would_be_mastery_db" in v for v in data["invariant_violations"])
    assert exc.value.code == 4


def test_sr_attempt_id_filter(capsys: Any) -> None:
    """--attempt-id filters to exactly one attempt."""
    rows = [
        _shadow_row("a1", "t1", 5.0, 50.0, 55.0),
        _shadow_row("a2", "t2", 3.0, 40.0, 43.0),
    ]
    replay_map = {"a1": {"t1": "5.0"}}
    sb = SBStub({"mock_mastery_shadow": rows})
    mock_ad = _make_mock_ad(replay_map=replay_map)
    with pytest.raises(SystemExit):
        _run(sa.shadow_replay, 14, attempt_id="a1", output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    # Only a1 rows loaded — a2 filtered out; a2 has no matching attempt_id eq filter
    assert data["distinct_attempt_count"] == 1


def test_sr_from_to_utc_filter(capsys: Any) -> None:
    """--from-utc / --to-utc filters to window."""
    from datetime import datetime, timezone

    past_iso = "2026-01-01T00:00:00+00:00"
    middle_iso = "2026-03-01T00:00:00+00:00"
    future_iso = "2026-12-31T00:00:00+00:00"
    rows = [
        {**_shadow_row("a1", "t1", 5.0, 50.0, 55.0), "decided_at": past_iso, "id": "id1"},
        {**_shadow_row("a2", "t2", 3.0, 40.0, 43.0), "decided_at": middle_iso, "id": "id2"},
    ]
    replay_map = {"a2": {"t2": "3.0"}}
    sb = SBStub({"mock_mastery_shadow": rows})
    mock_ad = _make_mock_ad(replay_map=replay_map)
    # Window: Feb 2026 to Apr 2026 — only a2 qualifies
    with pytest.raises(SystemExit):
        _run(
            sa.shadow_replay,
            14,
            from_utc="2026-02-01T00:00:00+00:00",
            to_utc="2026-04-01T00:00:00+00:00",
            output_json=True,
            mock_ad=mock_ad,
            sb=sb,
        )
    data = json.loads(capsys.readouterr().out)
    assert data["distinct_attempt_count"] == 1


def test_sr_json_schema_complete(capsys: Any) -> None:
    """JSON output contains all required schema fields."""
    mock_ad = _make_mock_ad()
    sb = SBStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit):
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    required = {
        "schema_version", "command", "window_start", "window_end", "status",
        "thresholds", "distinct_attempt_count", "topic_decision_count",
        "exact_match_count", "exact_match_pct", "coverage_pct",
        "answered_topic_count", "shadow_topic_count",
        "missing_count", "missing", "extra_count", "extra",
        "mismatch_count", "mismatches", "duplicate_key_count", "duplicate_keys",
        "classification_not_ready_count", "classification_not_ready",
        "invariant_violations",
    }
    assert required.issubset(set(data))
    assert data["command"] == "shadow_replay"


def test_sr_stdout_valid_json_only(capsys: Any) -> None:
    """stdout is valid JSON and nothing else; logs go to stderr."""
    mock_ad = _make_mock_ad()
    sb = SBStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit):
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    captured = capsys.readouterr()
    json.loads(captured.out)  # must not raise


def test_sr_missing_prerequisite(capsys: Any) -> None:
    """When attempt_derivation module is absent, exits 2 with PREREQUISITE_MISSING."""
    sb = SBStub({"mock_mastery_shadow": []})
    with patch.object(sa, "_check_attempt_derivation", wraps=lambda cmd: _raise_prereq(cmd)):
        with pytest.raises(SystemExit) as exc:
            with patch.object(sa, "_get_supabase", return_value=sb):
                sa.shadow_replay(14, output_json=True)
    assert exc.value.code == 2


def _raise_prereq(cmd: str) -> None:
    sa._emit_result(
        {"schema_version": 1, "command": cmd, "status": "ERROR",
         "error": "PREREQUISITE_MISSING", "detail": "test"},
        output_json=True,
    )
    sys.exit(sa._EXIT_ERROR)


def test_sr_query_error_exits_2(capsys: Any) -> None:
    """DB query failure → ERROR status, exit 2."""
    mock_ad = _make_mock_ad()
    sb = SBFailStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "ERROR"
    assert exc.value.code == 2


def test_sr_zero_write_calls() -> None:
    """shadow_replay makes zero write calls to the DB."""
    mock_ad = _make_mock_ad()
    sb = SBStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit):
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    assert sb.write_calls == []


def test_sr_trust_adjusted_cap_self_reported(capsys: Any) -> None:
    """self_reported row with |weighted_delta| > 4.5 db triggers invariant violation."""
    # self_reported weight = 0.3; cap = 15 * 0.3 = 4.5 db
    # set weighted = 5.0 (> 4.5), unweighted = 5.0 (≤ 15)
    replay_map, sb = _make_sr_pass_data(25, 3)
    bad_row = _shadow_row("attempt-0", "topic-0-0", 5.0, 50.0, 55.0, trust="self_reported", unweighted=5.0)
    bad_row["id"] = "trust-cap-violation"
    sb.db["mock_mastery_shadow"].append(bad_row)
    mock_ad = _make_mock_ad(replay_map=replay_map)
    with pytest.raises(SystemExit) as exc:
        _run(sa.shadow_replay, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert any("trust-adjusted cap" in v for v in data["invariant_violations"])
    assert exc.value.code == 4


# ---------------------------------------------------------------------------
# correction_parity tests
# ---------------------------------------------------------------------------


def test_cp_insufficient_data(capsys: Any) -> None:
    """No shadow attempts → INSUFFICIENT_DATA, exit 3."""
    mock_ad = _make_mock_ad()
    sb = SBStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit) as exc:
        _run(sa.correction_parity, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "INSUFFICIENT_DATA"
    assert exc.value.code == 3


def test_cp_pass(capsys: Any) -> None:
    """Generated == reference → exact_parity_pct = 100 → PASS, exit 0."""
    rows = [_shadow_row(f"a{i}", f"t{i}", 3.0, 50.0, 53.0) for i in range(15)]
    sb = SBStub({"mock_mastery_shadow": rows})

    # Generated: each attempt → (topic_id, "concept_gap")
    gen_corrections = {
        f"a{i}": [{"topic_id": f"t{i}", "category": "concept_gap"}] for i in range(15)
    }
    mock_ad = _make_mock_ad(gen_corrections=gen_corrections)

    # Reference: same → (topic_id, "concept_gap") — mock _build_reference_corrections
    def fake_ref(ad: Any, attempt_id: str) -> list[tuple[str, str]]:
        idx = attempt_id[1:]  # strip "a"
        return [(f"t{idx}", "concept_gap")]

    with patch.object(sa, "_build_reference_corrections", side_effect=fake_ref):
        with pytest.raises(SystemExit) as exc:
            _run(sa.correction_parity, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "PASS"
    assert data["exact_parity_pct"] == 100.0
    assert exc.value.code == 0


def test_cp_fail_divergence(capsys: Any) -> None:
    """Generated diverges from reference → exact_parity_pct < 100 → FAIL, exit 0."""
    rows = [_shadow_row(f"a{i}", f"t{i}", 3.0, 50.0, 53.0) for i in range(15)]
    sb = SBStub({"mock_mastery_shadow": rows})

    # Generated: all → concept_gap
    gen_corrections = {
        f"a{i}": [{"topic_id": f"t{i}", "category": "concept_gap"}] for i in range(15)
    }
    mock_ad = _make_mock_ad(gen_corrections=gen_corrections)

    # Reference: all → memory_gap — divergence from generated
    def fake_ref(ad: Any, attempt_id: str) -> list[tuple[str, str]]:
        idx = attempt_id[1:]
        return [(f"t{idx}", "memory_gap")]

    with patch.object(sa, "_build_reference_corrections", side_effect=fake_ref):
        with pytest.raises(SystemExit) as exc:
            _run(sa.correction_parity, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "FAIL"
    assert data["exact_parity_pct"] is not None
    assert data["exact_parity_pct"] < 100.0
    assert len(data["generated_only"]) > 0 or len(data["reference_only"]) > 0
    assert exc.value.code == 0


def test_cp_json_schema(capsys: Any) -> None:
    """JSON output has all required keys."""
    mock_ad = _make_mock_ad()
    sb = SBStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit):
        _run(sa.correction_parity, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    required = {
        "schema_version", "command", "status", "thresholds",
        "decision_count", "generated_count", "reference_count",
        "intersection_count", "generated_only", "reference_only",
        "exact_parity_pct",
    }
    assert required.issubset(set(data))
    assert data["command"] == "correction_parity"


# ---------------------------------------------------------------------------
# tasks_overlap tests
# ---------------------------------------------------------------------------


def test_tasks_overlap_exits_2(capsys: Any) -> None:
    """tasks_overlap always exits 2 with CROSS_ORIGIN_TOPIC_IDENTITY_UNAVAILABLE."""
    with pytest.raises(SystemExit) as exc:
        sa.tasks_overlap(output_json=True)
    data = json.loads(capsys.readouterr().out)
    assert exc.value.code == 2
    assert data["status"] == "ERROR"
    assert data["error"] == "CROSS_ORIGIN_TOPIC_IDENTITY_UNAVAILABLE"
    assert data["command"] == "tasks_overlap"


def test_tasks_overlap_no_overlap_pct(capsys: Any) -> None:
    """tasks_overlap must NOT emit overlap_pct."""
    with pytest.raises(SystemExit):
        sa.tasks_overlap(output_json=True)
    data = json.loads(capsys.readouterr().out)
    assert "overlap_pct" not in data


def test_tasks_overlap_correction_parity_hint(capsys: Any) -> None:
    """tasks_overlap detail mentions correction-parity."""
    with pytest.raises(SystemExit):
        sa.tasks_overlap(output_json=True)
    data = json.loads(capsys.readouterr().out)
    assert "correction-parity" in data["detail"]


# ---------------------------------------------------------------------------
# live_audit_compare tests
# ---------------------------------------------------------------------------


def test_lac_no_live_rows(capsys: Any) -> None:
    """No flag_state=live rows → INSUFFICIENT_DATA, exit 3."""
    sb = SBStub({"mock_mastery_shadow": [], "user_topic_mastery_audit": []})
    with pytest.raises(SystemExit) as exc:
        with patch.object(sa, "_get_supabase", return_value=sb):
            sa.live_audit_compare(14, output_json=True)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "INSUFFICIENT_DATA"
    assert exc.value.code == 3


def test_lac_uses_flag_state_live(capsys: Any) -> None:
    """live_audit_compare queries flag_state='live', not 'shadow'."""
    # Only live rows; shadow rows should be ignored
    live_rows = [
        _live_row("a1", "t1", 5.0, 50.0, 55.0),
        _live_row("a1", "t2", -3.0, 40.0, 37.0),
    ]
    shadow_rows = [
        _shadow_row("a9", "t9", 5.0, 50.0, 55.0),  # flag_state=shadow — should NOT match
    ]
    sb = SBStub(
        {
            "mock_mastery_shadow": live_rows + shadow_rows,
            "user_topic_mastery_audit": [],
        }
    )
    results: list[dict] = []
    with patch.object(sa, "_get_supabase", return_value=sb):
        with patch.object(sa, "_emit_result", side_effect=lambda r, _oj: results.append(r)):
            with pytest.raises(SystemExit):
                sa.live_audit_compare(14, output_json=True)
    assert results[0]["shadow_rows"] == 2  # only the 2 live rows
    assert results[0]["shadow_rows"] != 3  # the shadow row was not counted


def test_lac_filters_reason_mock_submit() -> None:
    """Only audit rows with reason='mock_submit' are used."""
    live_rows = [_live_row("a1", "t1", 5.0, 50.0, 55.0)]
    audit_rows_all = [
        {"attempt_id": "a1", "topic_id": "t1", "delta_applied_db": 5.0, "reason": "mock_submit"},
        {"attempt_id": "a1", "topic_id": "t2", "delta_applied_db": -3.0, "reason": "rollback"},
    ]
    # Stub only serves reason='mock_submit' rows (query filters by eq)
    sb = SBStub(
        {
            "mock_mastery_shadow": live_rows,
            "user_topic_mastery_audit": [r for r in audit_rows_all if r["reason"] == "mock_submit"],
        }
    )
    results: list[dict] = []
    with patch.object(sa, "_get_supabase", return_value=sb):
        with patch.object(sa, "_emit_result", side_effect=lambda r, _oj: results.append(r)):
            with pytest.raises(SystemExit):
                sa.live_audit_compare(14, output_json=True)
    assert results[0]["matched_with_audit"] == 1


def test_lac_duplicate_audit_detected() -> None:
    """Duplicate audit rows for same (attempt_id, topic_id) are counted."""
    live_rows = [_live_row("a1", "t1", 5.0, 50.0, 55.0)]
    dup_audit = [
        {"attempt_id": "a1", "topic_id": "t1", "delta_applied_db": 5.0, "reason": "mock_submit"},
        {"attempt_id": "a1", "topic_id": "t1", "delta_applied_db": 5.0, "reason": "mock_submit"},
    ]
    sb = SBStub(
        {"mock_mastery_shadow": live_rows, "user_topic_mastery_audit": dup_audit}
    )
    results: list[dict] = []
    with patch.object(sa, "_get_supabase", return_value=sb):
        with patch.object(sa, "_emit_result", side_effect=lambda r, _oj: results.append(r)):
            with pytest.raises(SystemExit):
                sa.live_audit_compare(14, output_json=True)
    assert results[0]["duplicate_audit_count"] == 1


def test_lac_missing_audit_detected() -> None:
    """Shadow live rows not matched in audit → missing_audit_count > 0."""
    live_rows = [
        _live_row("a1", "t1", 5.0, 50.0, 55.0),
        _live_row("a1", "t2", 3.0, 40.0, 43.0),
    ]
    # Audit only has t1, not t2
    audit_rows = [
        {"attempt_id": "a1", "topic_id": "t1", "delta_applied_db": 5.0, "reason": "mock_submit"},
    ]
    sb = SBStub({"mock_mastery_shadow": live_rows, "user_topic_mastery_audit": audit_rows})
    results: list[dict] = []
    with patch.object(sa, "_get_supabase", return_value=sb):
        with patch.object(sa, "_emit_result", side_effect=lambda r, _oj: results.append(r)):
            with pytest.raises(SystemExit):
                sa.live_audit_compare(14, output_json=True)
    assert results[0]["missing_audit_count"] == 1


def test_lac_json_schema(capsys: Any) -> None:
    """live_audit_compare JSON has schema_version and status fields."""
    sb = SBStub({"mock_mastery_shadow": [], "user_topic_mastery_audit": []})
    with pytest.raises(SystemExit):
        with patch.object(sa, "_get_supabase", return_value=sb):
            sa.live_audit_compare(14, output_json=True)
    data = json.loads(capsys.readouterr().out)
    assert "schema_version" in data
    assert "status" in data
    assert "thresholds" in data
    assert data["command"] == "live_audit_compare"


# ---------------------------------------------------------------------------
# Pagination tests
# ---------------------------------------------------------------------------


def test_pagination_3_pages_no_duplicates() -> None:
    """3-page result → all rows collected, no duplicates."""
    rows = [{"id": str(i), "decided_at": "2026-06-01T00:00:00+00:00"} for i in range(25)]
    sb = SBStub({"test_table": rows})
    result = sa._fetch_paginated(
        sb,
        "test_table",
        lambda q: q.gte("decided_at", "2000-01-01"),
        batch_size=10,
        order_by="id",
    )
    assert len(result) == 25
    ids = [r["id"] for r in result]
    assert len(ids) == len(set(ids))  # no duplicates


def test_pagination_exact_batch_boundary() -> None:
    """Exactly batch_size rows → no extra page fetched."""
    rows = [{"id": str(i)} for i in range(10)]
    sb = SBStub({"test_table": rows})
    result = sa._fetch_paginated(sb, "test_table", lambda q: q, batch_size=10)
    assert len(result) == 10


def test_pagination_empty_table() -> None:
    sb = SBStub({"test_table": []})
    result = sa._fetch_paginated(sb, "test_table", lambda q: q, batch_size=100)
    assert result == []


# ---------------------------------------------------------------------------
# Exit code + credential tests
# ---------------------------------------------------------------------------


def test_missing_credentials_exits_2(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.delenv("NEXT_PUBLIC_SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        sa._get_supabase()
    assert exc.value.code == 2
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "ERROR"
    assert data["error"] == "MISSING_CREDENTIALS"


def test_old_env_var_names_rejected(monkeypatch: Any) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://example.com")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    monkeypatch.delenv("NEXT_PUBLIC_SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        sa._get_supabase()
    assert exc.value.code == 2


def test_correct_env_vars_accepted(monkeypatch: Any) -> None:
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_URL", "http://example.com")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "key")
    called: list[tuple] = []

    def fake_create(url: str, key: str) -> SBStub:
        called.append((url, key))
        return SBStub()

    with patch("tools.mastery_shadow_analysis.shadow_analysis.create_client", fake_create):
        sa._get_supabase()

    assert called == [("http://example.com", "key")]


# ---------------------------------------------------------------------------
# --json flag before and after subcommand (argparse)
# ---------------------------------------------------------------------------


def test_json_flag_before_subcommand(monkeypatch: Any) -> None:
    """--json shadow-replay is parsed correctly."""
    import tools.mastery_shadow_analysis.shadow_analysis as _sa

    p = argparse.ArgumentParser(prog="shadow-analysis")
    p.add_argument("--json", dest="output_json", action="store_true")
    sp = p.add_subparsers(dest="cmd")
    sr = sp.add_parser("shadow-replay")
    sr.add_argument("--json", dest="sub_output_json", action="store_true", default=False)
    sr.add_argument("--days", type=int, default=14)
    a = p.parse_args(["--json", "shadow-replay"])
    output_json = a.output_json or getattr(a, "sub_output_json", False)
    assert output_json is True


def test_json_flag_after_subcommand(monkeypatch: Any) -> None:
    """shadow-replay --json is also accepted."""
    import argparse

    p = argparse.ArgumentParser(prog="shadow-analysis")
    p.add_argument("--json", dest="output_json", action="store_true")
    sp = p.add_subparsers(dest="cmd")
    sr = sp.add_parser("shadow-replay")
    sr.add_argument("--json", dest="sub_output_json", action="store_true", default=False)
    sr.add_argument("--days", type=int, default=14)
    a = p.parse_args(["shadow-replay", "--json"])
    output_json = a.output_json or getattr(a, "sub_output_json", False)
    assert output_json is True


# ---------------------------------------------------------------------------
# import argparse needed for the flag tests above
# ---------------------------------------------------------------------------

import argparse
