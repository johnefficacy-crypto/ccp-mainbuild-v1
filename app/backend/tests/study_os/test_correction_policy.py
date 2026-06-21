"""Shared mock-correction policy (§7): aggregation, aliases, and REAL adapter-level
cross-origin parity.

Parity is proven by driving the ACTUAL production adapters
(``mocks._draft_corrections_from_mock`` and
``mastery_engine.derive_correction_tasks``) — never by substituting a direct
shared-policy call for one side. Topic representation is intentionally NOT
asserted equal (manual carries a display label; generated carries a canonical id).

Stub-only; no live DB.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.study_os import correction_policy as cp
from app.study_os import mastery_writer as mw
from app.study_os import mocks
from app.study_os.mastery_engine.correction_tasks import derive_correction_tasks
from app.study_os.mastery_engine.schemas import (
    AttemptQuestionAnalytics,
    AttemptTopicAnalytics,
    DerivedAttemptAnalytics,
)
from app.study_os.mocks import VALID_CORRECTION_CATEGORIES
from tests.persona_questions._stub import SBStub

TOPIC = "t1"
USER = "u-1"
ATTEMPT = "11111111-1111-1111-1111-111111111111"
_BASE = {
    "concept_gap": "Concept drill",
    "memory_gap": "Spaced revision",
    "careless": "Accuracy drill",
    "speed_issue": "Timed retrieval set",
    "option_trap": "Distractor elimination drill",
}


# ── 1. shared policy aggregation ──────────────────────────────────────────────

def _inp(error_counts=None, **kw):
    return cp.CorrectionPolicyInput(topic=TOPIC, error_counts=error_counts or {}, **kw)


def test_aggregation_collapses_aliases():
    assert cp.canonical_counts({"concept": 1, "concept_gap": 2}) == {"concept_gap": 3}
    assert cp.select_categories(_inp({"concept": 1, "concept_gap": 2})) == ["concept_gap"]


def test_ordered_by_count_desc():
    assert cp.select_categories(_inp({"option": 3, "concept": 1})) == ["option_trap", "concept_gap"]


def test_equal_count_stable_tiebreak():
    got = cp.select_categories(_inp({"option_trap": 2, "concept_gap": 2}))
    assert got == ["concept_gap", "option_trap"]  # _TIE_BREAK_ORDER
    assert cp.select_categories(_inp({"concept_gap": 2, "option_trap": 2})) == got  # insertion-order independent


def test_unknown_only_no_categories():
    assert cp.select_categories(_inp({"guess": 5, "marked_unanswered": 2})) == []


def test_recognized_plus_unknown_keeps_recognized_only():
    assert cp.select_categories(_inp({"concept_gap": 2, "gibberish": 9})) == ["concept_gap"]


def test_explicit_fallbacks_only():
    assert cp.select_categories(_inp(weak_topic=True)) == ["concept_gap"]
    assert cp.select_categories(_inp(attempted=3, accuracy_pct=Decimal("10"))) == ["concept_gap"]
    assert cp.select_categories(_inp(prior_error=True)) == ["concept_gap"]
    assert cp.select_categories(_inp()) == []  # no signal at all
    assert cp.select_categories(_inp(attempted=2, accuracy_pct=Decimal("0"))) == []  # < min attempted


# ── 2. full alias coverage ────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("concept", "concept_gap"), ("concept_gap", "concept_gap"),
        ("knowledge_gap", "concept_gap"), ("formula_confusion", "concept_gap"),
        ("memory", "memory_gap"), ("memory_gap", "memory_gap"), ("recall", "memory_gap"),
        ("fact_recall", "memory_gap"), ("forgetting", "memory_gap"),
        ("careless", "careless"), ("calc", "careless"), ("calc_error", "careless"),
        ("calculation_error", "careless"), ("silly", "careless"), ("silly_mistake", "careless"),
        ("misread", "careless"), ("misread_question", "careless"),
        ("speed_issue", "speed_issue"), ("time", "speed_issue"), ("time_pressure", "speed_issue"),
        ("time_pressure_unattempted", "speed_issue"), ("time_management", "speed_issue"),
        ("slow", "speed_issue"), ("timeout", "speed_issue"),
        ("option", "option_trap"), ("option_trap", "option_trap"), ("trap", "option_trap"),
        ("  Misread  ", "careless"),
    ],
)
def test_alias_normalization(raw, expected):
    assert cp.normalize_error_type(raw) == expected
    assert expected in VALID_CORRECTION_CATEGORIES


@pytest.mark.parametrize("raw", ["guess", "marked_unanswered", "correct", "unknown", "", "gibberish", None])
def test_unknown_alias_is_none(raw):
    assert cp.normalize_error_type(raw) is None


# ── adapters ──────────────────────────────────────────────────────────────────

def _man(error_patterns, weak=None):
    out = mocks._draft_corrections_from_mock({"error_patterns": error_patterns, "weak_topics": weak or []})
    return [d["category"] for d in out], out


def _analytics(error_types, *, source_type="authored"):
    qs = [
        AttemptQuestionAnalytics(
            question_id=f"q{i}", topic_id=TOPIC, is_correct=False,
            difficulty="medium", source_type=source_type, error_type=et,
        )
        for i, et in enumerate(error_types)
    ]
    topics = [AttemptTopicAnalytics(topic_id=TOPIC, attempted=len(qs), correct=0, accuracy_pct=Decimal("0"))]
    return DerivedAttemptAnalytics(attempt_id=ATTEMPT, user_id=USER, questions=qs, topics=topics)


def _gen(error_types, *, source_type="authored"):
    drafts = derive_correction_tasks(_analytics(error_types, source_type=source_type), [], set())
    drafts = [d for d in drafts if d.topic_id == TOPIC]
    return [d.category for d in drafts], drafts


# ── 3. real manual adapter ────────────────────────────────────────────────────

def test_manual_mixed_evidence_ordered_no_dup():
    cats, out = _man({"concept": 1, "option": 3}, weak=[TOPIC])
    assert cats == ["option_trap", "concept_gap"]
    assert [d["title"] for d in out] == [_BASE["option_trap"], _BASE["concept_gap"]]


def test_manual_alias_collision_single_concept():
    cats, _ = _man({"concept": 1, "concept_gap": 2}, weak=[TOPIC])
    assert cats == ["concept_gap"]


@pytest.mark.parametrize("ep,expected", [
    ({"memory": 2}, "memory_gap"),
    ({"time": 2}, "speed_issue"),
    ({"misread": 2}, "careless"),
])
def test_manual_single_category(ep, expected):
    cats, out = _man(ep, weak=[TOPIC])
    assert cats == [expected]
    assert out[0]["title"] == _BASE[expected]


def test_manual_unknown_only_no_corrections():
    cats, _ = _man({"guess": 3})
    assert cats == []


def test_manual_unknown_evidence_with_weak_topic_emits_single_policy_fallback():
    cats, out = _man({"guess": 3, "mystery": 2}, weak=["first", "second"])

    assert cats == ["concept_gap"]
    assert [d["topic"] for d in out] == ["first"]
    assert out[0]["title"] == _BASE["concept_gap"]


def test_manual_weak_topic_fallback_policy_owned_single_topic():
    cats, out = _man({}, weak=["a", "b", "c", "d"])
    assert cats == ["concept_gap"]
    assert [d["topic"] for d in out] == ["a"]
    assert out[0]["title"] == _BASE["concept_gap"]


# ── 4. real generated pipeline ────────────────────────────────────────────────

def test_generated_mixed_ordered_no_dup_tasktype_irrelevant():
    cats, drafts = _gen(["concept_gap", "option_trap", "option_trap", "option_trap"])
    assert cats == ["option_trap", "concept_gap"]
    assert len({d.category for d in drafts}) == 2  # no duplicate category
    # task_type is action style; it does not equal/!alter the category
    by_cat = {d.category: d.task_type for d in drafts}
    assert by_cat["concept_gap"] == "concept_review" and by_cat["option_trap"] == "trap_review"


def test_generated_alias_collision():
    cats, _ = _gen(["concept", "concept_gap", "concept_gap"])
    assert cats == ["concept_gap"]


@pytest.mark.parametrize("ets,expected", [
    (["memory_gap", "recall"], "memory_gap"),
    (["time_pressure", "time_management"], "speed_issue"),
    (["calc_error", "misread_question"], "careless"),
])
def test_generated_memory_speed_misread_survive(ets, expected):
    cats, _ = _gen(ets)
    assert cats == [expected]


def test_generated_wrong_pyq_action_style_not_category():
    cats, drafts = _gen(["memory_gap", "memory_gap"], source_type="pyq")
    assert cats == ["memory_gap"]                 # category unchanged by pyq
    assert drafts[0].task_type == "pyq_revision"  # action style upgraded


def test_generated_low_accuracy_fallback_no_recognized_error():
    cats, _ = _gen([None, None, None])  # 3 wrong, no error_type → fallback
    assert cats == ["concept_gap"]


def test_generated_unknown_only_no_fallback():
    cats, _ = _gen(["guess"])  # 1 wrong unknown, attempted<3 → no fallback
    assert cats == []


# ── 5. REAL cross-origin parity (both adapters) ───────────────────────────────

_PARITY = [
    ("A", {"concept": 1, "option": 3}, ["concept_gap", "option_trap", "option_trap", "option_trap"], ["option_trap", "concept_gap"]),
    ("B", {"concept": 1, "concept_gap": 2}, ["concept", "concept_gap", "concept_gap"], ["concept_gap"]),
    ("C", {"memory": 1, "recall": 1}, ["memory_gap", "recall"], ["memory_gap"]),
    ("D", {"time": 1, "time_pressure": 1}, ["time_pressure", "time_management"], ["speed_issue"]),
    ("E", {"calc": 1, "misread": 1}, ["calc_error", "misread_question"], ["careless"]),
    ("F", {"concept": 2, "option": 2}, ["concept_gap", "concept_gap", "option_trap", "option_trap"], ["concept_gap", "option_trap"]),
    ("G", {"guess": 3}, ["guess"], []),
]


@pytest.mark.parametrize("name,manual_ep,gen_ets,expected", _PARITY)
def test_cross_origin_parity(name, manual_ep, gen_ets, expected):
    man_cats, man_out = _man(manual_ep, weak=[TOPIC] if expected else [])
    gen_cats, gen_drafts = _gen(gen_ets)
    assert man_cats == gen_cats == expected
    # base-title set parity (topic intentionally not compared)
    man_titles = [d["title"] for d in man_out]
    gen_titles = [cp.correction_title(d.category) for d in gen_drafts]
    assert man_titles == gen_titles == [_BASE[c] for c in expected]
    # one row per canonical category
    assert len(man_cats) == len(set(man_cats)) == len(gen_cats)


def test_cross_origin_parity_fallback_case_H():
    man_cats, man_out = _man({}, weak=[TOPIC])
    gen_cats, gen_drafts = _gen([None, None, None])
    assert man_cats == gen_cats == ["concept_gap"]
    assert man_out[0]["title"] == cp.correction_title("concept_gap") == _BASE["concept_gap"]


def test_evidence_mode_does_not_change_normalized_category_or_title_parity():
    manual_input = cp.CorrectionPolicyInput(
        topic=TOPIC,
        error_counts={},
        weak_topic=True,
        evidence_mode="summary",
    )
    generated_input = cp.CorrectionPolicyInput(
        topic=TOPIC,
        error_counts={},
        weak_topic=True,
        evidence_mode="question_level",
    )

    manual_categories = cp.select_categories(manual_input)
    generated_categories = cp.select_categories(generated_input)

    assert manual_categories == generated_categories == ["concept_gap"]
    assert [cp.correction_title(c) for c in manual_categories] == [
        cp.correction_title(c) for c in generated_categories
    ] == [_BASE["concept_gap"]]


# ── 6. persistence ────────────────────────────────────────────────────────────

def _seed_generated(sb, error_types):
    # Answered (selected_option_id set) wrong questions; error_type comes from the
    # classification table, not from the response row (the loader's authoritative
    # source post-DEFECT-003).
    sb.db.update({
        "mock_attempts": [{"id": ATTEMPT, "user_id": USER}],
        "mock_attempt_responses": [
            {"attempt_id": ATTEMPT, "question_id": f"q{i}", "selected_option_id": f"opt-{i}",
             "is_correct": False, "time_spent_sec": 5,
             "question_snapshot": {"topic_id": TOPIC, "difficulty": "medium", "source_type": "authored"}}
            for i, et in enumerate(error_types)
        ],
        "mock_attempt_response_classification": [
            {"attempt_id": ATTEMPT, "question_id": f"q{i}", "error_type": et}
            for i, et in enumerate(error_types)
        ],
        "mock_tests": [{"id": "mt-1", "mock_attempt_id": ATTEMPT, "trust_level": "platform_verified", "user_id": USER, "source_type": "platform_attempt"}],
        "mock_correction_tasks": [], "user_topic_mastery": [], "user_topic_mastery_audit": [],
        "user_topic_error_patterns": [], "mock_mastery_shadow": [], "study_plans": [], "study_tasks": [],
    })


def test_generated_persist_all_specs_063_and_serial_dedup(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    sb = SBStub()
    _seed_generated(sb, ["concept_gap", "option_trap", "option_trap", "option_trap"])
    writer = mw.MasteryWriter(sb, "live")
    asyncio.run(writer.process_attempt(ATTEMPT))

    rows = sb.db["mock_correction_tasks"]
    assert {r["category"] for r in rows} == {"concept_gap", "option_trap"}
    for r in rows:
        assert r["mock_test_id"] and r["category"] in VALID_CORRECTION_CATEGORIES
        assert r["title"] == _BASE[r["category"]]      # category-only title
        assert "task_type" not in r and "priority" not in r  # 063 columns only
    n = len(rows)
    asyncio.run(writer.process_attempt(ATTEMPT))        # serial retry
    assert len(sb.db["mock_correction_tasks"]) == n     # no duplicates


def test_manual_persist_redraft_and_apply(monkeypatch):
    sb = SBStub()
    sb.db.update({
        "mock_tests": [{"id": "mt-man", "user_id": USER, "review_state": "reviewed",
                        "error_patterns": {"concept": 1, "option": 3}, "weak_topics": [TOPIC]}],
        "mock_correction_tasks": [], "study_plans": [], "study_tasks": [],
    })
    first = mocks.draft_correction_tasks(sb, USER, "mt-man")
    assert {c["category"] for c in first} == {"concept_gap", "option_trap"}
    for c in first:
        assert c["title"] == _BASE[c["category"]]
    # re-draft replaces prior drafted rows (no accumulation)
    again = mocks.draft_correction_tasks(sb, USER, "mt-man")
    assert len([r for r in sb.db["mock_correction_tasks"] if r["state"] == "drafted"]) == len(again) == 2
    # apply → study_tasks with canonical category
    applied = mocks.apply_correction_task(sb, USER, again[0]["id"])
    task = sb.db["study_tasks"][-1]
    assert task["metadata"]["category"] == applied["category"] in VALID_CORRECTION_CATEGORIES


# ── 7. end-to-end cross-origin parity into study_tasks ────────────────────────

def _apply_all(sb, corrections):
    cats = {}
    for c in corrections:
        mocks.apply_correction_task(sb, USER, c["id"])
    for t in sb.db["study_tasks"]:
        cats[t["metadata"]["category"]] = t["title"]
    return cats


def test_e2e_generated_and_manual_same_categories_and_titles(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")

    # generated origin
    sb_gen = SBStub()
    _seed_generated(sb_gen, ["concept_gap", "option_trap", "option_trap", "option_trap"])
    asyncio.run(mw.MasteryWriter(sb_gen, "live").process_attempt(ATTEMPT))
    gen_cats = _apply_all(sb_gen, list(sb_gen.db["mock_correction_tasks"]))

    # manual origin: equivalent evidence
    sb_man = SBStub()
    sb_man.db.update({
        "mock_tests": [{"id": "mt-man", "user_id": USER, "review_state": "reviewed",
                        "error_patterns": {"concept": 1, "option": 3}, "weak_topics": [TOPIC]}],
        "mock_correction_tasks": [], "study_plans": [], "study_tasks": [],
    })
    man_drafts = mocks.draft_correction_tasks(sb_man, USER, "mt-man")
    man_cats = _apply_all(sb_man, man_drafts)

    assert set(gen_cats) == set(man_cats) == {"concept_gap", "option_trap"}
    # category-only base titles, identical across origins
    assert gen_cats == man_cats
    for c, title in gen_cats.items():
        assert title == _BASE[c]
