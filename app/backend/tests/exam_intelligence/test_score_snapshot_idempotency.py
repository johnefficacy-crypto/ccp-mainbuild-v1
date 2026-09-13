"""``compute_exam_topic_scores`` must be idempotent under repeat calls.

SNAP-DUP-01: twelve identical computes against UPSC CSE Mains (1 227 topics),
one a minute with no input change, wrote 1 092 duplicate drafts across five of
them; the other seven were correctly idempotent.

The mechanism is the ``existing_fps`` index, and it is the *reads* that build
it, not the guard itself. Every ``_paginate`` call site issued a bare
``.range(from, to)`` with no ``.order(...)``. Range paging without a total
order is undefined in Postgres — each window is a separate query and the
server may return rows in a different physical order per page — so rows repeat
across pages while others never appear. The drafts index then came back
missing entries, the guard read "this topic has no draft yet", and the compute
inserted a second one. It is intermittent and load-dependent, which is exactly
what the incident log shows.

The scoring maths is untouched here (v2.0, locked in PR #1091); these tests
are about writes.
"""
from __future__ import annotations

import random
from typing import Any

from app.exam_intelligence.score_snapshots import (
    MODEL_VERSION,
    _PAGE,
    _build_fingerprint,
    compute_exam_topic_scores,
)
from tests.persona_questions._stub import SBStub

# Enough topics to force the drafts read across a page boundary, matching the
# live corpus that produced the incident.
N_TOPICS = _PAGE + 227


# ── A stub that models undefined row order on an unordered read ──────────────
class _R:
    def __init__(self, data: list[dict[str, Any]], count: int | None = None):
        self.data = data
        self.count = count


class _Q:
    """PostgREST-shaped query with a server row cap, real ``.range()`` and —
    the point of this stub — a per-query shuffle whenever the caller did not
    ask for an order. That is the licence Postgres actually has, and the
    behaviour a correct paginated read must not depend on."""

    def __init__(self, name: str, db: dict, cap: int, rng: random.Random):
        self._name = name
        self._db = db
        self._cap = cap
        self._rng = rng
        self._filters: list[tuple[str, str, Any]] = []
        self._orders: list[tuple[str, bool]] = []
        self._range: tuple[int, int] | None = None
        self._count: str | None = None
        self._insert: Any = None

    def select(self, *a: Any, count: str | None = None, **k: Any) -> "_Q":
        self._count = count
        return self

    def eq(self, key: str, val: Any) -> "_Q":
        self._filters.append((key, "eq", val))
        return self

    def neq(self, key: str, val: Any) -> "_Q":
        self._filters.append((key, "neq", val))
        return self

    def in_(self, key: str, vals: Any) -> "_Q":
        self._filters.append((key, "in", list(vals)))
        return self

    def is_(self, key: str, val: Any) -> "_Q":
        self._filters.append((key, "is", val))
        return self

    def limit(self, n: int) -> "_Q":
        self._range = (0, n - 1)
        return self

    def order(self, key: str, desc: bool = False, **k: Any) -> "_Q":
        self._orders.append((key, desc))
        return self

    def range(self, from_n: int, to_n: int) -> "_Q":
        self._range = (from_n, to_n)
        return self

    def insert(self, payload: Any) -> "_Q":
        self._insert = payload
        return self

    def _match(self, row: dict[str, Any]) -> bool:
        for key, op, val in self._filters:
            cell = row.get(key)
            if op == "eq" and cell != val:
                return False
            if op == "neq" and cell == val:
                return False
            if op == "in" and cell not in val:
                return False
            if op == "is" and cell is not (None if val in (None, "null") else val):
                return False
        return True

    def execute(self) -> _R:
        store = self._db.setdefault(self._name, [])
        if self._insert is not None:
            payloads = self._insert if isinstance(self._insert, list) else [self._insert]
            written = []
            for p in payloads:
                row = dict(p)
                row.setdefault("id", f"gen-{len(store):06d}")
                store.append(row)
                written.append(row)
            return _R(written)

        rows = [r for r in store if self._match(r)]
        total = len(rows) if self._count == "exact" else None
        # Undefined physical order unless the caller asked for one.
        self._rng.shuffle(rows)
        for key, desc in reversed(self._orders):
            rows.sort(key=lambda r: (r.get(key) is None, r.get(key)), reverse=desc)
        if self._range is not None:
            f, t = self._range
            rows = rows[f : t + 1]
        rows = rows[: self._cap]
        return _R([dict(r) for r in rows], count=total)


class PagingSB:
    def __init__(self, db: dict, *, cap: int = _PAGE, seed: int = 7):
        self.db = db
        self._cap = cap
        self._rng = random.Random(seed)

    def table(self, name: str) -> _Q:
        return _Q(name, self.db, self._cap, self._rng)


def _corpus(n: int = N_TOPICS) -> dict:
    """One verified paper, one verified question per topic, one primary tag
    each — the minimum that gives ``n`` scored topics."""
    return {
        "pyq_papers": [
            {"id": "p1", "exam_id": "exam-1", "exam_phase_id": None, "trust_status": "verified"}
        ],
        "pyq_questions": [
            {"id": f"q{i:06d}", "pyq_paper_id": "p1", "reviewer_status": "verified"}
            for i in range(n)
        ],
        "pyq_question_topic_tags": [
            {
                "id": f"tag{i:06d}",
                "question_id": f"q{i:06d}",
                "topic_id": f"t{i:06d}",
                "reviewer_status": "verified",
                "tag_role": "primary",
            }
            for i in range(n)
        ],
        "topics": [{"id": f"t{i:06d}", "subject_id": "s1"} for i in range(n)],
        "exam_topic_coverage": [],
        "exam_topic_score_snapshots": [],
    }


def _drafts(sb: Any) -> list[dict[str, Any]]:
    return sb.db.get("exam_topic_score_snapshots", [])


# ── 1. Repeat computes over unchanged inputs write exactly once ──────────────
def test_ten_consecutive_computes_write_exactly_once():
    """The live failure: identical inputs, repeated calls, duplicate drafts.
    The corpus spans the drafts read's page boundary, so the second call
    onwards is served by a two-page index build — the read that was silently
    partitioning wrong."""
    sb = PagingSB(_corpus())

    first = compute_exam_topic_scores(sb, "exam-1")
    assert first["read_error"] is False
    assert first["errors"] == 0
    assert first["written"] == N_TOPICS
    assert len(_drafts(sb)) == N_TOPICS

    for call in range(2, 12):
        result = compute_exam_topic_scores(sb, "exam-1")
        assert result["read_error"] is False, f"call {call} refused"
        assert result["written"] == 0, f"call {call} wrote {result['written']} duplicates"
        assert result["skipped"] == N_TOPICS, f"call {call} skipped {result['skipped']}"

    # One draft per topic, still, after eleven computes.
    assert len(_drafts(sb)) == N_TOPICS
    per_topic: dict[str, int] = {}
    for row in _drafts(sb):
        per_topic[row["topic_id"]] = per_topic.get(row["topic_id"], 0) + 1
    assert max(per_topic.values()) == 1


# ── 2. A short index read refuses instead of writing ─────────────────────────
def test_short_drafts_read_refuses_rather_than_duplicating():
    """A page that comes back short WITHOUT raising is the dangerous case: by
    length alone it is indistinguishable from the end of the set. Compared
    against the server's exact count it is not, and the compute must fail
    closed — a refused run self-heals on the next call, a duplicate draft
    needs an operator."""
    db = _corpus(n=5)
    sb = PagingSB(db)
    assert compute_exam_topic_scores(sb, "exam-1")["written"] == 5
    baseline = [dict(r) for r in _drafts(sb)]

    class _ShortReadSB(PagingSB):
        """Drops one row from the drafts read while still reporting the true
        exact count — a partial read that looks like success."""

        def table(self, name: str) -> _Q:
            q = super().table(name)
            if name != "exam_topic_score_snapshots":
                return q
            inner = q.execute

            def _short() -> _R:
                resp = inner()
                if resp.count is None:  # an insert, not the index read
                    return resp
                return _R(resp.data[:-1], count=resp.count)

            q.execute = _short  # type: ignore[method-assign]
            return q

    short_sb = _ShortReadSB(db)
    result = compute_exam_topic_scores(short_sb, "exam-1")

    assert result["read_error"] is True
    assert result["written"] == 0
    assert _drafts(short_sb) == baseline  # nothing written


# ── 3. Fingerprint stability (G2) ────────────────────────────────────────────
def test_fingerprint_is_stable_across_input_orderings():
    """A fingerprint that folded in row order would produce duplicates with a
    perfectly healthy index. It does not: every component is sorted."""
    papers = [f"p{i}" for i in range(20)]
    questions = [f"q{i}" for i in range(50)]
    tags = [(f"q{i}", f"t{i % 7}") for i in range(50)]
    cov = [
        {"topic_id": f"t{i}", "exam_priority_score": 10 * i, "is_high_yield": i % 2 == 0}
        for i in range(7)
    ]
    q_to_paper = {f"q{i}": f"p{i % 20}" for i in range(50)}
    topic_subject = {f"t{i}": f"s{i % 3}" for i in range(7)}

    def fp(seed: int) -> str:
        rng = random.Random(seed)
        p, q, tg, cv = list(papers), list(questions), list(tags), list(cov)
        for seq in (p, q, tg, cv):
            rng.shuffle(seq)
        return _build_fingerprint(
            "exam-1", MODEL_VERSION, None, p, q, tg, cv,
            q_to_paper=dict(sorted(q_to_paper.items(), key=lambda kv: rng.random())),
            topic_subject=dict(sorted(topic_subject.items(), key=lambda kv: rng.random())),
        )

    digests = {fp(seed) for seed in range(12)}
    assert len(digests) == 1


def test_fingerprint_changes_when_an_input_changes():
    """Stability must not come from ignoring the inputs."""
    base = dict(
        exam_id="exam-1",
        model_version=MODEL_VERSION,
        exam_phase_id=None,
        paper_ids=["p1"],
        question_ids=["q1"],
        primary_tag_tuples=[("q1", "t1")],
        locked_cov_rows=[{"topic_id": "t1", "exam_priority_score": 80, "is_high_yield": True}],
    )
    a = _build_fingerprint(**base)
    moved = {**base, "primary_tag_tuples": [("q1", "t2")]}
    assert _build_fingerprint(**moved) != a


# ── 4. Small-corpus idempotency against the shared stub ──────────────────────
def test_repeat_compute_is_idempotent_on_the_shared_stub():
    """Guards the ordinary single-page path the rest of the suite exercises."""
    sb = SBStub(_corpus(n=3))
    assert compute_exam_topic_scores(sb, "exam-1")["written"] == 3
    for _ in range(5):
        result = compute_exam_topic_scores(sb, "exam-1")
        assert result["written"] == 0
        assert result["skipped"] == 3
    assert len(_drafts(sb)) == 3
