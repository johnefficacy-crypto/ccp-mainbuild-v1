"""Every migrated bulk read, driven at a server cap it does not know about.

`tests/common/test_pagination.py` proves the shared walk. This file proves each
CALL SITE actually uses it — a module that kept its own loop would pass the
first file and fail here.

Caps 5, 19 and 137: none is a divisor of the page size or of the row counts, so
a walk that trusts its own page size returns a slice and the assertion fails.
Before this change every one of these returned exactly `cap` rows.
"""
from __future__ import annotations

import pytest

from app.api import exam_intelligence as api_ei
from app.exam_intelligence import (
    coverage,
    coverage_derivation,
    cycle_readiness,
    document_policy,
    lookup,
    pyq_papers,
    reachability,
    score_snapshots,
)
from app.study_os import descriptive, generated_mock_attempt, planner, pyq_practice

CAPS = [5, 19, 137]
TOTAL = 421  # not a multiple of any cap, nor of any module's _PAGE


def _rows(n=TOTAL):
    return [{"id": f"r{i:05d}", "n": i} for i in range(n)]


class Capped:
    """A PostgREST read: inclusive range window, hard row cap applied last."""

    def __init__(self, rows, cap, *, exact_count=False):
        self.rows = rows
        self.cap = cap
        self.exact_count = exact_count
        self.calls = 0

    def rows_for(self, from_n, to_n):
        self.calls += 1
        return self.rows[from_n : to_n + 1][: self.cap]

    def response_for(self, from_n, to_n):
        return type("Resp", (), {"data": self.rows_for(from_n, to_n),
                                 "count": len(self.rows)})()

    def query_for(self, from_n, to_n):
        """A builder whose .execute() returns the response (safe_required path)."""
        server = self
        return type("Q", (), {"execute": staticmethod(
            lambda: server.response_for(from_n, to_n))})()


def _ns(rows):
    return [r["n"] for r in rows]


# ── the graceful callers: rows only ────────────────────────────────────────

@pytest.mark.parametrize("cap", CAPS)
@pytest.mark.parametrize("paginate_all", [
    pytest.param(api_ei._paginate_all, id="api.exam_intelligence"),
    pytest.param(reachability._paginate_all, id="exam_intelligence.reachability"),
    pytest.param(descriptive._paginate_all, id="study_os.descriptive"),
])
def test_rows_only_walks_return_every_row(cap, paginate_all):
    server = Capped(_rows(), cap)
    assert _ns(paginate_all(server.rows_for)) == list(range(TOTAL))


@pytest.mark.parametrize("cap", CAPS)
def test_pyq_papers_returns_every_row(cap):
    server = Capped(_rows(), cap)
    assert _ns(pyq_papers._paginate(server.rows_for)) == list(range(TOTAL))


# ── the (rows, complete) callers ───────────────────────────────────────────

@pytest.mark.parametrize("cap", CAPS)
def test_lookup_returns_every_row_and_reports_complete(cap):
    server = Capped(_rows(), cap)
    rows, complete = lookup._paginate(server.rows_for)
    assert complete is True
    assert _ns(rows) == list(range(TOTAL))


@pytest.mark.parametrize("cap", CAPS)
def test_planner_returns_every_row_and_reports_complete(cap):
    server = Capped(_rows(), cap)
    rows, complete = planner._paginate_all(server.rows_for, op="locked_coverage")
    assert complete is True
    assert _ns(rows) == list(range(TOTAL))


def test_planner_reports_a_failed_page_as_a_prefix():
    """The fail-closed half of the contract survived the migration."""
    server = Capped(_rows(), 19)
    calls = {"n": 0}

    def flaky(a, b):
        calls["n"] += 1
        return None if calls["n"] == 3 else server.rows_for(a, b)

    rows, complete = planner._paginate_all(flaky, op="locked_coverage")
    assert complete is False
    assert 0 < len(rows) < TOTAL


# ── the verified, fail-closed callers ──────────────────────────────────────

@pytest.mark.parametrize("cap", CAPS)
@pytest.mark.parametrize("module", [
    pytest.param(coverage, id="coverage"),
    pytest.param(coverage_derivation, id="coverage_derivation"),
    pytest.param(score_snapshots, id="score_snapshots"),
])
def test_verified_walks_return_every_row_when_the_count_agrees(cap, module):
    server = Capped(_rows(), cap, exact_count=True)
    rows = module._paginate(server.response_for, table="t", operation="op")
    assert rows is not None
    assert _ns(rows) == list(range(TOTAL))


@pytest.mark.parametrize("module", [
    pytest.param(coverage, id="coverage"),
    pytest.param(coverage_derivation, id="coverage_derivation"),
    pytest.param(score_snapshots, id="score_snapshots"),
])
def test_verified_walks_refuse_a_read_with_no_exact_count(module):
    """A partial read is more dangerous than a failed one, so no count means
    no rows — not the rows that happened to arrive."""
    server = Capped(_rows(), 19)
    assert module._paginate(server.rows_for, table="t", operation="op") is None


@pytest.mark.parametrize("module", [
    pytest.param(coverage, id="coverage"),
    pytest.param(coverage_derivation, id="coverage_derivation"),
    pytest.param(score_snapshots, id="score_snapshots"),
])
def test_verified_walks_refuse_a_short_read(module):
    server = Capped(_rows(), 19)

    def undercount(a, b):
        return type("Resp", (), {"data": server.rows_for(a, b), "count": TOTAL + 1})()

    assert module._paginate(undercount, table="t", operation="op") is None


# ── the safe_required callers ──────────────────────────────────────────────

@pytest.mark.parametrize("cap", CAPS)
@pytest.mark.parametrize("module", [
    pytest.param(generated_mock_attempt, id="generated_mock_attempt"),
    pytest.param(pyq_practice, id="pyq_practice"),
])
def test_safe_required_walks_return_every_row(cap, module):
    server = Capped(_rows(), cap)
    rows = module._read_paged(server.query_for, op="read")
    assert rows is not None
    assert _ns(rows) == list(range(TOTAL))


@pytest.mark.parametrize("module", [
    pytest.param(generated_mock_attempt, id="generated_mock_attempt"),
    pytest.param(pyq_practice, id="pyq_practice"),
])
def test_safe_required_walks_return_none_on_a_failed_page(module):
    """Never a partial page set — the caller must be able to tell "empty" from
    "could not read"."""
    server = Capped(_rows(), 19)
    calls = {"n": 0}

    def flaky(a, b):
        calls["n"] += 1
        if calls["n"] == 3:
            return type("Q", (), {"execute": staticmethod(_boom)})()
        return server.query_for(a, b)

    assert module._read_paged(flaky, op="read") is None


def _boom():
    raise RuntimeError("connection refused")


# ── the two that build their own query ─────────────────────────────────────

class _CappedSB:
    """Just enough Supabase to serve one capped, ordered, range-windowed table."""

    def __init__(self, rows, cap):
        self.rows = rows
        self.cap = cap
        self.calls = 0

    def table(self, name):
        return _CappedQuery(self)


class _CappedQuery:
    def __init__(self, sb):
        self.sb = sb
        self._range = None

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def range(self, from_n, to_n):
        self._range = (from_n, to_n)
        return self

    def execute(self):
        self.sb.calls += 1
        a, b = self._range or (0, len(self.sb.rows) - 1)
        return type("Resp", (), {"data": self.sb.rows[a : b + 1][: self.sb.cap],
                                 "count": None})()


@pytest.mark.parametrize("cap", CAPS)
def test_cycle_readiness_sees_every_document(cap):
    rows = [{"id": f"d{i:05d}", "metadata": {"exam_id": "e1", "exam_cycle_id": None}}
            for i in range(TOTAL)]
    sb = _CappedSB(rows, cap)
    assert len(cycle_readiness._get_exam_doc_ids(sb, "e1")) == TOTAL


@pytest.mark.parametrize("cap", CAPS)
def test_document_policy_reads_every_row(cap):
    sb = _CappedSB(_rows(), cap)
    rows = document_policy._fetch_paged(sb, "t", "id", {"exam_id": "e1"})
    assert _ns(rows) == list(range(TOTAL))


# ── the guarantee, stated once ─────────────────────────────────────────────

@pytest.mark.parametrize("cap", CAPS)
def test_no_migrated_read_returns_exactly_the_server_cap(cap):
    """What every one of these returned before the fix: one page, silently."""
    for walk in (api_ei._paginate_all, reachability._paginate_all,
                 descriptive._paginate_all, pyq_papers._paginate):
        rows = walk(Capped(_rows(), cap).rows_for)
        assert len(rows) != cap, f"{walk.__module__} still stops at the server cap"
        assert len(rows) == TOTAL


# ── the guard ──────────────────────────────────────────────────────────────

def test_no_module_still_terminates_a_walk_on_a_short_page():
    """The rule that caused this whole class of bug, banned repo-wide.

    `if len(rows) < _PAGE: break` is a no-op whenever the server's cap is below
    `_PAGE`, and it read as obviously-correct in nine separate modules. A tenth
    copy would pass every other test in this file, because it would be a read
    nothing here knows to exercise."""
    offenders = _grep(r"len\(\s*\w+\s*\)\s*<\s*_?PAGE\b")
    assert offenders == [], (
        "short-page termination is back in: " + ", ".join(offenders)
        + " — use app.common.pagination.paginate"
    )


def test_no_module_walks_its_own_pages():
    """The other half of the signature: a loop advancing an offset by a page
    constant IS a hand-rolled walk. Request-driven `.range()` (an API's own
    offset pagination) takes its offset from the caller and never does this, so
    the check catches new copies without flagging the legitimate reads."""
    offenders = _grep(r"\+=\s*_?PAGE\b")
    assert offenders == [], (
        "a hand-rolled pagination loop is back in: " + ", ".join(offenders)
        + " — use app.common.pagination.paginate"
    )


def _grep(pattern: str) -> list[str]:
    """Every `app/` line matching, except the shared module's own docstring."""
    import pathlib
    import re

    app_dir = pathlib.Path(__file__).resolve().parents[2] / "app"
    rx = re.compile(pattern)
    return [
        f"{p.relative_to(app_dir.parent)}:{i}"
        for p in sorted(app_dir.rglob("*.py"))
        if p.name != "pagination.py"
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if rx.search(line)
    ]
