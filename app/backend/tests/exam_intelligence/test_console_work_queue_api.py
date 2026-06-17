"""Endpoint + integration tests for the console work queue (Wave 4.6H).

Exercises GET /console/exams and /console/summary against the in-memory SBStub,
asserting the canonical status model, base-filter parity with /exams, workflow
filters, deterministic sort, pagination, summary scoping, response guards, and
that reads are set-based (constant DB calls regardless of exam count).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_api
from app.core.auth import get_current_user
from app.exam_intelligence import work_queue as wq
from tests.persona_questions._stub import SBStub


# ── Harness ─────────────────────────────────────────────────────────────────

class CountingSBStub(SBStub):
    """SBStub that counts table() calls, to prove reads don't scale per-exam."""

    def __init__(self, db=None):
        super().__init__(db)
        self.table_calls = 0

    def table(self, name):
        self.table_calls += 1
        return super().table(name)


def _build_app(sb, role="super_admin"):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    user = {"id": "admin-1", "role": role,
            "permissions": ["exam_intelligence.review"] if role == "admin" else []}
    app.dependency_overrides[get_current_user] = lambda: user
    return app


_RECENT = "2026-06-16T00:00:00+00:00"
_STALE = "2026-01-01T00:00:00+00:00"


class _Seed:
    """Accumulates rows across tables for a set of synthetic exams."""

    def __init__(self):
        self.db = {t: [] for t in (
            "exams", "exam_phases", "exam_topic_coverage", "syllabus_topic_mentions",
            "exam_policy_updates", "mock_question_bank", "pyq_papers", "pyq_questions",
            "pyq_question_topic_tags", "pyq_options", "organizations",
        )}

    def exam(self, eid, *, name, mode, phases=1, locked=1, reviewed=0,
             verified_pyq=0, total_pyq=0, mock=0, pending=0, stale=0,
             active=True, org=None):
        self.db["exams"].append({
            "id": eid, "slug": eid, "name": name, "exam_type": "recruitment",
            "is_active": active, "exam_family_id": None, "management_mode": mode,
            "cadence": "annual", "conducting_organization_id": org,
        })
        for i in range(phases):
            self.db["exam_phases"].append({"id": f"{eid}-ph{i}", "exam_id": eid})
        for i in range(locked):
            self.db["exam_topic_coverage"].append(
                {"id": f"{eid}-cl{i}", "exam_id": eid, "reviewer_status": "locked",
                 "created_at": _RECENT})
        for i in range(reviewed):
            self.db["exam_topic_coverage"].append(
                {"id": f"{eid}-cr{i}", "exam_id": eid, "reviewer_status": "reviewed",
                 "created_at": _RECENT})
        for i in range(mock):
            self.db["mock_question_bank"].append(
                {"id": f"{eid}-mk{i}", "exam_id": eid, "reviewer_status": "verified"})
        # PYQ: one verified paper, verified_pyq verified + (total_pyq-verified) pending questions.
        if total_pyq:
            self.db["pyq_papers"].append(
                {"id": f"{eid}-pp", "exam_id": eid, "trust_status": "verified"})
            for i in range(total_pyq):
                status = "verified" if i < verified_pyq else "pending"
                self.db["pyq_questions"].append(
                    {"id": f"{eid}-q{i}", "pyq_paper_id": f"{eid}-pp",
                     "reviewer_status": status, "created_at": _RECENT})
        # Pending / stale review rows on the syllabus table.
        for i in range(pending):
            self.db["syllabus_topic_mentions"].append(
                {"id": f"{eid}-sp{i}", "exam_id": eid, "reviewer_status": "pending",
                 "created_at": _RECENT})
        for i in range(stale):
            self.db["syllabus_topic_mentions"].append(
                {"id": f"{eid}-ss{i}", "exam_id": eid, "reviewer_status": "pending",
                 "created_at": _STALE})
        return self


def _seed():
    s = _Seed()
    s.db["organizations"].append({"id": "org1", "name": "Staff Selection Commission"})
    # blocked: no phases, no coverage
    s.exam("b1", name="Blocked Setup", mode=None, phases=0, locked=0, mock=40, org="org1")
    # blocked: phase present, only reviewed coverage (no locked)
    s.exam("b2", name="Blocked Coverage", mode="core", locked=0, reviewed=2, mock=40)
    # ready: locked + verified pyq + healthy mock + no pending
    s.exam("rdy", name="Ready Exam", mode="core", locked=1, verified_pyq=3, total_pyq=3, mock=40)
    # needs_action: no verified pyq
    s.exam("npyq", name="Needs Pyq", mode="light", locked=1, verified_pyq=0, total_pyq=2, mock=40)
    # needs_action: pending review (recent)
    s.exam("pend", name="Pending Review", mode="core", locked=1, verified_pyq=1, total_pyq=1,
           mock=40, pending=1)
    # needs_action: stale pending review (>14d)
    s.exam("stale", name="Stale Review", mode="core", locked=1, verified_pyq=1, total_pyq=1,
           mock=40, stale=1)
    # needs_action: thin mock bank only
    s.exam("thin", name="Thin Mock", mode="index_only", locked=1, verified_pyq=1, total_pyq=1,
           mock=5)
    # archived (excluded from default scope)
    s.exam("arch", name="Archived", mode="archive", locked=1, verified_pyq=1, total_pyq=1, mock=40)
    return s.db


def _client(role="super_admin", db=None):
    sb = CountingSBStub(db if db is not None else _seed())
    return TestClient(_build_app(sb, role=role)), sb


# ── Permission ──────────────────────────────────────────────────────────────

def test_permission_admin_ok_user_forbidden():
    ok, _ = _client(role="admin")
    assert ok.get("/api/admin/exam-intelligence/console/exams").status_code == 200
    assert ok.get("/api/admin/exam-intelligence/console/summary").status_code == 200
    denied, _ = _client(role="user")
    assert denied.get("/api/admin/exam-intelligence/console/exams").status_code == 403
    assert denied.get("/api/admin/exam-intelligence/console/summary").status_code == 403


# ── Status model + scope ────────────────────────────────────────────────────

def test_default_scope_excludes_archive_and_classifies():
    client, _ = _client()
    body = client.get("/api/admin/exam-intelligence/console/exams?limit=100").json()
    by_id = {r["id"]: r for r in body["items"]}
    assert "arch" not in by_id  # archive excluded by default, like /exams
    assert by_id["b1"]["status"] == "blocked" and by_id["b1"]["blocker_count"] == 2
    assert by_id["b2"]["status"] == "blocked" and "missing_coverage" in by_id["b2"]["flags"]
    assert by_id["rdy"]["status"] == "ready" and by_id["rdy"]["flags"] == []
    assert by_id["npyq"]["status"] == "needs_action" and "missing_pyq" in by_id["npyq"]["flags"]
    assert by_id["thin"]["status"] == "needs_action" and "thin_mock_bank" in by_id["thin"]["flags"]
    assert by_id["stale"]["flags"].count("stale_review_queue") == 1
    # truthful aggregates
    assert by_id["rdy"]["locked_coverage_count"] == 1
    assert by_id["rdy"]["verified_pyq_count"] == 3
    assert by_id["npyq"]["verified_pyq_count"] == 0 and by_id["npyq"]["total_pyq_count"] == 2


# ── Base-filter parity with /exams ──────────────────────────────────────────

def test_management_mode_null_sentinel_matches_unclassified():
    client, _ = _client()
    body = client.get("/api/admin/exam-intelligence/console/exams?management_mode=__null__&limit=100").json()
    assert [r["id"] for r in body["items"]] == ["b1"]


def test_management_mode_archive_includes_only_archive():
    client, _ = _client()
    body = client.get("/api/admin/exam-intelligence/console/exams?management_mode=archive&limit=100").json()
    assert [r["id"] for r in body["items"]] == ["arch"]


def test_active_state_all_includes_archive_scope():
    client, _ = _client()
    body = client.get("/api/admin/exam-intelligence/console/exams?active_state=all&limit=100").json()
    # active_state=all keeps the default archive-exclusion (management_mode rule),
    # so arch is still excluded; count is the 7 non-archive exams.
    assert body["total_count"] == 7


def test_q_filters_by_name():
    client, _ = _client()
    body = client.get("/api/admin/exam-intelligence/console/exams?q=ready&limit=100").json()
    assert [r["id"] for r in body["items"]] == ["rdy"]


# ── Workflow filters ────────────────────────────────────────────────────────

def test_workflow_primary_and_flag_filters():
    client, _ = _client()
    blocked = client.get("/api/admin/exam-intelligence/console/exams?workflow=blocked&limit=100").json()
    assert {r["id"] for r in blocked["items"]} == {"b1", "b2"}
    thin = client.get("/api/admin/exam-intelligence/console/exams?workflow=thin_mock_bank&limit=100").json()
    assert {r["id"] for r in thin["items"]} == {"thin"}
    stale = client.get("/api/admin/exam-intelligence/console/exams?workflow=stale_review_queue&limit=100").json()
    assert {r["id"] for r in stale["items"]} == {"stale"}


def test_unknown_workflow_rejected():
    client, _ = _client()
    r = client.get("/api/admin/exam-intelligence/console/exams?workflow=on_fire")
    assert r.status_code == 422


def test_unknown_sort_rejected():
    client, _ = _client()
    r = client.get("/api/admin/exam-intelligence/console/exams?sort=banana")
    assert r.status_code == 422


# ── Sort ────────────────────────────────────────────────────────────────────

def test_blockers_first_orders_blocked_then_needs_then_ready():
    client, _ = _client()
    items = client.get("/api/admin/exam-intelligence/console/exams?sort=blockers_first&limit=100").json()["items"]
    ranks = [wq.STATUS_RANK[r["status"]] for r in items]
    assert ranks == sorted(ranks)
    # first two are blocked, ordered by blocker_count desc (b1 has 2, b2 has 1)
    assert items[0]["id"] == "b1" and items[1]["id"] == "b2"


def test_name_sort_is_alphabetical():
    client, _ = _client()
    items = client.get("/api/admin/exam-intelligence/console/exams?sort=name&limit=100").json()["items"]
    names = [r["name"] for r in items]
    assert names == sorted(names)


def test_management_lane_sort_ranks_lanes():
    client, _ = _client()
    items = client.get("/api/admin/exam-intelligence/console/exams?sort=management_lane&limit=100").json()["items"]
    lane_ranks = [wq._LANE_RANK.get(r["management_mode"], wq._LANE_RANK[None]) for r in items]
    assert lane_ranks == sorted(lane_ranks)


# ── Pagination (after filter+sort) ──────────────────────────────────────────

def test_pagination_applies_after_filter_and_sort():
    client, _ = _client()
    p0 = client.get("/api/admin/exam-intelligence/console/exams?sort=name&limit=3&offset=0").json()
    p1 = client.get("/api/admin/exam-intelligence/console/exams?sort=name&limit=3&offset=3").json()
    assert p0["total_count"] == 7 and p1["total_count"] == 7
    assert p0["count"] == 3 and p0["has_next"] is True
    full = client.get("/api/admin/exam-intelligence/console/exams?sort=name&limit=100").json()["items"]
    assert [r["id"] for r in p0["items"]] == [r["id"] for r in full[:3]]
    assert [r["id"] for r in p1["items"]] == [r["id"] for r in full[3:6]]


# ── Summary ─────────────────────────────────────────────────────────────────

def test_summary_primaries_sum_to_total_and_flags_overlap():
    client, _ = _client()
    s = client.get("/api/admin/exam-intelligence/console/summary").json()
    assert s["blocked"] + s["needs_action"] + s["ready"] == s["total_count"] == 7
    assert s["blocked"] == 2 and s["ready"] == 1 and s["needs_action"] == 4
    # pend (syllabus) + stale (syllabus) + npyq (2 unverified PYQ questions awaiting review)
    assert s["pending_review"] == 3
    assert s["stale_review_queue"] == 1
    assert s["thin_mock_bank"] == 1
    assert "stale_official_intelligence" not in s
    assert "generated_at" in s


def test_summary_shares_scope_with_list_under_filters():
    client, _ = _client()
    s = client.get("/api/admin/exam-intelligence/console/summary?q=ready").json()
    lst = client.get("/api/admin/exam-intelligence/console/exams?q=ready&limit=100").json()
    assert s["total_count"] == lst["total_count"] == 1
    assert s["ready"] == 1 and s["blocked"] == 0 and s["needs_action"] == 0


# ── Response guards ─────────────────────────────────────────────────────────

def _walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_keys(v)


def test_no_forbidden_fields_in_responses():
    client, _ = _client()
    forbidden = {"score_percent", "confidence_score", "confidence_percent",
                 "conducting_organization_id", "state", "jurisdiction", "reviewer_status"}
    for path in ("/api/admin/exam-intelligence/console/exams?limit=100",
                 "/api/admin/exam-intelligence/console/summary"):
        body = client.get(path).json()
        keys = set(_walk_keys(body))
        assert not (keys & forbidden), keys & forbidden


def test_organization_name_exposed_not_raw_id():
    client, _ = _client()
    body = client.get("/api/admin/exam-intelligence/console/exams?limit=100").json()
    b1 = next(r for r in body["items"] if r["id"] == "b1")
    assert b1["organization_name"] == "Staff Selection Commission"
    rdy = next(r for r in body["items"] if r["id"] == "rdy")
    assert rdy["organization_name"] is None  # no conducting org → null, never fabricated


# ── Set-based: DB calls do not scale per exam ───────────────────────────────

def _seed_n(n):
    s = _Seed()
    for i in range(n):
        s.exam(f"e{i}", name=f"Exam {i}", mode="core", locked=1, verified_pyq=1,
               total_pyq=1, mock=40)
    return s.db


def test_reads_are_set_based_not_per_exam():
    small_client, small_sb = _client(db=_seed_n(2))
    small_client.get("/api/admin/exam-intelligence/console/exams?limit=100")
    small_calls = small_sb.table_calls

    big_client, big_sb = _client(db=_seed_n(40))
    big_client.get("/api/admin/exam-intelligence/console/exams?limit=100")
    big_calls = big_sb.table_calls

    # 20x the exams, same table structure → identical number of DB round-trips.
    assert small_calls == big_calls
