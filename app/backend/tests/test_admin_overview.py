"""Coverage for GET /api/admin/overview.

The overview KPIs intentionally compose several counts in Python rather
than relying on a server-side aggregate. The fix in this PR collapses
duplicate-keyed counts so we issue one Supabase call per distinct
(table, filters) tuple instead of repeating ``moderation_items
status=open`` and ``copyright_claims status=received`` queries.

These tests pin both behaviours:
    * the response shape stays identical for the same DB state;
    * the number of Supabase queries drops by at least 2 per request.
"""
from __future__ import annotations

import pytest

from app.api import admin_overview


class R:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class Q:
    def __init__(self, table, state):
        self.table = table
        self.state = state
        self.filters: dict = {}
        self.gte_filters: dict = {}
        self.limit_n = None
        self.order_calls: list = []
        self.want_count = False

    def select(self, *a, count=None, **k):
        if count == "exact":
            self.want_count = True
        return self

    def eq(self, k, v):
        self.filters[k] = v
        return self

    def is_(self, k, v):
        # "null" means IS NULL — store as a sentinel so dispatch can match
        self.filters[f"__is_null_{k}"] = (v == "null")
        return self

    def gte(self, k, v):
        self.gte_filters[k] = v
        return self

    def order(self, *a, **k):
        self.order_calls.append((a, k))
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def execute(self):
        return self.state.dispatch(self)


class SB:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {}
        self.queries: list[Q] = []

    def table(self, name):
        q = Q(name, self)
        self.queries.append(q)
        return q

    def dispatch(self, q):
        rows = self.tables.get(q.table, [])
        filtered = []
        for row in rows:
            match = True
            for k, v in q.filters.items():
                if k.startswith("__is_null_"):
                    col = k[len("__is_null_"):]
                    if v and row.get(col) is not None:
                        match = False
                        break
                    if not v and row.get(col) is None:
                        match = False
                        break
                elif row.get(k) != v:
                    match = False
                    break
            if match:
                filtered.append(row)
        if q.gte_filters:
            for k, v in q.gte_filters.items():
                filtered = [r for r in filtered if (r.get(k) or "") >= v]
        if q.limit_n is not None:
            filtered = filtered[: q.limit_n]
        return R([dict(r) for r in filtered], count=len(filtered) if q.want_count else None)


ADMIN_USER = {"id": "admin-1", "email": "a@b.c", "role": "admin"}


@pytest.fixture
def sb(monkeypatch):
    fake = SB()
    monkeypatch.setattr(admin_overview, "get_supabase_admin", lambda: fake)
    return fake


def _seed(sb):
    sb.tables["profiles"] = [{"id": f"u{i}"} for i in range(7)]
    sb.tables["recruitments"] = [
        {"id": "r1", "status": "active"},
        {"id": "r2", "status": "active"},
        {"id": "r3", "status": "archived"},
    ]
    sb.tables["forum_posts"] = [{"id": "p1"}, {"id": "p2"}]
    sb.tables["moderation_items"] = [
        {"id": "m1", "status": "open", "severity": "p0"},
        {"id": "m2", "status": "open", "severity": "p1"},
        {"id": "m3", "status": "resolved", "severity": "p0"},
    ]
    sb.tables["copyright_claims"] = [
        {"id": "c1", "status": "received"},
        {"id": "c2", "status": "received"},
        {"id": "c3", "status": "triage"},
        {"id": "c4", "status": "resolved"},
    ]
    sb.tables["scrape_runs"] = []
    sb.tables["admin_audit_logs"] = []
    sb.tables["exam_eligibility_rules"] = [
        {"id": "e1", "reviewer_status": "draft"},
        {"id": "e2", "reviewer_status": "draft"},
        {"id": "e3", "reviewer_status": "verified"},
        {"id": "e4", "reviewer_status": "archived"},
    ]
    sb.tables["reverification_batches"] = [
        {"id": "b1", "acknowledged_at": None},
        {"id": "b2", "acknowledged_at": None},
        {"id": "b3", "acknowledged_at": "2025-01-01T00:00:00Z"},
    ]
    sb.tables["recruitment_verification_reports"] = [
        {"id": "rv1", "superseded_by": None, "recommended_action": "request_admin_review"},
        {"id": "rv2", "superseded_by": None, "recommended_action": "request_admin_review"},
        {"id": "rv3", "superseded_by": "rv1",  "recommended_action": "request_admin_review"},  # superseded
        {"id": "rv4", "superseded_by": None, "recommended_action": "no_action"},
    ]


def test_overview_response_shape_stable(sb):
    _seed(sb)
    out = admin_overview.overview(user=ADMIN_USER)
    assert set(out.keys()) == {"kpis", "kg", "recent_audit"}
    assert set(out["kpis"].keys()) == {
        "users", "recruitments", "threads", "open_flags",
        "scrape_runs_today", "queue_depth", "moderation_p0_open",
        "copyright_open",
    }
    assert set(out["kg"].keys()) == {
        "eligibility_rules", "unacked_reverification_batches", "reports_need_action",
    }
    assert set(out["kg"]["eligibility_rules"].keys()) == {"draft", "verified", "archived"}


def test_overview_kpi_values_match_seeded_state(sb):
    _seed(sb)
    out = admin_overview.overview(user=ADMIN_USER)
    kpis = out["kpis"]
    assert kpis["users"] == 7
    assert kpis["recruitments"] == 2  # only active
    assert kpis["threads"] == 2
    # 2 open moderation items
    assert kpis["open_flags"] == 2
    # open moderation (2) + received copyright (2)
    assert kpis["queue_depth"] == 4
    # severity=p0 AND status=open => 1
    assert kpis["moderation_p0_open"] == 1
    # received (2) + triage (1)
    assert kpis["copyright_open"] == 3


def test_overview_kg_counts_match_seeded_state(sb):
    _seed(sb)
    out = admin_overview.overview(user=ADMIN_USER)
    kg = out["kg"]
    assert kg["eligibility_rules"] == {"draft": 2, "verified": 1, "archived": 1}
    # 2 batches have acknowledged_at IS NULL
    assert kg["unacked_reverification_batches"] == 2
    # 2 reports: superseded_by IS NULL AND recommended_action='request_admin_review'
    # rv3 is excluded (superseded_by is set), rv4 is excluded (no_action)
    assert kg["reports_need_action"] == 2


def test_overview_does_not_repeat_open_moderation_or_received_copyright(sb):
    _seed(sb)
    admin_overview.overview(user=ADMIN_USER)
    mod_open = [
        q for q in sb.queries
        if q.table == "moderation_items"
        and q.filters == {"status": "open"}
    ]
    cp_received = [
        q for q in sb.queries
        if q.table == "copyright_claims"
        and q.filters == {"status": "received"}
    ]
    # The dedupe collapses each duplicate-keyed count to exactly one
    # Supabase call.
    assert len(mod_open) == 1, "expected one moderation_items status=open query"
    assert len(cp_received) == 1, "expected one copyright_claims status=received query"


def test_overview_call_count_drops_versus_legacy(sb):
    """The legacy code path issued 8 distinct count queries for the
    duplicate-counted KPIs (open_flags x1, queue_depth x2,
    moderation_p0_open x1, copyright_open x2 = 6 for those, plus users,
    recruitments, threads, scrape_runs_today). The dedupe drops that by
    at least 2 — concretely, we now issue 3 queries that hit
    (moderation_items+open, copyright_claims+received, copyright_claims+
    triage) plus the same 4 base counts and the audit-log fetch.
    """
    _seed(sb)
    admin_overview.overview(user=ADMIN_USER)
    # Count only the count-style queries (those that asked for
    # count="exact"). The audit-log fetch is `order(...).limit(10)`.
    count_queries = [q for q in sb.queries if q.want_count]
    # Original 8: users, recruitments, threads, moderation_items(open),
    # moderation_items(open,p0), copyright(received), copyright(triage), scrape_runs_gte.
    # +5 kg: eligibility_rules x3 (draft/verified/archived),
    # reverification_batches(unacked), verification_reports(need_action).
    assert len(count_queries) <= 13, count_queries
    assert 12 <= len(count_queries) <= 13