"""Paper-practice eligibility and the specific empty-pool 409 (PRACTICE-PAPER-01).

UPSC CSE Mains optional papers are entirely question_type='descriptive'. The
mock engine is MCQ-only, so they are never projected and `start_pyq_practice`
correctly returns an empty pool. These tests pin the two halves of the fix: the
picker must not offer what cannot launch, and when something slips through the
409 must say which of the three reasons applies.
"""
from __future__ import annotations

import pytest

from app.study_os import pyq_practice as pp


# ── structural eligibility (shared by picker and launcher) ──────────────────

@pytest.mark.parametrize(
    "metadata,expected",
    [
        ({"corpus_half": "thematic"}, "thematic_not_paper"),
        ({"retired": True}, "retired_paper"),
        ({"corpus_half": "thematic", "retired": True}, "thematic_not_paper"),
        ({"paper_kind": "optional"}, None),
        ({}, None),
        (None, None),
        ("not-a-dict", None),
        # retired must be the boolean true, not any truthy value: a string
        # "false" would otherwise retire a live paper.
        ({"retired": "false"}, None),
        ({"retired": False}, None),
        ({"corpus_half": "paper"}, None),
    ],
)
def test_paper_practice_exclusion(metadata, expected):
    assert pp.paper_practice_exclusion(metadata) == expected
    assert pp.is_paper_practiceable(metadata) is (expected is None)


# ── the 409 diagnosis ──────────────────────────────────────────────────────

class _Res:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, table, db, calls):
        self._table, self._db, self._calls = table, db, calls
        self._filters = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        self._calls.append((self._table, dict(self._filters)))
        if self._table == "pyq_papers":
            pid = self._filters.get("id")
            row = self._db.get("papers", {}).get(pid)
            return _Res([row] if row else [])
        if self._table == "pyq_questions":
            rows = self._db.get("questions", {}).get(self._filters.get("pyq_paper_id"), [])
            if self._filters.get("reviewer_status"):
                rows = [r for r in rows if r.get("reviewer_status") == self._filters["reviewer_status"]]
            return _Res(rows)
        return _Res([])


class _SB:
    def __init__(self, db, *, fail_on=None):
        self.db, self.calls, self._fail_on = db, [], fail_on

    def table(self, name):
        if self._fail_on == name:
            raise RuntimeError("probe exploded")
        return _Q(name, self.db, self.calls)


PAPER = "11111111-1111-1111-1111-111111111111"


def _db(meta, questions):
    return {"papers": {PAPER: {"id": PAPER, "metadata": meta}},
            "questions": {PAPER: questions}}


def test_thematic_paper_gets_its_own_code():
    sb = _SB(_db({"corpus_half": "thematic"}, []))
    code, detail = pp.diagnose_empty_pool(sb, mode="paper", target_id=PAPER)
    assert code == "thematic_not_paper"
    assert "topic-wise collection" in detail
    # Structural: decided without ever reading the questions.
    assert [t for t, _ in sb.calls] == ["pyq_papers"]


def test_all_descriptive_paper_gets_its_own_code():
    sb = _SB(_db({"paper_kind": "optional"}, [
        {"question_type": "descriptive", "reviewer_status": "verified"},
        {"question_type": "Descriptive", "reviewer_status": "verified"},
    ]))
    code, detail = pp.diagnose_empty_pool(sb, mode="paper", target_id=PAPER)
    assert code == "descriptive_paper"
    assert "answer-writing practice not available yet" in detail


def test_mixed_paper_falls_through_to_the_generic_code():
    """A paper with any non-descriptive verified question is not a descriptive
    paper — it is an unprojected one, which is a different problem."""
    sb = _SB(_db({}, [
        {"question_type": "descriptive", "reviewer_status": "verified"},
        {"question_type": "mcq", "reviewer_status": "verified"},
    ]))
    code, detail = pp.diagnose_empty_pool(sb, mode="paper", target_id=PAPER)
    assert code == pp.EMPTY_POOL_DEFAULT_CODE
    assert detail == pp.EMPTY_POOL_DEFAULT_DETAIL


def test_unverified_descriptive_questions_do_not_decide_it():
    """Only verified questions count: the launcher would never select a pending
    row, so a pending MCQ must not make an all-descriptive paper look mixed."""
    sb = _SB(_db({}, [
        {"question_type": "descriptive", "reviewer_status": "verified"},
        {"question_type": "mcq", "reviewer_status": "pending"},
    ]))
    assert pp.diagnose_empty_pool(sb, mode="paper", target_id=PAPER)[0] == "descriptive_paper"


def test_paper_with_no_verified_questions_is_generic():
    sb = _SB(_db({}, [{"question_type": "mcq", "reviewer_status": "pending"}]))
    assert pp.diagnose_empty_pool(sb, mode="paper", target_id=PAPER)[0] == pp.EMPTY_POOL_DEFAULT_CODE


@pytest.mark.parametrize("mode", ["section", "topic"])
def test_non_paper_modes_are_not_diagnosed(mode):
    """A section or topic target is not a paper, so there is nothing structural
    to say — and nothing should be read."""
    sb = _SB(_db({"corpus_half": "thematic"}, []))
    assert pp.diagnose_empty_pool(sb, mode=mode, target_id=PAPER)[0] == pp.EMPTY_POOL_DEFAULT_CODE
    assert sb.calls == []


def test_missing_paper_is_generic():
    sb = _SB({"papers": {}, "questions": {}})
    assert pp.diagnose_empty_pool(sb, mode="paper", target_id=PAPER)[0] == pp.EMPTY_POOL_DEFAULT_CODE


def test_probe_failure_degrades_instead_of_escalating():
    """A diagnosis is a nicety. It must never turn a correct 409 into a 500."""
    sb = _SB(_db({}, []), fail_on="pyq_papers")
    code, detail = pp.diagnose_empty_pool(sb, mode="paper", target_id=PAPER)
    assert code == pp.EMPTY_POOL_DEFAULT_CODE
    assert detail == pp.EMPTY_POOL_DEFAULT_DETAIL
