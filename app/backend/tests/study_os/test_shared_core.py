"""Tests for the regulatory shared-core overlap model (Lane R R2, increment 1)."""
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
    assert part["shared_core"] == ["eco", "quant"]  # covered by both
    assert part["delta_by_exam"]["sebi"] == ["sebi_reg"]
    assert part["delta_by_exam"]["pfrda"] == ["pension"]


def test_partition_needs_two_exams_for_shared():
    # A topic in only one exam is never shared core.
    part = partition_topics({"sebi": ["quant"], "pfrda": ["pension"]})
    assert part["shared_core"] == []
    assert part["delta_by_exam"] == {"sebi": ["quant"], "pfrda": ["pension"]}


def test_partition_ignores_falsy_topic_ids():
    part = partition_topics({"a": ["quant", None, ""], "b": ["quant", None]})
    assert part["shared_core"] == ["quant"]


def test_mastery_reuse_only_shared_and_mastered():
    cov = {"sebi": ["quant", "eco"], "pfrda": ["quant", "pension"]}
    # quant is shared + mastered → reused; eco mastered but only in sebi → not reused.
    reuse = mastery_reuse(cov, mastered=["quant", "eco", "unknown"])
    assert reuse == [{"topic_id": "quant", "exams": ["pfrda", "sebi"]}]


def test_allocation_sums_exactly_and_is_deterministic():
    for total in range(0, 40):
        alloc = allocation_targets(total)
        assert alloc["shared_core"] + alloc["target_delta"] + alloc["current_affairs"] == total
    # 70/20/10 shape on a round number.
    assert allocation_targets(10) == {"shared_core": 7, "target_delta": 2, "current_affairs": 1}
    # Largest-remainder is stable band-ordered for a total that doesn't divide evenly.
    assert allocation_targets(11) == allocation_targets(11)


def test_allocation_nonpositive_total():
    assert allocation_targets(0) == {"shared_core": 0, "target_delta": 0, "current_affairs": 0}
    assert allocation_targets(-5) == {"shared_core": 0, "target_delta": 0, "current_affairs": 0}


# ── DB wrapper (fake supabase) ───────────────────────────────────────────────

class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return type("R", (), {"data": self._rows})()


class _FakeSupabase:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return _FakeQuery(self._tables.get(name, []))


def _fake(monkeypatch, *, target_exams, exams, coverage, mastery):
    tables = {
        "exam_families": [{"id": "fam-fr"}],
        "user_study_plan_preferences": [{"target_exams": target_exams}],
        "exams": exams,
        "user_topic_mastery": mastery,
    }
    sb = _FakeSupabase(tables)
    # Stub locked_topic_coverage so the wrapper doesn't hit the real coverage reader.
    import app.exam_intelligence.coverage as cov_mod

    monkeypatch.setattr(
        cov_mod,
        "locked_topic_coverage",
        lambda supabase, exam_id: [{"topic_id": t} for t in coverage.get(exam_id, [])],
    )
    return sb


def test_summary_fewer_than_two_regulatory_exams_is_empty(monkeypatch):
    sb = _fake(
        monkeypatch,
        target_exams=["sebi-id"],
        exams=[{"id": "sebi-id", "slug": "sebi-grade-a", "name": "SEBI", "exam_family_id": "fam-fr", "is_active": True}],
        coverage={"sebi-id": ["quant"]},
        mastery=[],
    )
    out = summarize_regulatory_overlap(sb, "user1")
    assert out["shared_core"] == []
    assert out["mastery_reuse"] == []
    assert out["allocation"]["shared_core"] == 7  # allocation still returned


def test_summary_two_exams_shared_core_and_reuse(monkeypatch):
    sb = _fake(
        monkeypatch,
        target_exams=["sebi-id", "pfrda-id", "unrelated"],
        exams=[
            {"id": "sebi-id", "slug": "sebi-grade-a", "name": "SEBI", "exam_family_id": "fam-fr", "is_active": True},
            {"id": "pfrda-id", "slug": "pfrda-grade-a", "name": "PFRDA", "exam_family_id": "fam-fr", "is_active": True},
        ],
        coverage={"sebi-id": ["quant", "eco", "sebi_reg"], "pfrda-id": ["quant", "eco", "pension"]},
        mastery=[{"topic_id": "quant", "mastery_score": 0.9}, {"topic_id": "eco", "mastery_score": 0.3}],
    )
    out = summarize_regulatory_overlap(sb, "user1")
    assert {e["id"] for e in out["exams"]} == {"sebi-id", "pfrda-id"}
    assert out["shared_core"] == ["eco", "quant"]
    assert out["delta_by_exam"]["sebi-id"] == ["sebi_reg"]
    # quant mastered (0.9 ≥ 0.7) and shared → reused; eco below threshold → not.
    assert out["mastery_reuse"] == [{"topic_id": "quant", "exams": ["pfrda-id", "sebi-id"]}]
