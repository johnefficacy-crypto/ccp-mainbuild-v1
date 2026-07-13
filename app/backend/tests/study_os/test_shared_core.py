"""Tests for the regulatory shared-core overlap model (Lane R R2, increment 1).

Uses a FILTER-AWARE fake supabase (applies .eq/.in_/.is_) and the real 0–100
mastery scale + canonical target-exam sources, so the schema/scope bugs the
checkpost flagged are actually exercised.
"""
from app.study_os.shared_core import (
    allocation_targets,
    mastery_reuse,
    partition_topics,
    summarize_regulatory_overlap,
)


# ── Pure functions ───────────────────────────────────────────────────────────

def test_partition_shared_vs_delta():
    cov = {"sebi": ["quant", "eco", "sebi_reg"], "pfrda": ["quant", "eco", "pension"]}
    part = partition_topics(cov)
    assert part["shared_core"] == ["eco", "quant"]
    assert part["delta_by_exam"]["sebi"] == ["sebi_reg"]
    assert part["delta_by_exam"]["pfrda"] == ["pension"]


def test_mastery_reuse_only_shared_and_global():
    cov = {"sebi": ["quant", "eco"], "pfrda": ["quant", "pension"]}
    # quant shared + globally mastered → reused; eco only in sebi → not.
    assert mastery_reuse(cov, ["quant", "eco", "unknown"]) == [
        {"topic_id": "quant", "exams": ["pfrda", "sebi"]}
    ]


def test_allocation_sums_exactly():
    for total in range(0, 40):
        a = allocation_targets(total)
        assert a["shared_core"] + a["target_delta"] + a["current_affairs"] == total
    assert allocation_targets(10) == {"shared_core": 7, "target_delta": 2, "current_affairs": 1}
    assert allocation_targets(0)["shared_core"] == 0


# ── Filter-aware fake supabase ───────────────────────────────────────────────

class _Q:
    def __init__(self, rows, fail=False):
        self._rows, self._fail, self._eq, self._in = rows, fail, {}, None

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._eq[col] = val
        return self

    def in_(self, col, vals):
        self._in = (col, list(vals))
        return self

    def is_(self, col, val):
        self._eq[col] = None if str(val).lower() == "null" else val
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._fail:
            raise RuntimeError("simulated read failure")
        rows = list(self._rows)
        for col, val in self._eq.items():
            rows = [r for r in rows if r.get(col) == val]
        if self._in:
            col, vals = self._in
            rows = [r for r in rows if r.get(col) in vals]
        return type("R", (), {"data": rows})()


class _SB:
    def __init__(self, tables, fail_tables=()):
        self._tables, self._fail = tables, set(fail_tables)

    def table(self, name):
        return _Q(self._tables.get(name, []), fail=name in self._fail)


def _tables(*, target_exams, primary=None, exams, coverage, mastery):
    return {
        "exam_families": [{"id": "fam-fr", "slug": "financial-regulatory"}],
        "aspirant_preferences": [{"user_id": "u1", "target_exams": target_exams}],
        "profiles": [{"id": "u1", "target_exam": primary}],
        "exams": exams,
        "exam_topic_coverage": coverage,
        "user_topic_mastery": mastery,
    }


_EXAMS = [
    {"id": "sebi-id", "slug": "sebi-grade-a", "name": "SEBI", "exam_family_id": "fam-fr", "is_active": True},
    {"id": "pfrda-id", "slug": "pfrda-grade-a", "name": "PFRDA", "exam_family_id": "fam-fr", "is_active": True},
]


def _cov(exam_id, topic_id, stream_id=None, status="locked"):
    return {"exam_id": exam_id, "topic_id": topic_id, "stream_id": stream_id, "reviewer_status": status}


def test_canonical_sources_and_shared_core_and_scope():
    coverage = [
        _cov("sebi-id", "quant"), _cov("sebi-id", "eco"), _cov("sebi-id", "sebi_reg"),
        _cov("sebi-id", "legal_only", stream_id="sebi-legal"),   # stream-specific → excluded
        _cov("sebi-id", "draft_topic", status="draft"),          # not locked → excluded
        _cov("pfrda-id", "quant"), _cov("pfrda-id", "eco"), _cov("pfrda-id", "pension"),
    ]
    mastery = [
        {"user_id": "u1", "topic_id": "quant", "exam_id": None, "mastery_score": 80},   # global ≥70 → mastered
        {"user_id": "u1", "topic_id": "eco", "exam_id": None, "mastery_score": 30},      # global <70 → not
        {"user_id": "u1", "topic_id": "eco", "exam_id": "sebi-id", "mastery_score": 95}, # exam-scoped → ignored
    ]
    sb = _SB(_tables(target_exams=["sebi-grade-a", "pfrda-grade-a", "unrelated"], exams=_EXAMS,
                     coverage=coverage, mastery=mastery))
    out = summarize_regulatory_overlap(sb, "u1")
    assert out["status"] == "ok"
    assert [e["id"] for e in out["exams"]] == ["pfrda-id", "sebi-id"]  # sorted by slug (deterministic)
    assert out["shared_core"] == ["eco", "quant"]                      # common only
    assert "legal_only" not in out["shared_core"] + out["delta_by_exam"]["sebi-id"]
    assert out["stream_specific_by_exam"]["sebi-id"] == 1
    # quant global-mastered & shared → reused; eco NOT (exam-scoped 95 ignored, global 30 < 70).
    assert out["mastery_reuse"] == [{"topic_id": "quant", "exams": ["pfrda-id", "sebi-id"]}]
    assert out["mastery_scale"] == "0-100"


def test_primary_target_exam_uuid_is_resolved():
    sb = _SB(_tables(target_exams=["sebi-grade-a"], primary="pfrda-id", exams=_EXAMS,
                     coverage=[_cov("sebi-id", "quant"), _cov("pfrda-id", "quant")], mastery=[]))
    out = summarize_regulatory_overlap(sb, "u1")
    assert {e["id"] for e in out["exams"]} == {"sebi-id", "pfrda-id"}
    assert out["shared_core"] == ["quant"]


def test_fewer_than_two_regulatory_exams_is_insufficient_zero_allocation():
    sb = _SB(_tables(target_exams=["sebi-grade-a"], exams=_EXAMS, coverage=[_cov("sebi-id", "quant")], mastery=[]))
    out = summarize_regulatory_overlap(sb, "u1")
    assert out["status"] == "insufficient_regulatory_exams"
    assert out["allocation"] == {"shared_core": 0, "target_delta": 0, "current_affairs": 0}


def test_no_shared_core_gives_zero_allocation():
    sb = _SB(_tables(target_exams=["sebi-grade-a", "pfrda-grade-a"], exams=_EXAMS,
                     coverage=[_cov("sebi-id", "a"), _cov("pfrda-id", "b")], mastery=[]))
    out = summarize_regulatory_overlap(sb, "u1")
    assert out["status"] == "ok"
    assert out["shared_core"] == []
    assert out["allocation"] == {"shared_core": 0, "target_delta": 0, "current_affairs": 0}


def test_coverage_read_failure_is_unavailable_not_partial():
    sb = _SB(_tables(target_exams=["sebi-grade-a", "pfrda-grade-a"], exams=_EXAMS, coverage=[], mastery=[]),
             fail_tables=["exam_topic_coverage"])
    out = summarize_regulatory_overlap(sb, "u1")
    assert out["status"] == "unavailable"
    assert out["reason"].startswith("coverage_read_failed")
    assert out["shared_core"] == []


def test_mastery_read_failure_is_unavailable():
    sb = _SB(_tables(target_exams=["sebi-grade-a", "pfrda-grade-a"], exams=_EXAMS,
                     coverage=[_cov("sebi-id", "quant"), _cov("pfrda-id", "quant")], mastery=[]),
             fail_tables=["user_topic_mastery"])
    out = summarize_regulatory_overlap(sb, "u1")
    assert out["status"] == "unavailable"
    assert out["reason"] == "mastery_read_failed"


def test_target_exams_read_failure_is_unavailable():
    sb = _SB(_tables(target_exams=[], exams=_EXAMS, coverage=[], mastery=[]),
             fail_tables=["aspirant_preferences"])
    out = summarize_regulatory_overlap(sb, "u1")
    assert out["status"] == "unavailable"
    assert out["reason"] == "target_exams_read_failed"
