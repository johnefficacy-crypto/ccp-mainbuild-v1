"""Regression: exam-scale `.in_()` reads must be chunked and paginated.

`practice_ready_counts_by_paper` returned 0 for EVERY paper on a healthy corpus
(26 verified papers, 1070 published + actively-projected bank rows). Cause:
`_active_projection_ids` put all ~1070 uuids into ONE PostgREST `.in_()` filter
— roughly 40 KB of query string — and the request was rejected:

    WARNING career_copilot.study_os.pyq_practice
    db_op_failed op=pyq_practice.active_projections err=Error 400:

`safe_required` returned None, the helper raised, and the caller's fail-closed
`except` turned the fault into "no availability" — a uniform, silent zero.

The fake client here enforces the two server-side ceilings the real stack has:

  * any `.in_()` list longer than `_ID_BATCH` raises ``Error 400`` (PostgREST
    URL-length ceiling), and
  * any single response is capped at `_PAGE` rows (Supabase ``db-max-rows``),

so an unchunked read fails and an unpaginated bulk read silently truncates.
Both would have been invisible to the pre-existing 3-row fixtures.
"""
from __future__ import annotations

import pytest

from app.study_os import pyq_practice as svc

EXAM = "11111111-1111-1111-1111-111111111111"
PAPERS = [f"paper-{i:04d}" for i in range(26)]
# Above _PAGE (1000) so a single unpaginated bank read cannot return them all,
# and well above _ID_BATCH (250) so an unchunked .in_() overflows.
TOTAL = 1070
OPTIONS_PER_Q = 4


def _bank_rows() -> list[dict]:
    rows = []
    for i in range(TOTAL):
        qid = f"q-{i:04d}"
        rows.append(
            {
                "id": qid,
                "question_text": f"Question {i}",
                "question_type": "mcq",
                "reviewer_status": "published",
                "correct_option_id": f"opt-{qid}-2",
                "exam_id": EXAM,
                "pyq_question_id": f"pyqq-{i:04d}",
                "pyq_paper_id": PAPERS[i % len(PAPERS)],
                "valid_until": None,
                "topic_id": "topic-1",
                "microtopic_id": None,
                "pyq_year": 2024,
                "difficulty": "medium",
                "source_kind": "pyq_projection",
            }
        )
    return rows


def _option_rows() -> list[dict]:
    return [
        {
            "id": f"opt-q-{i:04d}-{k}",
            "question_id": f"q-{i:04d}",
            "option_text": f"Option {k}",
            "option_index": k,
            "is_correct": k == 2,
            "source_label": f"({chr(96 + k)})",
            "display_order": k,
        }
        for i in range(TOTAL)
        for k in range(1, OPTIONS_PER_Q + 1)
    ]


class _Query:
    """Minimal PostgREST query builder with the real stack's two ceilings."""

    def __init__(self, client: "_FakeSB", table: str) -> None:
        self._c = client
        self._table = table
        self._rows = list(client.tables.get(table, []))
        self._order: list[str] = []
        self._range: tuple[int, int] | None = None
        self._negate = False

    # -- filters ----------------------------------------------------------
    def select(self, *_a, **_k) -> "_Query":
        return self

    def limit(self, _n: int) -> "_Query":
        # Deliberately a no-op: a bare `.limit()` does NOT defeat db-max-rows,
        # which is exactly the assumption the old code made.
        return self

    def eq(self, col: str, val) -> "_Query":
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def in_(self, col: str, vals) -> "_Query":
        vals = list(vals)
        self._c.in_sizes.append((self._table, col, len(vals)))
        if len(vals) > svc._ID_BATCH:
            raise RuntimeError(
                f"Error 400: query string too long ({len(vals)} ids in {col}=in.())"
            )
        wanted = set(vals)
        self._rows = [r for r in self._rows if r.get(col) in wanted]
        return self

    @property
    def not_(self) -> "_Query":
        self._negate = True
        return self

    def is_(self, col: str, val: str) -> "_Query":
        assert val == "null"
        if self._negate:
            self._rows = [r for r in self._rows if r.get(col) is not None]
            self._negate = False
        else:
            self._rows = [r for r in self._rows if r.get(col) is None]
        return self

    def or_(self, _expr: str) -> "_Query":
        # Only ever used here for the valid_until TTL guard; every fixture row
        # has valid_until NULL, so the predicate is a pass-through.
        return self

    def order(self, col: str, **_k) -> "_Query":
        self._order.append(col)
        return self

    def range(self, from_n: int, to_n: int) -> "_Query":
        self._range = (from_n, to_n)
        return self

    # -- execution --------------------------------------------------------
    def execute(self):
        rows = self._rows
        for col in reversed(self._order):
            rows = sorted(rows, key=lambda r: (r.get(col) is None, str(r.get(col))))
        if self._range is not None:
            f, t = self._range
            rows = rows[f : t + 1]
        capped = rows[: svc._PAGE]          # Supabase db-max-rows
        self._c.responses.append((self._table, len(capped)))
        return type("Res", (), {"data": capped})()


class _FakeSB:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables
        self.in_sizes: list[tuple[str, str, int]] = []
        self.responses: list[tuple[str, int]] = []

    def table(self, name: str) -> _Query:
        return _Query(self, name)


@pytest.fixture()
def sb() -> _FakeSB:
    bank = _bank_rows()
    return _FakeSB(
        {
            "mock_question_bank": bank,
            "pyq_mock_question_projections": [
                {"mock_question_id": r["id"], "sync_status": "active"} for r in bank
            ],
            "mock_question_options": _option_rows(),
            "mock_question_stimuli": [],
        }
    )


def test_ready_counts_survive_exam_scale_id_lists(sb: _FakeSB) -> None:
    """1070 projected rows across 26 papers must count, not collapse to zero."""
    counts = svc.practice_ready_counts_by_paper(sb, EXAM, paper_ids=PAPERS)

    assert sum(counts.values()) == TOTAL
    assert len(counts) == len(PAPERS)
    assert all(v > 0 for v in counts.values()), "no paper may report a false zero"
    # Every paper's count is exact, not merely non-zero.
    expected = {p: sum(1 for i in range(TOTAL) if PAPERS[i % len(PAPERS)] == p) for p in PAPERS}
    assert counts == expected


def test_no_single_in_filter_exceeds_the_url_batch(sb: _FakeSB) -> None:
    """Every `.in_()` on this path stays within the PostgREST URL ceiling."""
    svc.practice_ready_counts_by_paper(sb, EXAM, paper_ids=PAPERS)

    oversized = [(t, c, n) for t, c, n in sb.in_sizes if n > svc._ID_BATCH]
    assert not oversized, f"unchunked .in_() would 400: {oversized}"
    # The confirmed failure site specifically.
    proj = [n for t, _c, n in sb.in_sizes if t == "pyq_mock_question_projections"]
    assert proj and max(proj) <= svc._ID_BATCH


def test_bulk_reads_paginate_past_the_row_cap(sb: _FakeSB) -> None:
    """No read may stop at a full page — that is a silent truncation."""
    svc.practice_ready_counts_by_paper(sb, EXAM, paper_ids=PAPERS)

    # The bank read alone exceeds one page (1070 > _PAGE), and 250 questions
    # yield exactly _PAGE option rows, so both must have paged for the counts
    # above to come out whole.
    assert any(t == "mock_question_bank" and n == svc._PAGE for t, n in sb.responses)
    assert sum(n for t, n in sb.responses if t == "mock_question_options") == TOTAL * OPTIONS_PER_Q


def test_read_failure_surfaces_as_a_fault_not_a_zero(sb: _FakeSB) -> None:
    """A failed projection read must not be reported as "nothing is ready"."""
    original = sb.table

    def _break_projections(name: str):
        q = original(name)
        if name == "pyq_mock_question_projections":
            q.execute = lambda: (_ for _ in ()).throw(RuntimeError("Error 400:"))
        return q

    sb.table = _break_projections  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        svc._active_projection_ids(sb, [f"q-{i:04d}" for i in range(TOTAL)])
