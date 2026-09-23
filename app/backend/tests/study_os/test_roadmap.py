"""ROADMAP-01 — syllabus roadmap derivation and endpoint.

Pure derivation is tested with ``now`` fixed. The loader and the endpoint run
against the in-memory Supabase stub through the REAL
``load_scoped_coverage_checked`` so elective scoping is exercised, not mocked.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import study_os as study_os_api
from app.api.canonical import TASK_STATES
from app.core.auth import get_current_user
from app.exam_intelligence.lookup import invalidate_exam_lookup_cache
from app.study_os import roadmap, roadmap_thresholds
from app.study_os.report_cards import _HIGH_YIELD_MASTERED_THRESHOLD
from app.study_os.roadmap import RoadmapInputs, derive_roadmap
from tests.persona_questions._stub import SBStub

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _clear_exam_cache():
    invalidate_exam_lookup_cache()
    yield
    invalidate_exam_lookup_cache()


# ─── pure-derivation helpers ────────────────────────────────────────────────


def _node(tid: str, *, subject: str = "s-1", parent: str | None = None, name: str | None = None) -> dict:
    return {"id": tid, "name": name or tid, "subject_id": subject, "parent_topic_id": parent, "level": None}


def _audit(tid: str, n: int, *, last: datetime = NOW, score: float = 60.0, same_attempt: bool = False) -> list[dict]:
    return [
        {
            "id": f"a-{tid}-{i}",
            "topic_id": tid,
            "attempt_id": "att-same" if same_attempt else f"att-{tid}-{i}",
            "after_mastery_db": score,
            "at": (last - timedelta(days=n - 1 - i)).isoformat(),
        }
        for i in range(n)
    ]


def _mastery(tid: str, score: float, *, exam: str = "e-1", updated: datetime = NOW, rid: str | None = None) -> dict:
    return {"id": rid or f"m-{tid}-{exam}", "topic_id": tid, "exam_id": exam,
            "mastery_score": score, "updated_at": updated.isoformat()}


def _derive(nodes, *, mastery=(), audit=(), tasks=(), coverage=None) -> list[dict]:
    node_map = {n["id"]: n for n in nodes}
    cov = coverage if coverage is not None else {n["id"]: {"comparable_priority": 50} for n in nodes}
    inputs = RoadmapInputs(
        nodes=node_map,
        coverage_by_topic=cov,
        subject_names={n["subject_id"]: f"Subject {n['subject_id']}" for n in nodes},
        mastery_rows=list(mastery),
        audit_rows=list(audit),
        task_rows=list(tasks),
    )
    return derive_roadmap(inputs, now=NOW)


def _macro(out, tid) -> dict:
    for s in out:
        for m in s["macros"]:
            if m["topic_id"] == tid:
                return m
    raise AssertionError(f"{tid} not a macro")


def _one(score: float, attempts: int, *, last: datetime = NOW) -> dict:
    out = _derive([_node("t")], mastery=[_mastery("t", score)], audit=_audit("t", attempts, last=last))
    return _macro(out, "t")


# ─── thresholds ─────────────────────────────────────────────────────────────


def test_mastered_at_matches_report_card_threshold():
    # Drift guard: "mastered" must mean the same on the roadmap and report card.
    assert roadmap_thresholds.MASTERED_AT == _HIGH_YIELD_MASTERED_THRESHOLD


def test_threshold_values():
    assert (roadmap_thresholds.WEAK_BELOW, roadmap_thresholds.MASTERED_AT,
            roadmap_thresholds.MIN_ATTEMPTS, roadmap_thresholds.REVISE_AFTER_DAYS,
            roadmap_thresholds.HISTORY_POINTS) == (50.0, 75.0, 2, 14, 10)


def test_completed_status_is_the_task_enum_value():
    assert roadmap.TASK_COMPLETED in TASK_STATES


def test_weak_edge():
    assert _one(49.99, 2)["weak"] is True
    assert _one(50.00, 2)["weak"] is False


def test_mastered_edge():
    assert _one(74.99, 2)["state"] == "studied"
    assert _one(75.00, 2)["state"] == "mastered"


def test_attempts_edge_for_weak_and_mastered():
    assert _one(40.0, 1)["weak"] is False
    assert _one(40.0, 2)["weak"] is True
    assert _one(90.0, 1)["state"] == "studied"
    assert _one(90.0, 2)["state"] == "mastered"


def test_mastered_with_one_attempt_is_studied():
    m = _one(95.0, 1)
    assert m["state"] == "studied" and m["weak"] is False and m["revise"] is False


def test_revise_edge_at_14_vs_15_days():
    assert _one(80.0, 2, last=NOW - timedelta(days=14))["revise"] is False
    assert _one(80.0, 2, last=NOW - timedelta(days=15))["revise"] is True
    # Only a mastered topic can be flagged for revision.
    assert _one(60.0, 2, last=NOW - timedelta(days=40))["revise"] is False


def test_single_attempt_at_the_35_floor_is_studied_not_weak():
    m = _one(35.00, 1)
    assert (m["state"], m["weak"], m["revise"]) == ("studied", False, False)
    assert m["score"] == 35.0 and m["attempts"] == 1


def test_not_started_without_evidence_and_studied_from_a_task():
    out = _derive([_node("a"), _node("b")], tasks=[{"id": "k1", "topic_id": "b"}])
    assert _macro(out, "a")["state"] == "not_started"
    assert _macro(out, "b")["state"] == "studied"
    assert _macro(out, "b")["completed_tasks"] == 1


# ─── attempts / history ─────────────────────────────────────────────────────


def test_attempts_count_distinct_attempt_ids():
    out = _derive([_node("t")], mastery=[_mastery("t", 60)], audit=_audit("t", 2, same_attempt=True))
    assert _macro(out, "t")["attempts"] == 1


def test_history_is_last_points_ascending():
    out = _derive([_node("t")], mastery=[_mastery("t", 60)], audit=_audit("t", 13))
    hist = _macro(out, "t")["history"]
    assert len(hist) == roadmap_thresholds.HISTORY_POINTS
    assert [h["at"] for h in hist] == sorted(h["at"] for h in hist)
    assert _macro(out, "t")["last_practiced"] == hist[-1]["at"]


# ─── macro score source ─────────────────────────────────────────────────────


def test_macro_score_from_own_row():
    nodes = [_node("M"), _node("c1", parent="M")]
    out = _derive(nodes, mastery=[_mastery("M", 62.5), _mastery("c1", 10)], audit=_audit("c1", 3))
    assert _macro(out, "M")["score"] == 62.5


def test_macro_score_from_children_attempts_weighted():
    nodes = [_node("M"), _node("c1", parent="M"), _node("c2", parent="M")]
    out = _derive(
        nodes,
        mastery=[_mastery("c1", 40.0), _mastery("c2", 80.0)],
        audit=_audit("c1", 1) + _audit("c2", 3),
    )
    # (40*1 + 80*3) / 4 = 70
    assert _macro(out, "M")["score"] == 70.0


def test_macro_score_none_without_rows():
    nodes = [_node("M"), _node("c1", parent="M")]
    out = _derive(nodes)
    assert _macro(out, "M")["score"] is None


def test_micro_never_carries_score_attempts_or_flags():
    nodes = [_node("M"), _node("c1", parent="M")]
    out = _derive(nodes, mastery=[_mastery("c1", 90)], audit=_audit("c1", 5),
                  tasks=[{"id": "k", "topic_id": "c1"}])
    [micro] = _macro(out, "M")["micros"]
    assert set(micro) == {"topic_id", "name", "state", "completed_tasks",
                          "is_high_yield", "predictability_band"}
    assert micro["state"] == "studied" and micro["completed_tasks"] == 1


def test_mastery_row_with_another_exam_id_counts():
    out = _derive([_node("t")], mastery=[_mastery("t", 80, exam="e-other")], audit=_audit("t", 2))
    assert _macro(out, "t")["state"] == "mastered"


def test_latest_mastery_row_wins_when_a_topic_has_several():
    rows = [_mastery("t", 30, exam="e-1", updated=NOW - timedelta(days=5)),
            _mastery("t", 80, exam="e-2", updated=NOW)]
    out = _derive([_node("t")], mastery=rows, audit=_audit("t", 2))
    assert _macro(out, "t")["score"] == 80.0


# ─── rollup + ordering ──────────────────────────────────────────────────────


def test_rollup_counts_and_pct_mastered():
    nodes = [_node(t) for t in ("m1", "m2", "w", "n")]
    out = _derive(
        nodes,
        mastery=[_mastery("m1", 90), _mastery("m2", 80), _mastery("w", 30)],
        audit=_audit("m1", 2, last=NOW - timedelta(days=30)) + _audit("m2", 2) + _audit("w", 2),
    )
    [subj] = out
    assert subj["rollup"] == {
        "not_started": 1, "studied": 1, "mastered": 2,
        "weak_count": 1, "revise_count": 1, "pct_mastered": 50.0,
    }


def test_subjects_by_name_macros_by_comparable_priority():
    nodes = [_node("low", subject="s-b"), _node("high", subject="s-b"), _node("x", subject="s-a")]
    cov = {"low": {"comparable_priority": 10}, "high": {"comparable_priority": 90},
           "x": {"comparable_priority": 50}}
    out = _derive(nodes, coverage=cov)
    assert [s["subject_id"] for s in out] == ["s-a", "s-b"]
    assert [m["topic_id"] for m in out[1]["macros"]] == ["high", "low"]


# ─── loader + endpoint (stubbed Supabase, real coverage scoping) ────────────

_EXAM = "11111111-1111-1111-1111-111111111111"
_PHASE = "ph-1"


def _section(sec: str, sub: str, *, elective: bool) -> dict:
    return {"id": sec, "exam_phase_id": _PHASE, "subject_id": sub, "section_label": sec,
            "selection_kind": "elective" if elective else "compulsory",
            "elective_group": "opt" if elective else None}


def _cov(cid: str, tid: str, sec: str, prio: float = 70) -> dict:
    return {"id": cid, "exam_id": _EXAM, "exam_cycle_id": "cyc", "exam_phase_id": _PHASE,
            "section_id": sec, "topic_id": tid, "exam_priority_score": prio,
            "is_high_yield": True, "reviewer_status": "locked", "predictability_band": "high"}


def _seed(**extra: Any) -> dict:
    seed = {
        "profiles": [{"id": "u-1", "target_exam": _EXAM}],
        "exams": [{"id": _EXAM, "slug": "nabard", "name": "NABARD", "is_active": True}],
        "exam_phases": [{"id": _PHASE, "exam_id": _EXAM, "phase_slug": "mains"}],
        "exam_phase_sections": [
            _section("sec-gs", "sub-gs", elective=False),
            _section("sec-opt", "sub-opt", elective=True),
        ],
        "subjects": [{"id": "sub-gs", "name": "Reasoning", "slug": "gs", "subject_group": None},
                     {"id": "sub-opt", "name": "Optional", "slug": "opt", "subject_group": None}],
        "topics": [
            {"id": "t-macro", "name": "Puzzles", "subject_id": "sub-gs", "is_active": True,
             "parent_topic_id": None, "level": "topic"},
            {"id": "t-micro", "name": "Seating", "subject_id": "sub-gs", "is_active": True,
             "parent_topic_id": "t-macro", "level": "microtopic"},
            {"id": "t-dead", "name": "Retired", "subject_id": "sub-gs", "is_active": False,
             "parent_topic_id": None, "level": "topic"},
            {"id": "t-out", "name": "Not covered", "subject_id": "sub-gs", "is_active": True,
             "parent_topic_id": None, "level": "topic"},
            {"id": "t-opt", "name": "Optional topic", "subject_id": "sub-opt", "is_active": True,
             "parent_topic_id": None, "level": "topic"},
        ],
        "exam_topic_coverage": [
            _cov("c-micro", "t-micro", "sec-gs"),
            _cov("c-dead", "t-dead", "sec-gs"),
            _cov("c-opt", "t-opt", "sec-opt"),
        ],
        "user_topic_mastery": [
            {"id": "m1", "user_id": "u-1", "topic_id": "t-macro", "exam_id": "other-exam",
             "mastery_score": 54.71, "updated_at": NOW.isoformat()},
            {"id": "m2", "user_id": "u-1", "topic_id": "t-out", "exam_id": _EXAM,
             "mastery_score": 90, "updated_at": NOW.isoformat()},
        ],
        "user_topic_mastery_audit": [
            {"id": "a1", "user_id": "u-1", "topic_id": "t-macro", "attempt_id": "att-1",
             "after_mastery_db": 54.71, "at": NOW.isoformat()},
        ],
        "study_tasks": [],
    }
    seed.update(extra)
    return seed


def _client(sb: SBStub) -> TestClient:
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": "u-1", "role": "user"}
    return TestClient(app, raise_server_exceptions=False)


def _all_topic_ids(body: dict) -> set[str]:
    ids = set()
    for s in body["subjects"]:
        for m in s["macros"]:
            ids.add(m["topic_id"])
            ids.update(x["topic_id"] for x in m["micros"])
    return ids


def test_endpoint_builds_the_scoped_tree():
    res = _client(SBStub(_seed())).get(f"/api/study/progress/roadmap?exam_id={_EXAM}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["thresholds"] == {"weak_below": 50.0, "mastered_at": 75.0,
                                  "min_attempts": 2, "revise_after_days": 14}
    [subj] = body["subjects"]
    assert subj["name"] == "Reasoning"
    [macro] = subj["macros"]
    # Macro parent pulled in from the covered micro; its mastery row came from
    # another exam and still counts.
    assert macro["topic_id"] == "t-macro" and macro["score"] == 54.71
    assert macro["state"] == "studied" and macro["attempts"] == 1
    assert [m["topic_id"] for m in macro["micros"]] == ["t-micro"]
    assert macro["micros"][0]["is_high_yield"] is True
    assert macro["micros"][0]["predictability_band"] == "high"


def test_inactive_and_uncovered_topics_are_excluded():
    body = _client(SBStub(_seed())).get(f"/api/study/progress/roadmap?exam_id={_EXAM}").json()
    ids = _all_topic_ids(body)
    assert "t-dead" not in ids  # inactive
    assert "t-out" not in ids   # mastery exists, but outside scoped coverage


def test_gs_only_user_never_sees_optional_nodes():
    body = _client(SBStub(_seed())).get(f"/api/study/progress/roadmap?exam_id={_EXAM}").json()
    assert "t-opt" not in _all_topic_ids(body)
    assert "sub-opt" not in {s["subject_id"] for s in body["subjects"]}


def test_user_who_chose_the_optional_sees_it():
    seed = _seed(user_exam_electives=[{"id": "ue", "user_id": "u-1", "exam_id": _EXAM,
                                       "elective_group": "opt", "subject_ids": ["sub-opt"]}])
    body = _client(SBStub(seed)).get(f"/api/study/progress/roadmap?exam_id={_EXAM}").json()
    assert "t-opt" in _all_topic_ids(body)


def test_completed_tasks_are_counted_per_topic():
    seed = _seed(study_tasks=[
        {"id": "k1", "user_id": "u-1", "topic_id": "t-micro", "subject_id": "sub-gs", "status": "completed"},
        {"id": "k2", "user_id": "u-1", "topic_id": "t-micro", "subject_id": "sub-gs", "status": "planned"},
    ])
    body = _client(SBStub(seed)).get(f"/api/study/progress/roadmap?exam_id={_EXAM}").json()
    micro = body["subjects"][0]["macros"][0]["micros"][0]
    assert micro["completed_tasks"] == 1 and micro["state"] == "studied"


def test_not_planner_ready_is_409():
    seed = _seed(exam_topic_coverage=[])
    res = _client(SBStub(seed)).get(f"/api/study/progress/roadmap?exam_id={_EXAM}")
    assert res.status_code == 409
    assert res.json()["detail"] == {"reason": "not_planner_ready"}


def test_inactive_exam_is_409():
    seed = _seed(exams=[{"id": _EXAM, "slug": "nabard", "name": "NABARD", "is_active": False}])
    res = _client(SBStub(seed)).get(f"/api/study/progress/roadmap?exam_id={_EXAM}")
    assert res.status_code == 409


def test_coverage_read_failure_is_503(monkeypatch):
    monkeypatch.setattr(roadmap, "load_scoped_coverage_checked", lambda *a, **k: ([], False))
    res = _client(SBStub(_seed())).get(f"/api/study/progress/roadmap?exam_id={_EXAM}")
    assert res.status_code == 503
    assert res.json()["detail"] == {"reason": "roadmap_read_failed"}


def test_evidence_read_failure_is_503_not_a_partial_tree(monkeypatch):
    sb = SBStub(_seed())
    real_table = sb.table

    def table(name):
        if name == "user_topic_mastery_audit":
            raise RuntimeError("boom")
        return real_table(name)

    sb.table = table  # type: ignore[assignment]
    res = _client(sb).get(f"/api/study/progress/roadmap?exam_id={_EXAM}")
    assert res.status_code == 503


def test_drawer_readiness_rule_is_shared():
    # The exam drawer and the roadmap call the same predicate.
    assert study_os_api._is_planner_ready({"id": "e", "is_active": True}, {"e": 1}) is True
    assert study_os_api._is_planner_ready({"id": "e", "is_active": True}, {}) is False
    assert study_os_api._is_planner_ready({"id": "e", "is_active": False}, {"e": 3}) is False
    assert study_os_api._is_planner_ready({"id": "e", "is_active": True}, None) is False
