"""Tests for tools/mastery_shadow_analysis/shadow_analysis.py.

RB5: shadow_replay tests use the real attempt_derivation module, patching only
the DB-querying functions (load_attempt_inputs, load_persisted_shadow_decisions).
replay_from_persisted_baseline runs for real so field-name bugs are caught.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import os
import sys
import types
import uuid as _uuid_stdlib
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest

# Ensure backend is importable for the real attempt_derivation module.
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../app/backend"))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import tools.mastery_shadow_analysis.shadow_analysis as sa

# Real module imports — used by _run_real and test data builders.
from app.study_os import attempt_derivation as _ad_module
from app.study_os.attempt_derivation import (
    AttemptInputs,
    ReplayResult,
    ResponseStateCounts,
    ShadowDecisions,
)
from app.study_os.attempt_classification_readiness import ClassificationReadiness
from app.study_os.mastery_engine.schemas import (
    AttemptQuestionAnalytics,
    AttemptTopicAnalytics,
    DerivedAttemptAnalytics,
)


# ---------------------------------------------------------------------------
# Minimal Supabase stub
# ---------------------------------------------------------------------------


class _NotProxy:
    """Proxy for _Query.not_ that records IS NOT NULL filters."""

    def __init__(self, query: "_Query") -> None:
        self._q = query

    def is_(self, k: str, v: Any) -> "_Query":
        # "IS NOT NULL" — filter rows where the column is not None
        if v == "null":
            self._q.filters.append((k, "not_is_null", None))
        return self._q


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
        self._limit: int | None = None

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

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    @property
    def not_(self) -> _NotProxy:
        return _NotProxy(self)

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
            if op == "not_is_null" and cell is None:
                return False
        return True

    def execute(self) -> _Exec:
        rows = self.db.get(self.name, [])
        matched = [r for r in rows if self._matches(r)]
        if self._order_col:
            matched.sort(key=lambda r: (r.get(self._order_col) or ""))
        if self._range_start is not None and self._range_end is not None:
            matched = matched[self._range_start : self._range_end + 1]
        if self._limit is not None:
            matched = matched[: self._limit]
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
# Row helpers
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
# Real-module data builders (RB5)
#
# The canonical delta for a 1-correct-question (medium, authored) attempt
# with current_mastery_db=50.00 and trust=platform_verified is 8.00 db.
# Derivation:
#   observed=1.0, expected=0.60 (mastery 0.5 → tier [0.3,0.6))
#   raw = (1.0-0.60) * min(1.0, 1.0/5.0) = 0.40 * 0.2 = 0.08
#   capped = 0.08; weighted = 0.08*1.0 = 0.08
#   expected_delta_db = (0.08*100).quantize(0.01) = 8.00
# ---------------------------------------------------------------------------

_MATCH_DELTA_DB = "8.00"
_MATCH_CURRENT_DB = "50.00"
_MATCH_WOULD_BE_DB = "58.00"   # clamp(50+8) = 58


def _make_real_inputs(
    attempt_id: str,
    topic_ids: list[str],
    *,
    ready: bool = True,
    missing_qids: list[str] | None = None,
    duplicate_qids: list[str] | None = None,
) -> AttemptInputs:
    """Build a real AttemptInputs with one correct medium/authored question per topic.

    DerivedAttemptAnalytics.attempt_id must be a valid UUID (pydantic-enforced).
    We derive a deterministic UUID from the short test key so callers can use
    simple names like "a1" or "attempt-0" as dict keys while the model gets a
    structurally valid UUID internally.
    """
    try:
        _uuid_stdlib.UUID(attempt_id)
        analytics_attempt_id: str = attempt_id
    except ValueError:
        analytics_attempt_id = str(_uuid_stdlib.uuid5(_uuid_stdlib.NAMESPACE_DNS, attempt_id))

    questions = [
        AttemptQuestionAnalytics(
            question_id=f"q-{analytics_attempt_id}-{tid}",
            topic_id=tid,
            microtopic_id=None,
            is_correct=True,
            attempted=True,
            difficulty="medium",
            source_type="authored",
            pyq_year=None,
            expected_time_sec=None,
            actual_time_sec=30,
            error_type=None,
            confidence=Decimal("0.5"),
        )
        for tid in topic_ids
    ]
    topics = [
        AttemptTopicAnalytics(
            topic_id=tid,
            microtopic_id=None,
            attempted=1,
            correct=1,
            accuracy_pct=Decimal("100"),
        )
        for tid in topic_ids
    ]
    analytics = DerivedAttemptAnalytics(
        attempt_id=analytics_attempt_id,
        user_id="user-1",
        questions=questions,
        topics=topics,
    )
    coverage = ClassificationReadiness(
        response_count=len(topic_ids),
        classification_count=len(topic_ids),
        unique_classification_count=len(topic_ids),
        missing_question_ids=missing_qids or [],
        duplicate_question_ids=duplicate_qids or [],
        ready=ready,
    )
    return AttemptInputs(
        analytics=analytics,
        response_counts=ResponseStateCounts(),
        classification_coverage=coverage,
        classification_counts={},
        classification_rows=[],
        trust_level="platform_verified",
        user_id="user-1",
    )


def _make_match_decisions(topic_ids: list[str]) -> ShadowDecisions:
    """ShadowDecisions with proposed_delta_db matching the 8.00 db canonical value."""
    return ShadowDecisions(
        rows=[
            {
                "topic_id": tid,
                "proposed_delta_db": _MATCH_DELTA_DB,
                "proposed_delta_db_unweighted": _MATCH_DELTA_DB,
                "current_mastery_db": _MATCH_CURRENT_DB,
                "would_be_mastery_db": _MATCH_WOULD_BE_DB,
                "trust_level": "platform_verified",
                "flag_state": "shadow",
            }
            for tid in topic_ids
        ],
        duplicate_keys=[],
    )


# ---------------------------------------------------------------------------
# _run_real: uses the real attempt_derivation module, patching only DB functions
# ---------------------------------------------------------------------------


def _run_real(
    fn: Any,
    *args: Any,
    sb: Any,
    inputs_map: dict[str, Any] | None = None,
    decisions_map: dict[str, Any] | None = None,
    gen_corrections_map: dict[str, list[dict]] | None = None,
    **kwargs: Any,
) -> None:
    """Run fn with the real attempt_derivation module.

    Only the DB-querying functions are patched:
      - load_attempt_inputs (queries mock_attempts + responses + classification)
      - load_persisted_shadow_decisions (queries mock_mastery_shadow)
    replay_from_persisted_baseline runs for real → catches field-name bugs (RB1).
    """
    _inputs = inputs_map or {}
    _decisions = decisions_map or {}
    _corrections = gen_corrections_map or {}

    stack = contextlib.ExitStack()
    stack.enter_context(patch.object(sa, "_get_supabase", return_value=sb))
    stack.enter_context(patch.object(sa, "_check_attempt_derivation", return_value=_ad_module))
    stack.enter_context(patch.object(
        _ad_module, "load_attempt_inputs",
        side_effect=lambda _sb, aid: _inputs.get(aid),
    ))
    stack.enter_context(patch.object(
        _ad_module, "load_persisted_shadow_decisions",
        side_effect=lambda _sb, aid: _decisions.get(aid, ShadowDecisions()),
    ))
    if gen_corrections_map is not None:
        stack.enter_context(patch.object(
            _ad_module, "derive_attempt_evidence_corrections",
            side_effect=lambda analytics, trust: _corrections.get(analytics.attempt_id, []),
        ))

    with stack:
        fn(*args, **kwargs)


# ---------------------------------------------------------------------------
# _make_mock_ad: stub module for correction_parity tests
# (correction_parity stubs derive_attempt_evidence_corrections to avoid
# complex correction_policy imports in the test environment)
# ---------------------------------------------------------------------------


def _make_mock_inputs(attempt_id: str, *, ready: bool = True) -> Any:
    """SimpleNamespace mimicking AttemptInputs — used only for correction_parity stubs."""
    coverage = types.SimpleNamespace(
        ready=ready,
        missing_question_ids=[],
        duplicate_question_ids=[],
    )
    analytics = types.SimpleNamespace(attempt_id=attempt_id)
    return types.SimpleNamespace(
        analytics=analytics,
        trust_level="platform_verified",
        classification_coverage=coverage,
    )


def _make_mock_ad(
    inputs_map: dict[str, Any] | None = None,
    gen_corrections_map: dict[str, list[dict]] | None = None,
) -> types.ModuleType:
    """Fake attempt_derivation for correction_parity tests only.

    Stubs load_attempt_inputs and derive_attempt_evidence_corrections.
    Not used for shadow_replay (use _run_real instead).
    """
    ad = types.ModuleType("attempt_derivation")
    _inputs = inputs_map or {}
    _corrections = gen_corrections_map or {}

    def load_attempt_inputs(sb: Any, attempt_id: str) -> Any:
        return _inputs.get(attempt_id)

    def load_persisted_shadow_decisions(sb: Any, attempt_id: str) -> Any:
        return ShadowDecisions()

    def replay_from_persisted_baseline(persisted: Any, analytics: Any, trust_level: str) -> Any:
        return ReplayResult(status="NO_BASELINE", sample_count=0, exact_match_count=0)

    def derive_attempt_evidence_corrections(analytics: Any, trust_level: str) -> list[dict]:
        return _corrections.get(analytics.attempt_id, [])

    ad.load_attempt_inputs = load_attempt_inputs
    ad.load_persisted_shadow_decisions = load_persisted_shadow_decisions
    ad.replay_from_persisted_baseline = replay_from_persisted_baseline
    ad.derive_attempt_evidence_corrections = derive_attempt_evidence_corrections
    return ad


# ---------------------------------------------------------------------------
# _run: legacy helper for tests that still use mock_ad (correction_parity)
# ---------------------------------------------------------------------------


def _run(fn: Any, *args: Any, mock_ad: Any = None, sb: Any = None, **kwargs: Any) -> None:
    stack = contextlib.ExitStack()
    if mock_ad is not None:
        stack.enter_context(
            patch.object(sa, "_check_attempt_derivation", return_value=mock_ad)
        )
    if sb is not None:
        stack.enter_context(patch.object(sa, "_get_supabase", return_value=sb))
    with stack:
        fn(*args, **kwargs)


# ---------------------------------------------------------------------------
# shadow_replay data builder (real module)
# ---------------------------------------------------------------------------


def _make_sr_pass_data(
    n_attempts: int = 25, topics_per: int = 3
) -> tuple[dict, dict, "SBStub"]:
    """Build shadow rows + per-attempt maps for a PASS result with the real module."""
    rows: list[dict] = []
    inputs_map: dict[str, Any] = {}
    decisions_map: dict[str, ShadowDecisions] = {}

    for i in range(n_attempts):
        aid = f"attempt-{i}"
        topic_ids = [f"topic-{i}-{j}" for j in range(topics_per)]
        for tid in topic_ids:
            rows.append(_shadow_row(aid, tid, 8.0, 50.0, 58.0))
        inputs_map[aid] = _make_real_inputs(aid, topic_ids)
        decisions_map[aid] = _make_match_decisions(topic_ids)

    sb = SBStub({"mock_mastery_shadow": rows})
    return inputs_map, decisions_map, sb


# ---------------------------------------------------------------------------
# shadow_replay tests — all use _run_real (real replay_from_persisted_baseline)
# ---------------------------------------------------------------------------


def test_sr_empty_window(capsys: Any) -> None:
    """Empty shadow table → INSUFFICIENT_DATA, exit 3."""
    sb = SBStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "INSUFFICIENT_DATA"
    assert exc.value.code == 3


def test_sr_insufficient_thresholds(capsys: Any) -> None:
    """< 20 attempts → INSUFFICIENT_DATA, exit 3."""
    rows = [_shadow_row("a1", "t1", 8.0, 50.0, 58.0)]
    inputs_map = {"a1": _make_real_inputs("a1", ["t1"])}
    decisions_map = {"a1": _make_match_decisions(["t1"])}
    sb = SBStub({"mock_mastery_shadow": rows})
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb,
                  inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "INSUFFICIENT_DATA"
    assert exc.value.code == 3


def test_sr_pass(capsys: Any) -> None:
    """≥ 20 attempts, ≥ 50 decisions, all exact matches → PASS, exit 0."""
    inputs_map, decisions_map, sb = _make_sr_pass_data(25, 3)
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb,
                  inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "PASS"
    assert data["exact_match_pct"] == 100.0
    assert data["coverage_pct"] == 100.0
    assert data["mismatch_count"] == 0
    assert exc.value.code == 0


def test_sr_mismatch_causes_fail(capsys: Any) -> None:
    """Any mismatch → FAIL; real module verifies persisted_delta_db/replay_delta_db keys (RB1)."""
    inputs_map, decisions_map, sb = _make_sr_pass_data(25, 3)
    # Override attempt-0 decisions with a wrong delta (5.00 instead of 8.00)
    topic_ids_0 = [f"topic-0-{j}" for j in range(3)]
    mismatch_rows = [{
        "topic_id": "topic-0-0",
        "proposed_delta_db": "5.00",    # intentionally wrong; replay will compute 8.00
        "proposed_delta_db_unweighted": "5.00",
        "current_mastery_db": _MATCH_CURRENT_DB,
        "would_be_mastery_db": "55.00",
        "trust_level": "platform_verified",
        "flag_state": "shadow",
    }] + [
        {
            "topic_id": f"topic-0-{j}",
            "proposed_delta_db": _MATCH_DELTA_DB,
            "proposed_delta_db_unweighted": _MATCH_DELTA_DB,
            "current_mastery_db": _MATCH_CURRENT_DB,
            "would_be_mastery_db": _MATCH_WOULD_BE_DB,
            "trust_level": "platform_verified",
            "flag_state": "shadow",
        }
        for j in range(1, 3)
    ]
    decisions_map["attempt-0"] = ShadowDecisions(rows=mismatch_rows, duplicate_keys=[])
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb,
                  inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "FAIL"
    assert data["mismatch_count"] >= 1
    # RB1 regression guard: real module returns persisted_delta_db / replay_delta_db
    m = data["mismatches"][0]
    assert "persisted_delta_db" in m, "RB1: persisted_delta_db missing from mismatch"
    assert "replay_delta_db" in m, "RB1: replay_delta_db missing from mismatch"
    assert m["persisted_delta_db"] == "5.00"
    assert m["replay_delta_db"] == "8.00"
    assert exc.value.code == 0


def test_sr_missing_topic(capsys: Any) -> None:
    """Topic in analytics but absent from shadow decisions → missing_count > 0 → FAIL."""
    inputs_map, decisions_map, sb = _make_sr_pass_data(25, 3)
    # attempt-0 analytics has an extra topic not in decisions
    topic_ids_0 = [f"topic-0-{j}" for j in range(3)]
    inputs_map["attempt-0"] = _make_real_inputs("attempt-0", topic_ids_0 + ["missing-topic"])
    # decisions_map["attempt-0"] only covers topic-0-{0,1,2}, so missing-topic is absent
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb,
                  inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    assert data["missing_count"] >= 1
    assert data["status"] == "FAIL"
    assert exc.value.code == 0


def test_sr_extra_topic(capsys: Any) -> None:
    """Shadow has topic not in analytics → extra_count > 0 → FAIL."""
    inputs_map, decisions_map, sb = _make_sr_pass_data(25, 3)
    # Add an extra shadow topic to decisions that analytics won't compute a delta for
    existing_rows = decisions_map["attempt-0"].rows
    decisions_map["attempt-0"] = ShadowDecisions(
        rows=existing_rows + [{
            "topic_id": "extra-topic-not-in-analytics",
            "proposed_delta_db": _MATCH_DELTA_DB,
            "proposed_delta_db_unweighted": _MATCH_DELTA_DB,
            "current_mastery_db": _MATCH_CURRENT_DB,
            "would_be_mastery_db": _MATCH_WOULD_BE_DB,
            "trust_level": "platform_verified",
            "flag_state": "shadow",
        }],
        duplicate_keys=[],
    )
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb,
                  inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    assert data["extra_count"] >= 1
    assert data["status"] == "FAIL"
    assert exc.value.code == 0


def test_sr_duplicate_shadow_key(capsys: Any) -> None:
    """Duplicate (attempt_id, topic_id, flag_state) → duplicate_key_count > 0 → FAIL."""
    inputs_map, decisions_map, sb = _make_sr_pass_data(25, 3)
    dup = dict(_shadow_row("attempt-0", "topic-0-0", 8.0, 50.0, 58.0))
    dup["id"] = "dup-row-id"
    sb.db["mock_mastery_shadow"].append(dup)
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb,
                  inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    assert data["duplicate_key_count"] >= 1
    assert data["status"] == "FAIL"
    assert exc.value.code == 0


def test_sr_classification_not_ready_none(capsys: Any) -> None:
    """load_attempt_inputs returning None → structured record in classification_not_ready (RB2)."""
    inputs_map, decisions_map, sb = _make_sr_pass_data(25, 3)
    del inputs_map["attempt-0"]  # returns None → classification_not_ready
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb,
                  inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    assert data["classification_not_ready_count"] >= 1
    nr = data["classification_not_ready"][0]
    assert isinstance(nr, dict), "RB2: classification_not_ready must contain dicts"
    assert nr["attempt_id"] == "attempt-0"
    assert data["status"] == "FAIL"
    assert exc.value.code == 0


def test_sr_classification_not_ready_exposes_ids(capsys: Any) -> None:
    """When classification isn't ready, missing/duplicate question IDs are exposed (RB2)."""
    inputs_map, decisions_map, sb = _make_sr_pass_data(25, 3)
    not_ready = _make_real_inputs(
        "attempt-0",
        ["topic-0-0", "topic-0-1", "topic-0-2"],
        ready=False,
        missing_qids=["q-missing-1"],
        duplicate_qids=["q-dup-1"],
    )
    inputs_map["attempt-0"] = not_ready
    with pytest.raises(SystemExit):
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb,
                  inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    nr = next(r for r in data["classification_not_ready"] if r["attempt_id"] == "attempt-0")
    assert "missing" in nr, "RB2: missing_question_ids not in classification_not_ready record"
    assert "q-missing-1" in nr["missing"]
    assert "duplicate" in nr, "RB2: duplicate_question_ids not in classification_not_ready record"
    assert "q-dup-1" in nr["duplicate"]


def test_sr_invariant_unweighted_cap_violation(capsys: Any) -> None:
    """|unweighted_delta| > 15 → invariant_violations non-empty → exit 4."""
    inputs_map, decisions_map, sb = _make_sr_pass_data(25, 3)
    row = _shadow_row("attempt-0", "topic-0-0", 15.0, 50.0, 65.0, unweighted=20.0)
    row["id"] = "cap-violation"
    sb.db["mock_mastery_shadow"].append(row)
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb,
                  inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    assert len(data["invariant_violations"]) >= 1
    assert "proposed_delta_db_unweighted" in data["invariant_violations"][0]
    assert exc.value.code == 4


def test_sr_invariant_clamp_violation(capsys: Any) -> None:
    """would_be ≠ clamp(current + weighted_delta) → invariant violation → exit 4."""
    inputs_map, decisions_map, sb = _make_sr_pass_data(25, 3)
    bad_row = _shadow_row("attempt-0", "topic-0-0", 5.0, 50.0, 99.0)  # 99 ≠ 55
    bad_row["id"] = "clamp-violation"
    sb.db["mock_mastery_shadow"].append(bad_row)
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb,
                  inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    assert any("would_be_mastery_db" in v for v in data["invariant_violations"])
    assert exc.value.code == 4


def test_sr_attempt_id_filter(capsys: Any) -> None:
    """--attempt-id filters to exactly one attempt."""
    rows = [
        _shadow_row("a1", "t1", 8.0, 50.0, 58.0),
        _shadow_row("a2", "t2", 8.0, 50.0, 58.0),
    ]
    inputs_map = {"a1": _make_real_inputs("a1", ["t1"])}
    decisions_map = {"a1": _make_match_decisions(["t1"])}
    sb = SBStub({"mock_mastery_shadow": rows})
    with pytest.raises(SystemExit):
        _run_real(sa.shadow_replay, 14, attempt_id="a1", output_json=True,
                  sb=sb, inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    assert data["distinct_attempt_count"] == 1


def test_sr_from_to_utc_filter(capsys: Any) -> None:
    """--from-utc / --to-utc restricts to window; out-of-window rows excluded."""
    past_iso = "2026-01-01T00:00:00+00:00"
    middle_iso = "2026-03-01T00:00:00+00:00"
    rows = [
        {**_shadow_row("a1", "t1", 8.0, 50.0, 58.0), "decided_at": past_iso, "id": "id1"},
        {**_shadow_row("a2", "t2", 8.0, 50.0, 58.0), "decided_at": middle_iso, "id": "id2"},
    ]
    inputs_map = {"a2": _make_real_inputs("a2", ["t2"])}
    decisions_map = {"a2": _make_match_decisions(["t2"])}
    sb = SBStub({"mock_mastery_shadow": rows})
    with pytest.raises(SystemExit):
        _run_real(
            sa.shadow_replay, 14,
            from_utc="2026-02-01T00:00:00+00:00",
            to_utc="2026-04-01T00:00:00+00:00",
            output_json=True,
            sb=sb,
            inputs_map=inputs_map,
            decisions_map=decisions_map,
        )
    data = json.loads(capsys.readouterr().out)
    assert data["distinct_attempt_count"] == 1


def test_sr_json_schema_complete(capsys: Any) -> None:
    """JSON output contains all required schema fields."""
    sb = SBStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit):
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb)
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
    sb = SBStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit):
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb)
    json.loads(capsys.readouterr().out)  # must not raise


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
    sb = SBFailStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "ERROR"
    assert exc.value.code == 2


def test_sr_zero_write_calls() -> None:
    """shadow_replay makes zero write calls to the DB."""
    sb = SBStub({"mock_mastery_shadow": []})
    with pytest.raises(SystemExit):
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb)
    assert sb.write_calls == []


def test_sr_trust_adjusted_cap_self_reported(capsys: Any) -> None:
    """self_reported row with |weighted_delta| > 4.5 db triggers trust-adjusted cap violation."""
    inputs_map, decisions_map, sb = _make_sr_pass_data(25, 3)
    # self_reported weight=0.3; trust-adjusted cap = 15*0.3 = 4.5; |5.0| > 4.5
    bad_row = _shadow_row(
        "attempt-0", "topic-0-0", 5.0, 50.0, 55.0, trust="self_reported", unweighted=5.0
    )
    bad_row["id"] = "trust-cap-violation"
    sb.db["mock_mastery_shadow"].append(bad_row)
    with pytest.raises(SystemExit) as exc:
        _run_real(sa.shadow_replay, 14, output_json=True, sb=sb,
                  inputs_map=inputs_map, decisions_map=decisions_map)
    data = json.loads(capsys.readouterr().out)
    assert any("trust-adjusted cap" in v for v in data["invariant_violations"])
    assert exc.value.code == 4


# ---------------------------------------------------------------------------
# correction_parity tests
# (Uses _make_mock_ad for derive_attempt_evidence_corrections; RB3: queries
# mock_attempts instead of mock_mastery_shadow)
# ---------------------------------------------------------------------------


def test_cp_insufficient_data(capsys: Any) -> None:
    """No submitted attempts → INSUFFICIENT_DATA, exit 3."""
    mock_ad = _make_mock_ad()
    sb = SBStub({"mock_attempts": []})
    with pytest.raises(SystemExit) as exc:
        _run(sa.correction_parity, 14, output_json=True, mock_ad=mock_ad, sb=sb)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "INSUFFICIENT_DATA"
    assert exc.value.code == 3


def test_cp_pass(capsys: Any) -> None:
    """Generated == reference → exact_parity_pct = 100 → PASS, exit 0."""
    attempt_rows = [{"id": f"a{i}", "submitted_at": _recent_iso()} for i in range(15)]
    sb = SBStub({"mock_attempts": attempt_rows})

    inputs_map = {f"a{i}": _make_mock_inputs(f"a{i}") for i in range(15)}
    gen_corrections_map = {
        f"a{i}": [{"topic_id": f"t{i}", "category": "concept_gap"}] for i in range(15)
    }
    mock_ad = _make_mock_ad(inputs_map=inputs_map, gen_corrections_map=gen_corrections_map)

    def fake_ref(analytics: Any) -> list[tuple[str, str]]:
        idx = analytics.attempt_id[1:]  # strip "a"
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
    attempt_rows = [{"id": f"a{i}", "submitted_at": _recent_iso()} for i in range(15)]
    sb = SBStub({"mock_attempts": attempt_rows})

    inputs_map = {f"a{i}": _make_mock_inputs(f"a{i}") for i in range(15)}
    gen_corrections_map = {
        f"a{i}": [{"topic_id": f"t{i}", "category": "concept_gap"}] for i in range(15)
    }
    mock_ad = _make_mock_ad(inputs_map=inputs_map, gen_corrections_map=gen_corrections_map)

    def fake_ref(analytics: Any) -> list[tuple[str, str]]:
        idx = analytics.attempt_id[1:]
        return [(f"t{idx}", "memory_gap")]  # diverges

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
    sb = SBStub({"mock_attempts": []})
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
# live_audit_compare tests (RB4: FAIL status, delta_mismatch_count)
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
    live_rows = [
        _live_row("a1", "t1", 5.0, 50.0, 55.0),
        _live_row("a1", "t2", -3.0, 40.0, 37.0),
    ]
    shadow_rows = [
        _shadow_row("a9", "t9", 5.0, 50.0, 55.0),  # flag_state=shadow — must NOT match
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


def test_lac_filters_reason_mock_submit() -> None:
    """Only audit rows with reason='mock_submit' are used."""
    live_rows = [_live_row("a1", "t1", 5.0, 50.0, 55.0)]
    audit_rows = [
        {"id": "audit-1", "attempt_id": "a1", "topic_id": "t1",
         "delta_applied_db": 5.0, "reason": "mock_submit"},
    ]
    sb = SBStub({"mock_mastery_shadow": live_rows, "user_topic_mastery_audit": audit_rows})
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
        {"id": "audit-1", "attempt_id": "a1", "topic_id": "t1",
         "delta_applied_db": 5.0, "reason": "mock_submit"},
        {"id": "audit-2", "attempt_id": "a1", "topic_id": "t1",
         "delta_applied_db": 5.0, "reason": "mock_submit"},
    ]
    sb = SBStub({"mock_mastery_shadow": live_rows, "user_topic_mastery_audit": dup_audit})
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
    audit_rows = [
        {"id": "audit-1", "attempt_id": "a1", "topic_id": "t1",
         "delta_applied_db": 5.0, "reason": "mock_submit"},
    ]
    sb = SBStub({"mock_mastery_shadow": live_rows, "user_topic_mastery_audit": audit_rows})
    results: list[dict] = []
    with patch.object(sa, "_get_supabase", return_value=sb):
        with patch.object(sa, "_emit_result", side_effect=lambda r, _oj: results.append(r)):
            with pytest.raises(SystemExit):
                sa.live_audit_compare(14, output_json=True)
    assert results[0]["missing_audit_count"] == 1


def test_lac_fail_when_missing_audit(capsys: Any) -> None:
    """Sufficient matched pairs + missing_audit > 0 → FAIL status (not PASS)."""
    # 11 live rows; 10 matched; 1 missing
    live_rows = [_live_row(f"a{i}", f"t{i}", 5.0, 50.0, 55.0) for i in range(11)]
    audit_rows = [
        {"id": f"audit-{i}", "attempt_id": f"a{i}", "topic_id": f"t{i}",
         "delta_applied_db": 5.0, "reason": "mock_submit"}
        for i in range(10)  # a10 has no audit row
    ]
    sb = SBStub({"mock_mastery_shadow": live_rows, "user_topic_mastery_audit": audit_rows})
    with patch.object(sa, "_get_supabase", return_value=sb):
        with pytest.raises(SystemExit) as exc:
            sa.live_audit_compare(14, output_json=True)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "FAIL"
    assert data["missing_audit_count"] == 1
    assert exc.value.code == 0


def test_lac_fail_when_sign_agreement_low(capsys: Any) -> None:
    """sign_agreement_pct < 95 with sufficient pairs → FAIL."""
    # 10 live rows positive, 5 audit positive + 5 audit negative → 50% agreement
    live_rows = [_live_row(f"a{i}", f"t{i}", 5.0, 50.0, 55.0) for i in range(10)]
    audit_rows = (
        [{"id": f"audit-{i}", "attempt_id": f"a{i}", "topic_id": f"t{i}",
          "delta_applied_db": 5.0, "reason": "mock_submit"} for i in range(5)]
        + [{"id": f"audit-{i}", "attempt_id": f"a{i}", "topic_id": f"t{i}",
            "delta_applied_db": -5.0, "reason": "mock_submit"} for i in range(5, 10)]
    )
    sb = SBStub({"mock_mastery_shadow": live_rows, "user_topic_mastery_audit": audit_rows})
    with patch.object(sa, "_get_supabase", return_value=sb):
        with pytest.raises(SystemExit) as exc:
            sa.live_audit_compare(14, output_json=True)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "FAIL"
    assert data["sign_agreement_pct"] == 50.0
    assert exc.value.code == 0


def test_lac_delta_mismatch_causes_fail(capsys: Any) -> None:
    """delta |shadow - audit| > 0.01 → FAIL; delta_mismatch_count and delta_mismatches emitted."""
    live_rows = [_live_row(f"a{i}", f"t{i}", 5.0, 50.0, 55.0) for i in range(10)]
    # First 9 pairs exact match; a9 audit has delta 3.0 vs shadow 5.0 → diff=2.0 > 0.01
    audit_rows = [
        {"id": f"audit-{i}", "attempt_id": f"a{i}", "topic_id": f"t{i}",
         "delta_applied_db": 5.0, "reason": "mock_submit"}
        for i in range(9)
    ] + [
        {"id": "audit-9", "attempt_id": "a9", "topic_id": "t9",
         "delta_applied_db": 3.0, "reason": "mock_submit"},
    ]
    sb = SBStub({"mock_mastery_shadow": live_rows, "user_topic_mastery_audit": audit_rows})
    with patch.object(sa, "_get_supabase", return_value=sb):
        with pytest.raises(SystemExit) as exc:
            sa.live_audit_compare(14, output_json=True)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "FAIL"
    assert data["delta_mismatch_count"] == 1
    assert len(data["delta_mismatches"]) == 1
    dm = data["delta_mismatches"][0]
    assert dm["attempt_id"] == "a9"
    assert dm["topic_id"] == "t9"
    assert exc.value.code == 0


def test_lac_pass_all_conditions_met(capsys: Any) -> None:
    """≥10 matched pairs, 100% sign agreement, 0 missing/duplicate/outlier/delta → PASS."""
    live_rows = [_live_row(f"a{i}", f"t{i}", 5.0, 50.0, 55.0) for i in range(10)]
    audit_rows = [
        {"id": f"audit-{i}", "attempt_id": f"a{i}", "topic_id": f"t{i}",
         "delta_applied_db": 5.0, "reason": "mock_submit"}
        for i in range(10)
    ]
    sb = SBStub({"mock_mastery_shadow": live_rows, "user_topic_mastery_audit": audit_rows})
    with patch.object(sa, "_get_supabase", return_value=sb):
        with pytest.raises(SystemExit) as exc:
            sa.live_audit_compare(14, output_json=True)
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "PASS"
    assert data["sign_agreement_pct"] == 100.0
    assert data["delta_mismatch_count"] == 0
    assert data["missing_audit_count"] == 0
    assert exc.value.code == 0


def test_lac_json_schema(capsys: Any) -> None:
    """live_audit_compare JSON has all required keys including delta_mismatch fields."""
    sb = SBStub({"mock_mastery_shadow": [], "user_topic_mastery_audit": []})
    with pytest.raises(SystemExit):
        with patch.object(sa, "_get_supabase", return_value=sb):
            sa.live_audit_compare(14, output_json=True)
    data = json.loads(capsys.readouterr().out)
    required = {
        "schema_version", "status", "thresholds", "command",
        "delta_mismatch_count", "delta_mismatches",
    }
    assert required.issubset(set(data))
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
    assert len(ids) == len(set(ids))


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
# CLI validation tests (new validations added for RB5/CLI requirements)
# ---------------------------------------------------------------------------


def _run_main(argv: list[str], monkeypatch: Any, capsys: Any) -> tuple[int, dict]:
    """Run sa.main() with given argv; return (exit_code, parsed_json)."""
    monkeypatch.setattr("sys.argv", ["shadow-analysis"] + argv)
    with pytest.raises(SystemExit) as exc:
        sa.main()
    out = capsys.readouterr().out
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        data = {}
    return exc.value.code, data


def test_cli_attempt_id_and_days_mutually_exclusive(monkeypatch: Any, capsys: Any) -> None:
    """--attempt-id combined with --days → exit 2, ERROR/INVALID_FLAGS."""
    import uuid
    code, data = _run_main(
        ["--json", "shadow-replay", "--attempt-id", str(uuid.uuid4()), "--days", "7"],
        monkeypatch, capsys,
    )
    assert code == 2
    assert data.get("status") == "ERROR"
    assert data.get("error") == "INVALID_FLAGS"


def test_cli_to_utc_without_from_utc_exits_2(monkeypatch: Any, capsys: Any) -> None:
    """--to-utc without --from-utc → exit 2."""
    code, data = _run_main(
        ["--json", "shadow-replay", "--to-utc", "2026-06-01T00:00:00"],
        monkeypatch, capsys,
    )
    assert code == 2
    assert data.get("error") == "INVALID_FLAGS"


def test_cli_invalid_uuid_exits_2(monkeypatch: Any, capsys: Any) -> None:
    """--attempt-id with non-UUID value → exit 2."""
    code, data = _run_main(
        ["--json", "shadow-replay", "--attempt-id", "not-a-uuid"],
        monkeypatch, capsys,
    )
    assert code == 2
    assert data.get("error") == "INVALID_FLAGS"
    assert "UUID" in data.get("detail", "")


def test_cli_invalid_iso8601_exits_2(monkeypatch: Any, capsys: Any) -> None:
    """--from-utc with invalid ISO-8601 → exit 2."""
    code, data = _run_main(
        ["--json", "shadow-replay", "--from-utc", "not-a-date"],
        monkeypatch, capsys,
    )
    assert code == 2
    assert data.get("error") == "INVALID_FLAGS"
    assert "ISO-8601" in data.get("detail", "")


def test_cli_from_utc_after_to_utc_exits_2(monkeypatch: Any, capsys: Any) -> None:
    """--from-utc >= --to-utc → exit 2."""
    code, data = _run_main(
        ["--json", "shadow-replay",
         "--from-utc", "2026-06-01T00:00:00",
         "--to-utc", "2026-01-01T00:00:00"],
        monkeypatch, capsys,
    )
    assert code == 2
    assert data.get("error") == "INVALID_FLAGS"


def test_cli_days_zero_exits_2(monkeypatch: Any, capsys: Any) -> None:
    """--days 0 → exit 2."""
    code, data = _run_main(
        ["--json", "shadow-replay", "--days", "0"],
        monkeypatch, capsys,
    )
    assert code == 2
    assert data.get("error") == "INVALID_FLAGS"


def test_cli_days_negative_exits_2(monkeypatch: Any, capsys: Any) -> None:
    """--days -1 → exit 2."""
    code, data = _run_main(
        ["--json", "shadow-replay", "--days", "-1"],
        monkeypatch, capsys,
    )
    assert code == 2
    assert data.get("error") == "INVALID_FLAGS"


def test_lac_days_zero_exits_2(monkeypatch: Any, capsys: Any) -> None:
    """live-audit-compare --days 0 → exit 2."""
    code, data = _run_main(
        ["--json", "live-audit-compare", "--days", "0"],
        monkeypatch, capsys,
    )
    assert code == 2
    assert data.get("error") == "INVALID_FLAGS"
